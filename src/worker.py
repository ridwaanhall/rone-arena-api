"""Cloudflare Python Workers entry point (see wrangler.jsonc).

Cloudflare imports this module at deploy time and snapshots the result, so the
work done here (building the OpenAPI catalog, compiling templates) is paid once
per deploy instead of on the first request of every isolate.
"""

from workers import asgi

from app.main import app
from app.web.warm import warm

warm(app)

Default = asgi.entrypoint(app)
