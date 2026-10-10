from __future__ import annotations

import sys
from functools import wraps
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import Response

from app.core.config import DEBUG

# Web pages are the same for every visitor (sign-in state lives in the browser), so on
# Cloudflare Workers, where each request gets a small CPU budget, a rendered page is
# kept per isolate and reused. Elsewhere pages render on every request.
ENABLED = sys.platform == "emscripten" and not DEBUG

# (host, path) -> (status code, body, headers). Only rendered pages land here, so the key
# space is bounded by the site's routes; 404s are never stored. Headers carry the content
# type, since markdown pages and llms.txt are cached here too.
_pages: dict[tuple[str, str], tuple[int, bytes, dict[str, str]]] = {}


def page_cached(view: Callable[..., Response]) -> Callable[..., Response]:
    """Serve a web page view from the per-isolate cache when enabled.

    The host is part of the key because analytics only renders on the production host.
    """
    if not ENABLED:
        return view

    @wraps(view)
    def wrapper(request: Request, *args: Any, **kwargs: Any) -> Response:
        key = (request.url.hostname or "", request.url.path)
        hit = _pages.get(key)
        if hit is not None:
            return Response(content=hit[1], status_code=hit[0], headers=hit[2])
        response = view(request, *args, **kwargs)
        if response.status_code in (200, 503):
            headers = {name: value for name, value in response.headers.items() if name != "content-length"}
            _pages[key] = (response.status_code, bytes(response.body), headers)
        return response

    return wrapper
