"""Cloudflare Python Workers entry point (see wrangler.jsonc).

Cloudflare imports this module at deploy time and snapshots the result, so the
work done here (building the OpenAPI catalog, compiling templates) is paid once
per deploy instead of on the first request of every isolate.
"""

from workers import WorkerEntrypoint, asgi

from app.main import app
from app.utils.client_ip import reset_edge_geo, set_edge_geo
from app.web.warm import warm

warm(app)


def _edge_geo(request) -> dict[str, str] | None:
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
            return await asgi.fetch(app, request, self.env, self.ctx)
        finally:
            reset_edge_geo(token)
