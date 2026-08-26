from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.core.config import (
    API_BASE_URL,
    API_STATUS_MESSAGES,
    PROJECT_VERSION,
    DONATION_CURRENCY,
    DONATION_MIN,
    DONATION_NOW,
    DONATION_TARGET,
    DOCS_BASE_URL,
    IS_AVAILABLE,
    SERVICE_STATUS_KEY,
    MAINTENANCE_INFO_URL,
    SUPPORT_DETAILS,
    SUPPORT_STATUS_MESSAGES,
    BASE_URL,
)


from fastapi.routing import APIRoute
from fastapi import Request

router = APIRouter(tags=["root"])


def get_available_endpoints(app, include_methods: set[str] | None = None) -> list[dict]:
    endpoints: list[dict] = []
    internal_paths = {
        "/openapi.json",
        "/docs",
        "/redoc",
        "/api/openapi.json",
        "/api/docs",
        "/api/redoc",
        "/static",
    }
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if include_methods and not (set(route.methods) & include_methods):
            continue
        if route.path in internal_paths:
            continue
        endpoints.append({
            "path": route.path,
            "methods": list(route.methods),
            "name": route.name,
            "summary": getattr(route, "summary", None),
            "include_in_schema": getattr(route, "include_in_schema", True),
        })
    return endpoints


@router.get(
    path="/docs",
    include_in_schema=False,
)
def api_docs_redirect() -> RedirectResponse:
    return RedirectResponse(url="/api/docs", status_code=307)


@router.get(
    path="/api",
    summary="API Index and Status",
    include_in_schema=False,
    description=(
        "Provides API metadata, current status, and available endpoints.\n\n"
        "No parameters.\n\n"
        "The response includes API metadata and operational details:\n"
        "- **code**: Response code (e.g., 200).\n"
        "- **status**: Operational status (e.g., 'success').\n"
        "- **message**: Status message.\n"
        "- **timestamp**: Current server timestamp.\n"
        "- **meta**:\n"
        "    - **version**: API version (e.g., '3.1.0').\n"
        "    - **author**: API author.\n"
        "    - **base_url**: Base API URL.\n"
        "    - **support**: Support and donation details:\n"
        "        - **status**: Availability status.\n"
        "        - **donation_min**: Minimum donation amount.\n"
        "        - **donation_now**: Current donation progress.\n"
        "        - **donation_target**: Donation target.\n"
        "        - **donation_currency**: Currency used.\n"
        "        - **donation_links**: Links for support (GitHub Sponsors, BuyMeACoffee).\n"
        "        - **message**: Support message.\n"
        "- **endpoints**: List of available API endpoints (e.g., `/api/hero-list`, `/api/academy/heroes/{hero_identifier}/stats`).\n"
        "- **links**:\n"
        "    - **api_url**: Base API URL.\n"
        "    - **docs**: Documentation link.\n\n"
        "This endpoint is useful for:\n"
        "- Checking API operational status.\n"
        "- Retrieving metadata such as version and author.\n"
        "- Discovering available endpoints.\n"
        "- Accessing support and donation information.\n"
        "- Linking to API documentation."
    ),
)
async def api_index(request: Request) -> dict:
    from fastapi import FastAPI
    app: FastAPI = request.app
    status_key = SERVICE_STATUS_KEY
    status_info = API_STATUS_MESSAGES[status_key]
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    base_api_url = API_BASE_URL.rstrip("/")
    docs_url = DOCS_BASE_URL.rstrip("/")


    always_available: set[str] = {"/", "/api", "/docs", "/api/docs", "/robots.txt"}
    endpoints = get_available_endpoints(app, include_methods={"GET", "POST"})
    if IS_AVAILABLE:
        available_endpoints: list[str] = [
            ep["path"] for ep in endpoints if ep["include_in_schema"]
        ]
    else:
        available_endpoints: list[str] = [ep["path"] for ep in endpoints if ep["path"] in always_available]

    return {
        "code": 200,
        "status": "success",
        "message": "Request processed successfully",
        "timestamp": timestamp,
        "meta": {
            "version": PROJECT_VERSION,
            "author": "ridwaanhall",
            "base_url": base_api_url,
            "support": {
                "status": status_info["status"],
                "donation_min": DONATION_MIN,
                "donation_now": DONATION_NOW,
                "donation_target": DONATION_TARGET,
                "donation_currency": DONATION_CURRENCY,
                "donation_links": {
                    "github_sponsors": SUPPORT_DETAILS["github_sponsors"],
                    "buymeacoffee": SUPPORT_DETAILS["buymeacoffee"],
                },
                "message": SUPPORT_STATUS_MESSAGES[status_key],
            },
        },
        "endpoints": available_endpoints,
        "links": {
            "api_url": base_api_url if IS_AVAILABLE else MAINTENANCE_INFO_URL,
            "docs": docs_url,
        },
    }


@router.get(
    path="/robots.txt",
    summary="Robots.txt for Web Crawlers",
    include_in_schema=False,
    description=(
        "Provides instructions for web crawlers and bots accessing the API. "
        "The response defines rules for user-agents, allowed/disallowed paths, "
        "and includes references to the host information. "
        "This helps search engines and automated crawlers understand how to index "
        "and interact with the API resources."
    ),
)
def robots_txt() -> PlainTextResponse:
    host_url = BASE_URL.rstrip("/")
    content = "\n".join(["User-agent: *", "Allow: /", "Disallow:", f"Host: {host_url}"])
    return PlainTextResponse(content=content)
