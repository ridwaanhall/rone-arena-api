from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import LIVECHAT_LINK, CONTACT_FORM_LINK
from app.core.exceptions import AppError


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_error_code(status_code: int, message: str) -> str:
    normalized = (message or "").lower()
    if "failed to fetch data" in normalized:
        return "UPSTREAM_REQUEST_FAILED"
    if status_code == 503:
        return "SERVICE_UNAVAILABLE"
    if status_code == 400:
        return "BAD_REQUEST"
    if status_code == 404:
        return "RESOURCE_NOT_FOUND"
    if status_code == 429:
        return "TOO_MANY_REQUESTS"
    if status_code >= 500:
        return "INTERNAL_SERVER_ERROR"
    return "REQUEST_FAILED"


def to_error_message(status_code: int, message: str) -> str:
    normalized = (message or "").lower()
    if "failed to fetch data" in normalized:
        return "We could not process your request right now due to an upstream service issue. Please contact support."
    if status_code == 503:
        return message or "Service is temporarily unavailable due to high traffic."
    if status_code >= 500:
        return "An internal server error occurred. Please contact support."
    return message or "Request failed."


def safe_error_payload(message: str, status_code: int, details: Any = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "error",
        "code": to_error_code(status_code, message),
        "message": to_error_message(status_code, message),
        "timestamp": timestamp_utc(),
        "support": {
            "livechat": LIVECHAT_LINK,
            "contact": CONTACT_FORM_LINK,
        },
    }

    if "failed to fetch data" not in (message or "").lower() and details is not None:
        payload["details"] = details
    return payload


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    payload = safe_error_payload(exc.message, exc.status_code, exc.details)
    payload.update(exc.extra)
    payload["code"] = exc.code
    return JSONResponse(status_code=exc.status_code, content=payload)


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    payload = safe_error_payload("An internal server error occurred.", 500)
    payload["details"] = {"type": type(exc).__name__}
    return JSONResponse(status_code=500, content=payload)
