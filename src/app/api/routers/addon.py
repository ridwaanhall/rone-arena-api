from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.core.exceptions import AppError
from app.services.addon import fetch_ip_get
from app.schemas.addon import AddonIpResponse, AddonWinRateResponse
from app.utils.client_ip import as_ipv4, extract_client_ip, get_edge_geo

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
    # Presence, types and ranges are enforced by the Query constraints above;
    # what remains are the rules that depend on more than one value.
    def bad_request(message: str) -> AppError:
        return AppError(
            status_code=400,
            code="BAD_REQUEST",
            message=message,
            extra={"match_now": match_now, "wr_now": wr_now, "wr_future": wr_future, "required_no_lose_matches": None},
        )

    if wr_future <= wr_now:
        raise bad_request("The target win rate (wr-future) must be greater than the current win rate (wr-now).")
    if wr_future == 100:
        raise bad_request(f"It is not possible to reach a {wr_future}% win rate with a finite number of matches.")

    # Solve (wins + x) / (matches + x) = target for x consecutive wins. With
    # wr_now < wr_future < 100 the result is never negative.
    current_wins = match_now * wr_now / 100.0
    target = wr_future / 100.0
    required_matches = math.ceil((current_wins - match_now * target) / (target - 1.0))

    return {
        "status": "success",
        "match_now": match_now,
        "wr_now": wr_now,
        "wr_future": wr_future,
        "required_no_lose_matches": required_matches,
        "message": (
            f"To achieve a win rate of {wr_future}%, "
            f"you need {required_matches} consecutive wins without any losses."
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
)
def ip(request: Request) -> object:
    client_ip = extract_client_ip(request, public_only=True)
    if client_ip and not as_ipv4(client_ip):
        # The upstream lookup only understands IPv4 and answers an IPv6 address
        # with code -1. Use Cloudflare's own geolocation of the visitor instead;
        # without it, let the upstream locate the calling server.
        geo = get_edge_geo()
        if geo:
            return {"code": 0, "msg": "ok", "data": {**geo, "lang": "en"}}
        client_ip = None
    elif client_ip:
        client_ip = as_ipv4(client_ip)
    return fetch_ip_get("c/ip", client_ip)
