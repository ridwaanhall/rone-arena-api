from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import (
    ALTERNATIVE_ENDPOINT_URL,
    ANALYTICS_HOST,
    API_STATUS_MESSAGES,
    DEBUG,
    IS_AVAILABLE,
    IS_HIGH_TRAFFIC,
    IS_MAINTENANCE,
    DATE_AVAILABLE,
    SERVICE_STATUS_KEY,
    PROJECT_VERSION,
    BASE_URL,
    API_URL,
)
from app.core.paths import PUBLIC_DIR
from app.web.openapi_catalog import GROUP_META, WEB_GROUPS, get_group_operations
from app.web.showcase import ENTRY_KEYS, SHOWCASE, SUBMIT_URL, format_entry, llm_prompt, with_playground_links

router = APIRouter(tags=["web"])

_WEB_DIR = Path(__file__).resolve().parents[1]
_TEMPLATES_DIR = _WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _asset_version() -> str:
    """Content hash of the web static files, used as a cache-busting query string.

    Falls back to the project version where `public/` is not on disk (Cloudflare Workers).
    """
    if PUBLIC_DIR is None:
        return PROJECT_VERSION
    digest = hashlib.sha256()
    for path in sorted((PUBLIC_DIR / "static").rglob("*")):
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:10]


ASSET_VERSION = _asset_version()


def _shared_context(request: Request, current_group: str | None = None) -> dict[str, object]:
    return {
        "request": request,
        "group_meta": GROUP_META,
        "groups": WEB_GROUPS,
        "current_group": current_group,
        "group_counts": {group: len(get_group_operations(request.app, group)) for group in WEB_GROUPS},
        "current_year": datetime.now(UTC).year,
        "api_version": PROJECT_VERSION,
        "asset_version": ASSET_VERSION,
        "is_available": IS_AVAILABLE,
        "is_maintenance": IS_MAINTENANCE,
        "is_high_traffic": IS_HIGH_TRAFFIC,
        "date_available": DATE_AVAILABLE,
        "alternative_endpoint": ALTERNATIVE_ENDPOINT_URL,
        "maintenance_message": API_STATUS_MESSAGES[SERVICE_STATUS_KEY]["message"],
        "seo_description": "Interactive web interface for the Rone Arena API with endpoint forms, readable response tables, and cURL output.",
        "seo_keywords": "rone arena api, mobile legends data api, web ui, fastapi, openapi, response table",
        "base_url": BASE_URL,
        "is_debug": DEBUG,
        "api_url": API_URL.rstrip("/"),
        "is_analytics_host": bool(ANALYTICS_HOST) and (request.url.hostname or "").lower() == ANALYTICS_HOST.lower(),
    }


def _operations_by_group(app) -> dict[str, list[dict[str, object]]]:
    return {group: get_group_operations(app, group) for group in WEB_GROUPS}


