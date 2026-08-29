from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.errors import AppError
from app.services.addon import fetch_ip_get
from fastapi import Request
from app.schemas.addon import AddonIpResponse, AddonWinRateResponse
from app.utils.client_ip import extract_client_ip

router = APIRouter(prefix="/api/addon", tags=["addon"])


@router.get(
    path="/win-rate-calculator",
    name="api.addon.win_rate_calculator",
    response_model=AddonWinRateResponse,
    summary="Win Rate Calculator for Consecutive Wins",
    description=(
        "Calculate the number of consecutive wins required to reach a target win rate "
        "based on current matches and current win rate.\n\n"
        "Query parameters:\n"
        "- **match-now**: Current total number of matches played (minimum: 0).\n"
        "- **wr-now**: Current win rate in percent (range: 0-100).\n"
        "- **wr-future**: Target win rate in percent. Must be greater than current win rate and between 0-100.\n\n"
        "The response includes win rate calculation data:\n"
        "- **status**: Response status (e.g., 'success').\n"
        "- **match_now**: Current total matches played.\n"
        "- **wr_now**: Current win rate.\n"
        "- **wr_future**: Target win rate.\n"
        "- **required_no_lose_matches**: Number of consecutive wins required without losses to reach the target win rate.\n"
        "- **message**: Explanation message summarizing the result.\n\n"
        "This endpoint is useful for:\n"
        "- Calculating how many consecutive wins are needed to reach a desired win rate.\n"
        "- Helping players set realistic performance goals.\n"
        "- Providing analytics for win rate progression."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "match_now": 100,
                        "wr_now": 50,
                        "wr_future": 75,
                        "required_no_lose_matches": 100,
                        "message": "To achieve a win rate of 75.0%, you need 100 consecutive wins without any losses."
                    }
                }
            }
        }
    }
)
def win_rate(
    match_now: Annotated[
        int,
        Query(
            alias="match-now",
            title="Current Matches Played",
            description="Current total number of matches played. Must be a non-negative integer.",
            ge=0,
        ),
    ],
    wr_now: Annotated[
        float,
        Query(
            alias="wr-now",
            title="Current Win Rate",
            description="Current win rate in percent. Must be a value between 0 and 100.",
            ge=0,
            le=100,
        ),
    ],
    wr_future: Annotated[
        float,
        Query(
            alias="wr-future",
            title="Target Win Rate",
            description="Target win rate in percent. Must be greater than the current win rate and between 0 and 100.",
            gt=0,
            le=100,
        ),
    ],
) -> object:
    missing_params = [
        param
        for param, value in [("match-now", match_now), ("wr-now", wr_now), ("wr-future", wr_future)]
        if value is None or value == ""
    ]
    if missing_params:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=(
                f"Missing required parameter(s): {', '.join(missing_params)}. "
                "Please provide all required parameters: match-now, wr-now, and wr-future."
            ),
            extra={
                "match_now": match_now,
                "wr_now": wr_now,
                "wr_future": wr_future,
                "required_no_lose_matches": None,
            },
        )

    try:
        if "." in str(match_now):
            raise ValueError("match-now must be an integer (no decimals allowed).")
        match_now_int = int(str(match_now))
        wr_now_float = float(str(wr_now))
        wr_future_float = float(str(wr_future))
    except ValueError:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="Invalid input. Ensure match-now is an integer and wr-now, wr-future are numeric values.",
            extra={
                "match_now": match_now,
                "wr_now": wr_now,
                "wr_future": wr_future,
                "required_no_lose_matches": None,
            },
        )

    if match_now_int < 0:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="match-now must be a non-negative integer.",
            extra={
                "match_now": match_now_int,
                "wr_now": wr_now_float,
                "wr_future": wr_future_float,
                "required_no_lose_matches": None,
            },
        )

    if not (0 <= wr_now_float <= 100) or not (0 < wr_future_float <= 100):
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="Win rates must be between 0 and 100 (wr-future must be greater than 0).",
            extra={
                "match_now": match_now_int,
                "wr_now": wr_now_float,
                "wr_future": wr_future_float,
                "required_no_lose_matches": None,
            },
        )

    if wr_future_float <= wr_now_float:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="The target win rate (wr-future) must be greater than the current win rate (wr-now).",
            extra={
                "match_now": match_now_int,
                "wr_now": wr_now_float,
                "wr_future": wr_future_float,
                "required_no_lose_matches": None,
            },
        )

    current_wins = match_now_int * wr_now_float / 100.0
    wr_future_ratio = wr_future_float / 100.0
    denominator = wr_future_ratio - 1.0
    numerator = current_wins - match_now_int * wr_future_ratio

    if denominator == 0:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=f"It is not possible to reach a {wr_future_float}% win rate with a finite number of matches.",
            extra={
                "match_now": match_now_int,
                "wr_now": wr_now_float,
                "wr_future": wr_future_float,
                "required_no_lose_matches": None,
            },
        )

    required_matches = numerator / denominator
    required_matches_int = int(required_matches) + (1 if required_matches % 1 > 0 else 0)

    if required_matches_int < 0:
        raise AppError(
            status_code=400,
            code="BAD_REQUEST",
            message="The target win rate cannot be achieved with only consecutive wins from your current record.",
            extra={
                "match_now": match_now_int,
                "wr_now": wr_now_float,
                "wr_future": wr_future_float,
                "required_no_lose_matches": None,
            },
        )

    return {
        "status": "success",
        "match_now": match_now_int,
        "wr_now": wr_now_float,
        "wr_future": wr_future_float,
        "required_no_lose_matches": required_matches_int,
        "message": (
            f"To achieve a win rate of {wr_future_float}%, "
            f"you need {required_matches_int} consecutive wins without any losses."
        ),
    }


@router.get(
    path="/ip",
    name="api.addon.ip_location",
    response_model=AddonIpResponse,
    summary="Check IP address location details",
    description=(
        "Retrieves geographic information associated with a given IP address. "
        "No parameters required.\n\n"
        "The response includes IP location data:\n"
        "- **code**: Response code (e.g., 0).\n"
        "- **msg**: Status message (e.g., 'ok').\n"
        "- **data**:\n"
        "    - **city**: City name (e.g., 'Yogyakarta').\n"
        "    - **state**: State or region (e.g., 'Yogyakarta').\n"
        "    - **country**: Country code (e.g., 'id').\n"
        "    - **lang**: Language code (e.g., 'en').\n\n"
        "This endpoint is useful for:\n"
        "- Identifying approximate geographic location of an IP address.\n"
        "- Supporting analytics and personalization.\n"
        "- Performing security checks and contextual validation."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "data": {
                            "city": "Yogyakarta",
                            "country": "id",
                            "lang": "en",
                            "state": "Yogyakarta"
                        },
                        "msg": "ok"
                    }
                }
            }
        }
    },
    deprecated=True,
)
async def ip(request: Request):
    client_ip = extract_client_ip(request, public_only=True)
    return fetch_ip_get("c/ip", client_ip)
