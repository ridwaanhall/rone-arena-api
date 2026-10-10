"""Cloudflare Python Workers entry point (see wrangler.jsonc).

Cloudflare imports this module at deploy time and snapshots the result, so the
work done here (building the OpenAPI catalog, compiling templates) is paid once
per deploy instead of on the first request of every isolate.
"""

from workers import Response, WorkerEntrypoint, asgi

from app.core.config import ALTERNATIVE_ENDPOINT_URL
from app.core.fallback import FALLBACK_STATUSES, backup_url, redirect_headers
from app.main import app
from app.utils.client_ip import reset_edge_geo, set_edge_geo
from app.web.warm import warm

warm(app)


def _edge_geo(request) -> dict[str, str | None] | None:
    cf = getattr(request, "cf", None)
    if not cf:
        return None
    country = getattr(cf, "country", None)
    if not country:
        return None
    return {
        "city": getattr(cf, "city", None) or None,
        "state": getattr(cf, "region", None) or None,
        "country": str(country).lower(),
    }


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        # The ASGI scope carries no request.cf, so hand the visitor's location
        # to the app through a ContextVar (the app task copies this context).
        token = set_edge_geo(_edge_geo(request))
        try:
            response = await asgi.fetch(app, request, self.env, self.ctx)
        except Exception:
            # The app crashed: send the caller to the same path on the backup host.
            fallback = _to_backup(request, "exception")
            if fallback is None:
                raise
            return fallback
        finally:
            reset_edge_geo(token)
        if response.status in FALLBACK_STATUSES:
            return _to_backup(request, f"status-{response.status}") or response
        return response


def _to_backup(request, reason: str) -> Response | None:
    location = backup_url(str(request.url), ALTERNATIVE_ENDPOINT_URL)
    if location is None:
        return None
    return Response("", status=307, headers=redirect_headers(location, reason))
