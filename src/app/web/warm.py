from __future__ import annotations

from fastapi import FastAPI

from app.web.openapi_catalog import WEB_GROUPS, get_group_operations
from app.web.routers.root import templates


def warm(app: FastAPI) -> None:
    """Build what every page render needs, ahead of the first request.

    Generates the OpenAPI schema and the per-group endpoint catalog, and compiles
    every template. Called by the Cloudflare Worker entry point so this lands in the
    deploy-time snapshot.
    """
    for group in WEB_GROUPS:
        get_group_operations(app, group)
    for name in templates.env.list_templates(extensions=["html"]):
        templates.env.get_template(name)
