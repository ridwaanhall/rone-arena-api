from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # <-- 1. IMPORT ADDED HERE

from app.core.config import (
    ALTERNATIVE_ENDPOINT_URL,
    API_STATUS_MESSAGES,
    DEBUG,
    IS_AVAILABLE,
    SERVICE_STATUS_KEY,
    PROJECT_VERSION,
)

from app.api.routers.root import router as root_router
from app.api.routers.heroes import router as heroes_router
from app.api.routers.academy import router as academy_router
from app.api.routers.addon import router as addon_router
from app.api.routers.user import router as user_router
from app.web.routers.root import router as web_router
from app.web.routers.blog import router as blog_router

from app.core.errors import AppError, app_error_handler, safe_error_payload, unhandled_error_handler

app = FastAPI(
    debug=DEBUG,
    title="Rone Arena API",
    summary="Unofficial community data API for the game Mobile Legends: Bang Bang, providing hero data, analytics, academy resources, user endpoints, and utility tools.",
    description=(
        "Rone Arena API is a comprehensive community data API for the game Mobile Legends: Bang Bang, built for developers, analysts, and fans who need structured and reliable game data. "
        "It provides access to hero information including listings, rankings, positions, detailed statistics, performance trends, skill combos, counters, compatibility, and hero relationships. "
        "In addition, the API includes academy resources such as roles, equipment, emblems, spells, builds, lane distribution, win rate timelines, and performance ratings to support deeper analysis and game understanding. "
        "User-related endpoints are available for authentication, profile data, match history, and player statistics, while utility tools such as win rate calculators and IP lookup enhance integration capabilities. "
        "The API is designed with a consistent and RESTful structure, supports flexible hero identifiers using either ID or name, and delivers standardized responses optimized for seamless integration into applications, dashboards, and analytics systems.\n\n"
        "**Disclaimer:** Rone Arena is an unofficial, community-maintained project. It is not affiliated with, endorsed by, sponsored by, or associated with Shanghai Moonton Technology Co., Ltd. "
        "\"Mobile Legends: Bang Bang\", \"MLBB\", and all related names, marks, logos, and in-game assets are trademarks of their respective owners. "
        "Data is sourced from publicly accessible endpoints and provided for informational, educational, and analytical purposes only."
    ),
    version=PROJECT_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
    },
    contact={
        "name": "RoneAI",
        "url": "https://rone.dev/#Contact",
        "email": "founder@rone.dev",
    },
    license_info={
        "name": "BSD 3-Clause License",
        "url": "https://github.com/ridwaanhall/rone-arena-api/blob/main/LICENSE",
    },
    openapi_tags=[
        {
            "name": "user",
            "description": "Authentication and player-related data.",
        },
        {
            "name": "heroes",
            "description": "Hero data, stats, and in-game analytics.",
        },
        {
            "name": "academy",
            "description": "Game guides, builds, and reference data.",
        },
        {
            "name": "addon",
            "description": "Utility tools and extra features.",
        },
    ]
)

# ==========================================
# 2. CORS MIDDLEWARE ADDED HERE
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all domains, including http://localhost:3000
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

def _inline_enum_defaults_in_parameters(schema: dict[str, object]) -> None:
    components = schema.get("components", {})
    if not isinstance(components, dict):
        return

    component_schemas = components.get("schemas", {})
    if not isinstance(component_schemas, dict):
        return

    paths = schema.get("paths", {})
    if not isinstance(paths, dict):
        return

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue

        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            parameters = operation.get("parameters", [])
            if not isinstance(parameters, list):
                continue

            for parameter in parameters:
                if not isinstance(parameter, dict):
                    continue

                param_schema = parameter.get("schema", {})
                if not isinstance(param_schema, dict):
                    continue

                ref = param_schema.get("$ref")
                has_default = "default" in param_schema
                if not isinstance(ref, str) or not has_default:
                    continue

                prefix = "#/components/schemas/"
                if not ref.startswith(prefix):
                    continue

                component_name = ref[len(prefix):]
                component_schema = component_schemas.get(component_name, {})
                if not isinstance(component_schema, dict) or "enum" not in component_schema:
                    continue

                inlined_schema = {
                    "type": component_schema.get("type", "string"),
                    "enum": deepcopy(component_schema.get("enum", [])),
                }

                for key in ("title", "description", "default"):
                    if key in param_schema:
                        inlined_schema[key] = deepcopy(param_schema[key])

                parameter["schema"] = inlined_schema


