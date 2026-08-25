from __future__ import annotations

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
    PROJECT_VERSION,
    BASE_URL,
    PROD_URL_STANDARD,
    PROD_URL_HIGH_VOLUME,
)
from app.web.openapi_catalog import GROUP_META, WEB_GROUPS, get_group_operations

router = APIRouter(tags=["web"])

_TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _shared_context(request: Request, current_group: str | None = None) -> dict[str, object]:
    return {
        "request": request,
        "group_meta": GROUP_META,
        "groups": WEB_GROUPS,
        "current_group": current_group,
        "current_year": datetime.now(UTC).year,
        "api_version": PROJECT_VERSION,
        "is_available": IS_AVAILABLE,
        "alternative_endpoint": ALTERNATIVE_ENDPOINT_URL,
        "maintenance_message": API_STATUS_MESSAGES["limited"]["message"],
        "seo_description": "Interactive web interface for the Rone Arena API with endpoint forms, readable response tables, and cURL output.",
        "seo_keywords": "rone arena api, mobile legends data api, web ui, fastapi, openapi, response table",
        "base_url": BASE_URL,
        "is_debug": DEBUG,
        "debug_api_base": "http://127.0.0.1:8000/api" if DEBUG else None,
        "prod_url_standard": PROD_URL_STANDARD.rstrip("/"),
        "prod_url_high_volume": PROD_URL_HIGH_VOLUME.rstrip("/"),
        "is_analytics_host": bool(ANALYTICS_HOST) and (request.url.hostname or "").lower() == ANALYTICS_HOST.lower(),
    }


def _normalize_path(value: str) -> str:
    normalized = value.rstrip("/")
    return normalized or "/"


@router.get(path="/", include_in_schema=False, response_class=HTMLResponse)
def landing_page(request: Request) -> HTMLResponse:
    context = _shared_context(request)
    if IS_AVAILABLE:
        context.update(
            {
                "title": "Home / Rone Arena API & Web",
                "web_title": "Home",
                "seo_description": "Modern landing page for the Rone Arena API. Access docs and a full interactive web playground for all endpoints.",
                "seo_keywords": "rone arena, mobile legends data, api docs, web playground, analytics api",
            }
        )
        return templates.TemplateResponse(request, "root/landing_page.html", context)

    context.update(
        {
            "title": "503 Service Unavailable / Rone Arena API",
            "web_title": "Service Unavailable",
            "seo_description": "Rone Arena API is temporarily unavailable due to high traffic.",
            "seo_keywords": "rone arena api status, service unavailable, high traffic",
        }
    )
    return templates.TemplateResponse(request, "root/landing_page.html", context, status_code=503)


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
            "title": f"{operation_summary} - {group_title[:-1] if group_title.endswith('s') else group_title} Endpoint / Rone Arena API & Web",
            "web_title": f"{group_title[:-1] if group_title.endswith('s') else group_title} Endpoint",
            "subtitle": "Interactive request form for this API endpoint.",
            "seo_description": f"Execute and inspect a {GROUP_META[group]['title']} endpoint from the Rone Arena API web interface.",
            "seo_keywords": f"rone arena api endpoint, {group}, curl, readable response",
            "operations": matched_operations,
            "sidebar_operations": all_operations,
            "selected_web_path": normalized_path,
        }
    )
    return templates.TemplateResponse(request, "web/group_page.html", context)
