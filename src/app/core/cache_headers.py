"""Let browsers and shared caches keep public API answers for a few minutes.

Hero, academy and esports data is the same for every caller and changes at most a few times a day, so a
successful GET answer carries ``Cache-Control: public, max-age=300``. A site that calls the API from the
browser then asks once per page and visitor instead of on every reload, and Cloudflare in front of a
caller's own site can share one answer between its visitors.

Never cached: user endpoints (personal, token in the header), the addon tools (the IP lookup answers per
visitor), anything sent with an Authorization header or cookies, errors, and answers that already say how
to be cached.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

PUBLIC_MAX_AGE = 300
# A stale answer may be shown for this long while a fresh one is fetched in the background.
STALE_WHILE_REVALIDATE = 60
PUBLIC_PREFIXES = ("/api/heroes", "/api/academy", "/api/esports/")
PUBLIC_CACHE_CONTROL = f"public, max-age={PUBLIC_MAX_AGE}, stale-while-revalidate={STALE_WHILE_REVALIDATE}"


def is_public_request(scope: Scope) -> bool:
    if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
        return False
    if not scope["path"].startswith(PUBLIC_PREFIXES):
        return False
    return not any(name in (b"authorization", b"cookie") for name, _ in scope.get("headers", []))


class PublicCacheHeaders:
    """A plain ASGI middleware: it only touches the response start of the requests it covers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not is_public_request(scope):
            await self.app(scope, receive, send)
            return

        async def send_with_cache(message: Message) -> None:
            if message["type"] == "http.response.start" and message["status"] == 200:
                headers = list(message.get("headers", []))
                if not any(name.lower() == b"cache-control" for name, _ in headers):
                    headers.append((b"cache-control", PUBLIC_CACHE_CONTROL.encode()))
                    message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_cache)