def _showcase_products(operations_by_group: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    web_paths = {
        (str(operation["method"]), str(operation["api_path"])): str(operation["web_path"])
        for operations in operations_by_group.values()
        for operation in operations
    }
    return with_playground_links(web_paths)


def _normalize_path(value: str) -> str:
    normalized = value.rstrip("/")
    return normalized or "/"


@router.get(path="/", include_in_schema=False, response_class=HTMLResponse)
def landing_page(request: Request) -> HTMLResponse:
    context = _shared_context(request)
    if IS_AVAILABLE:
        operations_by_group = _operations_by_group(request.app)
        context.update(
            {
                "operations_by_group": operations_by_group,
                "endpoint_total": sum(len(operations) for operations in operations_by_group.values()),
                "products": _showcase_products(operations_by_group),
                "title": "Rone Arena API: Mobile Legends: Bang Bang game data as JSON",
                "web_title": "Home",
                "seo_description": "Free REST API for Mobile Legends: Bang Bang game data: heroes, win rates, builds, counters, academy guides, and player records, with an interactive playground.",
                "seo_keywords": "rone arena, mobile legends data, api docs, web playground, analytics api",
            }
        )
        return templates.TemplateResponse(request, "root/landing_page.html", context)

    if IS_MAINTENANCE:
        context.update(
            {
                "title": "Under Maintenance / Rone Arena API",
                "web_title": "Under Maintenance",
                "seo_description": "Rone Arena API is temporarily unavailable while under maintenance.",
                "seo_keywords": "rone arena api status, maintenance, service unavailable",
            }
        )
    else:
        context.update(
            {
                "title": "503 Service Unavailable / Rone Arena API",
                "web_title": "Service Unavailable",
                "seo_description": "Rone Arena API is temporarily unavailable due to high traffic.",
                "seo_keywords": "rone arena api status, service unavailable, high traffic",
            }
        )
    return templates.TemplateResponse(request, "root/landing_page.html", context, status_code=503)


@router.get(path="/showcase", include_in_schema=False, response_class=HTMLResponse, name="web.showcase")
def showcase_page(request: Request) -> HTMLResponse:
    context = _shared_context(request)
    context.update(
        {
            "title": "Showcase: projects built on the Rone Arena API",
            "web_title": "Showcase",
            "seo_description": "Projects the community built on the Rone Arena API, with the endpoints behind each page. Add your own project with one issue.",
            "seo_keywords": "rone arena api examples, arena academy, arena card, api integration example, showcase",
            "products": _showcase_products(_operations_by_group(request.app)),
            "submit_url": SUBMIT_URL,
            "entry_keys": ENTRY_KEYS,
            "entry_example": format_entry(SHOWCASE[0]),
            "llm_prompt": llm_prompt(context["base_url"]),
        }
    )
    return templates.TemplateResponse(request, "root/showcase_page.html", context)


@router.get(path="/web", include_in_schema=False)
def web_home() -> RedirectResponse:
    return RedirectResponse(url="/web/user", status_code=307)


@router.get(path="/web/{group}", include_in_schema=False, response_class=HTMLResponse)
def web_group_page(request: Request, group: str) -> HTMLResponse:
    if group not in WEB_GROUPS:
        raise HTTPException(status_code=404, detail="Web group not found")

    operations = get_group_operations(request.app, group)
    context = _shared_context(request, current_group=group)
    context.update(
        {
            "title": f"{GROUP_META[group]['title']} Endpoints / Rone Arena API & Web",
            "web_title": f"{GROUP_META[group]['title']} Endpoints",
            "subtitle": GROUP_META[group]["description"],
            "seo_description": f"Browse and execute {GROUP_META[group]['title']} endpoints from the Rone Arena API & Web interface.",
            "seo_keywords": f"rone arena api, {group} endpoints, openapi web ui",
            "operations": operations,
            "sidebar_operations": operations,
            "selected_web_path": None,
        }
    )
    return templates.TemplateResponse(request, "web/group_page.html", context)


@router.get(path="/web/{group}/{endpoint_path:path}", include_in_schema=False, response_class=HTMLResponse)
def web_endpoint_page(request: Request, group: str, endpoint_path: str) -> HTMLResponse:
    if group not in WEB_GROUPS:
        raise HTTPException(status_code=404, detail="Web group not found")

    all_operations = get_group_operations(request.app, group)
    normalized_path = _normalize_path(f"/web/{group}/{endpoint_path}")
    matched_operations = [
        operation
        for operation in all_operations
        if _normalize_path(str(operation["web_path"])) == normalized_path
    ]

    if not matched_operations:
        raise HTTPException(status_code=404, detail="Web endpoint not found")

    context = _shared_context(request, current_group=group)
    operation_summary = str(matched_operations[0].get("summary") or "Endpoint").strip()
    group_title = str(GROUP_META[group]["title"]).strip()
    context.update(
        {
            "title": f"{operation_summary} - {group_title} API / Rone Arena API & Web",
            "web_title": operation_summary,
            "subtitle": f"{group_title} endpoint. Fill in the form, execute it, and inspect the response.",
            "seo_description": f"Execute and inspect a {GROUP_META[group]['title']} endpoint from the Rone Arena API web interface.",
            "seo_keywords": f"rone arena api endpoint, {group}, curl, readable response",
            "operations": matched_operations,
            "sidebar_operations": all_operations,
            "selected_web_path": normalized_path,
        }
    )
    return templates.TemplateResponse(request, "web/group_page.html", context)
