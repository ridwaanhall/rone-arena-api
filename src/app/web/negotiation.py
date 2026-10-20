"""Point agents at the markdown twin of every web page (see `app/web/llms.py`).

A plain ASGI middleware, like `ServiceStatusGuard` in `main.py`, so it costs nothing on the API:

- A page request whose `Accept` header prefers `text/markdown` over `text/html` is answered with
  the page's `.md` twin at the same URL (the path is rewritten before routing).
- Every HTML page answer carries a `Link` header to its twin and to `/llms.txt`, so an agent finds
  them without parsing the page, and `Vary: Accept` because the same URL now has two forms.
"""
from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.web.routers.root import markdown_path

# Paths of the HTML pages that have a markdown twin; files and the API never match.
_PAGE_PREFIXES = ("/showcase", "/tools/", "/patch-notes", "/web/", "/web", "/blog")
_MARKDOWN_TYPES = ("text/markdown", "text/x-markdown")


def is_page(path: str) -> bool:
    if path == "/":
        return True
    last = path.rstrip("/").rsplit("/", 1)[-1]
    return path.startswith(_PAGE_PREFIXES) and "." not in last


def prefers_markdown(accept: str) -> bool:
    """True when markdown is asked for and ranks at least as high as HTML (wildcards ignored)."""
    markdown_q = html_q = 0.0
    for item in accept.split(","):
        media_type, *params = (part.strip() for part in item.split(";"))
        q = 1.0
        for param in params:
            name, _, value = param.partition("=")
            if name.strip().lower() == "q":
                try:
                    q = float(value)
                except ValueError:
                    q = 0.0
        media_type = media_type.lower()
        if media_type in _MARKDOWN_TYPES:
            markdown_q = max(markdown_q, q)
        elif media_type == "text/html":
            html_q = max(html_q, q)
    return markdown_q > 0 and markdown_q >= html_q


class MarkdownNegotiation:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or scope.get("method") not in ("GET", "HEAD") or not is_page(path):
            await self.app(scope, receive, send)
            return

        twin = markdown_path(path)
        accept = next((value.decode("latin-1") for name, value in scope["headers"] if name == b"accept"), "")
        if prefers_markdown(accept):
            scope = {**scope, "path": twin, "raw_path": twin.encode()}

        async def send_with_links(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("Vary", "Accept")
                if headers.get("content-type", "").startswith("text/html"):
                    headers.append(
                        "Link",
                        f'<{twin}>; rel="alternate"; type="text/markdown", </llms.txt>; rel="describedby"; type="text/plain"',
                    )
            await send(message)

        await self.app(scope, receive, send_with_links)
