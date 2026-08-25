from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import ALTERNATIVE_ENDPOINT_URL, API_STATUS_MESSAGES, IS_AVAILABLE
from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder


user_bearer = HTTPBearer(auto_error=False)


def require_api_available() -> None:
    if IS_AVAILABLE:
        return

    status_info = API_STATUS_MESSAGES["limited"]
    raise AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message=cast(str, status_info["message"]),
        details={
            "available_endpoints": status_info["available_endpoints"],
            "alternative_endpoint": ALTERNATIVE_ENDPOINT_URL,
        },
    )


def require_user_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(user_bearer)],
) -> str:
    if credentials and credentials.credentials:
        return UpstreamHeaderBuilder.normalize_auth_token(credentials.credentials)

    raise AppError(
        status_code=401,
        code="UNAUTHORIZED",
        message="Authorization header is required",
        details="Provide Authorization: Bearer <jwt>.",
    )
