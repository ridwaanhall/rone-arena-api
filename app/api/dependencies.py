from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import (
    ALTERNATIVE_ENDPOINT_URL,
    API_STATUS_MESSAGES,
    IS_AVAILABLE,
    SERVICE_STATUS_KEY,
)
from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder


user_bearer = HTTPBearer(auto_error=False)


def require_api_available() -> None:
    if IS_AVAILABLE:
        return

    status_info = API_STATUS_MESSAGES[SERVICE_STATUS_KEY]
    details: dict[str, object] = {
        "available_endpoints": status_info["available_endpoints"],
    }
    # Only high traffic has somewhere else to send callers; during maintenance
    # the alternative host is down for the same reason. Keyed off the effective
    # status so that maintenance still wins when both flags are set.
    if SERVICE_STATUS_KEY == "limited":
        details["alternative_endpoint"] = ALTERNATIVE_ENDPOINT_URL

    raise AppError(
        status_code=503,
        code="SERVICE_UNAVAILABLE",
        message=cast(str, status_info["message"]),
        details=details,
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