def _resolve_schema_ref(
    schema: dict[str, object],
    component_schemas: dict[str, object],
) -> dict[str, object]:
    ref = schema.get("$ref")
    if not isinstance(ref, str):
        return schema

    prefix = "#/components/schemas/"
    if not ref.startswith(prefix):
        return schema

    component_name = ref[len(prefix):]
    target = component_schemas.get(component_name, {})
    if isinstance(target, dict):
        return target
    return schema


def _order_example_by_schema(
    example_data: object,
    schema: dict[str, object],
    component_schemas: dict[str, object],
) -> object:
    resolved = _resolve_schema_ref(schema, component_schemas)

    if isinstance(example_data, dict):
        properties = resolved.get("properties", {})
        if isinstance(properties, dict) and properties:
            ordered: dict[str, object] = {}

            for key, child_schema in properties.items():
                if key not in example_data:
                    continue
                child = child_schema if isinstance(child_schema, dict) else {}
                ordered[key] = _order_example_by_schema(example_data[key], child, component_schemas)

            for key, value in example_data.items():
                if key in ordered:
                    continue
                ordered[key] = value

            return ordered

        return {
            key: _order_example_by_schema(value, {}, component_schemas)
            for key, value in example_data.items()
        }

    if isinstance(example_data, list):
        item_schema = resolved.get("items", {})
        item_schema_dict = item_schema if isinstance(item_schema, dict) else {}
        return [
            _order_example_by_schema(item, item_schema_dict, component_schemas)
            for item in example_data
        ]

    return example_data


def _normalize_component_schema_examples(schema: dict[str, object]) -> None:
    components = schema.get("components", {})
    if not isinstance(components, dict):
        return

    component_schemas = components.get("schemas", {})
    if not isinstance(component_schemas, dict):
        return

    for component_schema in component_schemas.values():
        if not isinstance(component_schema, dict):
            continue

        if "example" in component_schema:
            component_schema["example"] = _order_example_by_schema(
                component_schema["example"],
                component_schema,
                component_schemas,
            )


def custom_openapi() -> dict[str, object]:
    if app.openapi_schema is not None:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
        separate_input_output_schemas=app.separate_input_output_schemas,
    )

    _inline_enum_defaults_in_parameters(openapi_schema)
    _normalize_component_schema_examples(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.middleware("http")
async def maintenance_mode_guard(request: Request, call_next):
    allowed_when_limited_prefixes = ("/blog", "/images/blog")
    if IS_AVAILABLE or request.url.path == "/" or request.url.path.startswith(allowed_when_limited_prefixes):
        return await call_next(request)

    status_info = API_STATUS_MESSAGES[SERVICE_STATUS_KEY]
    available_endpoints = status_info.get("available_endpoints", ["/"])
    if not isinstance(available_endpoints, list):
        available_endpoints = ["/"]

    details: dict[str, object] = {"available_endpoints": available_endpoints}
    if SERVICE_STATUS_KEY == "limited":
        details["alternative_endpoint"] = ALTERNATIVE_ENDPOINT_URL

    if request.url.path.startswith("/api"):
        payload = safe_error_payload(str(status_info["message"]), 503, details)
        payload["code"] = "SERVICE_UNAVAILABLE"
        return JSONResponse(status_code=503, content=payload)

    return RedirectResponse(url="/", status_code=307)

# api routers
app.include_router(root_router)
app.include_router(heroes_router)
app.include_router(academy_router)
app.include_router(user_router)
app.include_router(addon_router)

# web routes
app.include_router(web_router)
app.include_router(blog_router)

# static assets
_STATIC_IMAGES_DIR = Path(__file__).resolve().parents[1] / "images"
app.mount("/images", StaticFiles(directory=str(_STATIC_IMAGES_DIR)), name="images")


# exception handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_error_handler)  # type: ignore[arg-type]


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    payload = safe_error_payload(str(exc.detail), exc.status_code)
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    payload = safe_error_payload("Validation failed.", 422, exc.errors())
    payload["code"] = "VALIDATION_ERROR"
    return JSONResponse(status_code=422, content=payload)