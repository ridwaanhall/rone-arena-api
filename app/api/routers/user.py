from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import require_api_available, require_user_jwt

from app.services.user import fetch_user_post, fetch_user_actgateway, fetch_user_actgateway_post

from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder
from app.core.errors import _hero_id_or_404
from app.core.enums import LanguageEnum, VisibilityEnum
from app.schemas.user import (
    UserAuthSimpleResponse,
    UserFriendsResponse,
    UserFrequentHeroesResponse,
    UserInfoResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserMatchDetailsResponse,
    UserMatchesResponse,
    UserPrivacySettingsResponse,
    UserSendVcRequest,
    UserSeasonResponse,
    UserStatsResponse,
    UserMatchesByHeroResponse,
)

from typing import Annotated

router = APIRouter(prefix="/api/user", tags=["user"], dependencies=[Depends(require_api_available)])


def _require_dict_response(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise AppError(
            status_code=502,
            code="UPSTREAM_INVALID_RESPONSE",
            message="Failed to fetch data",
            details="Upstream response format is invalid.",
        )
    return data


def _require_key(response_data: dict[str, object], key: str) -> None:
    if key not in response_data:
        raise AppError(
            status_code=502,
            code="UPSTREAM_INVALID_RESPONSE",
            message="Failed to fetch data",
            details=f"Upstream response missing required field: {key}.",
        )


@router.post(
    path="/auth/send-vc",
    name="api.user.send_verification_code",
    response_model=UserAuthSimpleResponse,
    summary="Send Verification Code",
    description=(
        "Send an in-game verification code to the player's account, valid for 5 mins. "
        "This endpoint is part of the authentication flow and is used to validate ownership of a game account.\n\n"
        "Request body:\n"
        "- **role_id**: Player role identifier (Game ID).\n"
        "- **zone_id**: Server zone identifier (Server ID).\n\n"
        "The response confirms whether the verification code was successfully dispatched:\n"
        "- **code**: Status code (0 indicates success).\n"
        "- **data**: Empty string (no payload returned).\n"
        "- **msg**: Message string (e.g., 'ok').\n\n"
        "Useful for account authentication flows, linking user identity, and validating account ownership."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "data": "",
                        "msg": "ok"
                    }
                }
            }
        }
    }
)
def send_vc(
    body: UserSendVcRequest,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header()
    payload = {
        "roleId": body.role_id,
        "zoneId": body.zone_id,
    }
    return fetch_user_post("base/sendVc", headers, payload)


@router.post(
    path="/auth/login",
    name="api.user.login",
    response_model=UserLoginResponse,
    summary="Login with Verification Code",
    description=(
        "Authenticate the player using a verification code to obtain a JWT and session token. "
        "This endpoint completes the account login flow, establishes a secure session, and enables authorized access "
        "to user-specific resources.\n\n"
        "Request body:\n"
        "- **role_id**: Player role identifier.\n"
        "- **zone_id**: Server zone identifier.\n"
        "- **vc**: Verification code sent to the player via in-game mail, valid 5 mins.\n\n"
        "The response includes authentication details:\n"
        "- **code**: Status code (0 indicates success).\n"
        "- **data.jwt**: JSON Web Token used for subsequent authenticated requests.\n"
        "- **data.token**: Session token string.\n"
        "- **data.roleid**: Player role ID.\n"
        "- **data.zoneid**: Player zone ID.\n"
        "- **data.time**: Timestamp of login.\n"
        "- **data.module, name, email, mobile, open_id**: Metadata fields (may be empty depending on account).\n\n"
        "The response confirms successful login and provides the credentials required for accessing other user endpoints."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "data": {
                            "email": "",
                            "jwt": "eyJhbGciOiJI...REDACTED",
                            "mobile": "",
                            "module": "",
                            "name": "",
                            "open_id": "",
                            "roleid": 1234567890,
                            "time": 1774975992,
                            "token": "MTc3ND...REDACTED",
                            "zoneid": 1234
                        },
                        "msg": "ok"
                    }
                }
            }
        }
    }
)
def login(
    body: UserLoginRequest,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header()
    payload = {
        "roleId": body.role_id,
        "zoneId": body.zone_id,
        "vc": body.vc,
        "referer": "academy",
        "type": "web",
    }
    return fetch_user_post("base/login", headers, payload)


@router.post(
    path="/auth/logout",
    name="api.user.logout",
    response_model=UserAuthSimpleResponse,
    summary="Logout",
    description=(
        "Invalidate the player's session using the JWT obtained from `/api/user/auth/login`. "
        "This endpoint terminates the current authenticated session, ensuring that the JWT can no longer be used "
        "for authorized requests.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "The response confirms whether the logout was successful:\n"
        "- **code**: Status code (0 indicates success).\n"
        "- **data**: Empty string (no payload returned).\n"
        "- **msg**: Message string (e.g., 'ok').\n\n"
        "Note: Although the login response also includes a `token` field, only the JWT is required for logout. "
        "The server uses the JWT to invalidate the session."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "data": "",
                        "msg": "ok"
                    }
                }
            }
        }
    }
)
def logout(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        jwt=jwt
    )
    payload = {}
    return fetch_user_post("base/logout", headers, payload)


@router.get(
    path="/info",
    name="api.user.info",
    response_model=UserInfoResponse,
    summary="User Info",
    description=(
        "Retrieve the authenticated player's base profile information using a valid JWT. "
        "Supports query parameter for localization (`lang`). Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes player details:\n"
        "- **avatar**: Avatar image URL.\n"
        "- **name**: Display name.\n"
        "- **level**: Current player level.\n"
        "- **rank_level**: Current rank level.\n"
        "- **history_rank_level**: Highest historical rank level.\n"
        "- **reg_country**: Registered country code.\n"
        "- **roleId**: Player role identifier.\n"
        "- **zoneId**: Server zone identifier.\n\n"
        "Useful for displaying identity card information, verifying account ownership, "
        "and populating player profile data in client applications."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "data": {
                            "avatar": "https://akmpicture.youngjoygame.com/dist/face/57060/66/96/1149309666_26_new_9ced56d6-3625-48c3-85d1-0b862a2044e7.jpg",
                            "history_rank_level": 9999,
                            "level": 200,
                            "name": "SAYA AKAN LAWAN",
                            "rank_level": 8000,
                            "reg_country": "ID",
                            "roleId": 1234567890,
                            "zoneId": 123456
                        },
                        "msg": "ok"
                    }
                }
            }
        }
    }
)
def user_info(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_actid="2728785",
        x_appid="2713644",
        jwt=jwt
    )
    payload = {}
    response = _require_dict_response(fetch_user_post("base/getBaseInfo", headers, payload))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/stats",
    name="api.user.stats",
    response_model=UserStatsResponse,
    summary="User Statistics",
    description=(
        "Retrieve the authenticated player's overall statistics using a valid JWT. "
        "Supports query parameter for localization (`lang`). Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes general player statistics:\n"
        "- **wc**: Win Count (total matches won).\n"
        "- **tc**: Total Count (total matches played).\n"
        "- **as**: Average Score (overall performance rating, as/100).\n"
        "- **gt**: Game Time (total play time duration in hours).\n"
        "- **mvpc**: MVP Count (number of times player earned MVP).\n"
        "- **wsc**: Win Streak Count (longest consecutive wins).\n\n"
        "Hero-specific highlights:\n"
        "- **mo**: Most Often (hero most damage dealt).\n"
        "- **hk**: Highest Kills (hero with the most kills).\n"
        "- **ma**: Most Assists (hero contributing the most assists).\n"
        "- **ms**: Most Score (hero with the highest accumulated score).\n"
        "- **mdt**: Most Damage Taken (hero absorbing the most damage).\n"
        "- **mg**: Most Gold (hero earning the most gold).\n"
        "- **mtd**: Most Total Damage (hero dealing the most damage overall).\n\n"
        "Each hero highlight includes metadata such as:\n"
        "    - **v**: Value or statistic for the highlight. if `ms` is used, it calculates `v/100`.\n"
        "    - **ts**: Timestamp of the highlight.\n"
        "    - **hid**: Hero ID.\n"
        "    - **n**: Hero name.\n"
        "    - **ix**: Hero image URL.\n"
        "    - **i2x**: Large hero image URL.\n"
        "    - **bid**: Battle ID reference.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing overall player performance.\n"
        "- Identifying favorite heroes.\n"
        "- Showcasing personal achievements in Mobile Legends: Bang Bang."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "b506b47e790797eb1f9762d2f1586496",
                        "data": {
                            "wc": 188,
                            "tc": 308,
                            "as": 762.3552,
                            "gt": 77.95,
                            "mvpc": 73,
                            "wsc": 11,
                            "mo": {
                                "v": 112848,
                                "ts": 1726010389,
                                "hid": 36,
                                "bid": 4110381620662451700,
                                "sid": 0,
                                "hid_e": {
                                    "id": 36,
                                    "n": "Aurora",
                                    "ix": "https://akmweb.youngjoygame.com/web/gms/image/ed2295c60bd772b89b7bdbbc2aee6095.png",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_58b97db6a5c286059057d42289612b16.jpg"
                                },
                                "bid_s": "4110381620662451526"
                            },
                            "hk": {
                                "v": 25,
                                "ts": 1672500616,
                                "hid": 84,
                                "bid": 4108435467847910000,
                                "sid": 0,
                                "hid_e": {
                                    "id": 84,
                                    "n": "Ling",
                                    "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_af4312bae7aa443129b46a17b4dce3a6.png",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_f76a7dfe805afa316e5ec44295b75772.jpg"
                                },
                                "bid_s": "4108435467847910024"
                            },
                            "ma": {
                                "v": 31,
                                "ts": 1725653347,
                                "hid": 20,
                                "bid": 4109721990994840000,
                                "sid": 0,
                                "hid_e": {
                                    "id": 20,
                                    "n": "Lolita",
                                    "ix": "https://akmweb.youngjoygame.com/web/gms/image/ce1c7af1a946f70585e40296ba85c9c0.jpg",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_1bc4973e512cf4958fe639e12391666e.jpg"
                                },
                                "bid_s": "4109721990994840266"
                            },
                            "ms": {
                                "v": 1330,
                                "ts": 1715555863,
                                "hid": 84,
                                "bid": 4110821683001146000,
                                "sid": 0,
                                "hid_e": {
                                    "id": 84,
                                    "n": "Ling",
                                    "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_af4312bae7aa443129b46a17b4dce3a6.png",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_f76a7dfe805afa316e5ec44295b75772.jpg"
                                },
                                "bid_s": "4110821683001146109"
                            },
                            "mdt": {
                                "v": 372063,
                                "ts": 1727227888,
                                "hid": 20,
                                "bid": 4109978035471765500,
                                "sid": 0,
                                "hid_e": {
                                    "id": 20,
                                    "n": "Lolita",
                                    "ix": "https://akmweb.youngjoygame.com/web/gms/image/ce1c7af1a946f70585e40296ba85c9c0.jpg",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_1bc4973e512cf4958fe639e12391666e.jpg"
                                },
                                "bid_s": "4109978035471765660"
                            },
                            "mg": {
                                "v": 22282,
                                "ts": 1718939040,
                                "hid": 84,
                                "bid": 4116060748536699000,
                                "sid": 0,
                                "hid_e": {
                                    "id": 84,
                                    "n": "Ling",
                                    "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_af4312bae7aa443129b46a17b4dce3a6.png",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_f76a7dfe805afa316e5ec44295b75772.jpg"
                                },
                                "bid_s": "4116060748536698631"
                            },
                            "mtd": {
                                "v": 27152,
                                "ts": 1719290587,
                                "hid": 65,
                                "bid": 4110233968270030300,
                                "sid": 0,
                                "hid_e": {
                                    "id": 65,
                                    "n": "Claude",
                                    "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_7ed528f154dd4f460c59361ab0ed7942.png",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_1edf19b0839ffd2bffb60b4ee4953239.jpg"
                                },
                                "bid_s": "4110233968270030438"
                            },
                            "sids": [40, 39, 38, 37]
                        }
                    }
                }
            }
        }
    }
)
def user_stats(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {}
    response = _require_dict_response(fetch_user_actgateway("battlereport/stats", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/privacy/settings",
    name="api.user.privacy_settings",
    response_model=UserPrivacySettingsResponse,
    summary="User Privacy Settings",
    description=(
        "Retrieve the authenticated player's privacy settings using a valid JWT. "
        "Supports query parameter for localization (`lang`). Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes:\n"
        "- **popup_shown**: Whether the privacy popup has been shown to the user.\n"
        "- **privacy**: Current privacy state (true/false)."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "410b98229c4a2ab35edddb49df774922",
                        "data": {
                            "popup_shown": True,
                            "privacy": False,
                        },
                    }
                }
            }
        }
    }
)
def user_privacy_settings(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {}
    response = _require_dict_response(fetch_user_actgateway("battlereport/privacy/settings", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.post(
    path="/privacy/settings",
    name="api.user.update_privacy_settings",
    response_model=UserPrivacySettingsResponse,
    summary="Update User Privacy Settings",
    description=(
        "Update the authenticated player's privacy settings using a valid JWT. "
        "Supports query parameter for localization (`lang`). Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **visibility**: Visibility mode. Use `visible` to allow friends to view your profile, "
        "and `invisible` to hide your profile from friends. This parameter is required.\n"
        "- **lang**: Language code for localized content (default: `en`)."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "410b98229c4a2ab35edddb49df774922",
                        "data": {
                            "popup_shown": True,
                            "privacy": False,
                        },
                    }
                }
            }
        }
    }
)
def user_update_privacy_settings(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    visibility: Annotated[
        VisibilityEnum,
        Query(
            title="Profile Visibility",
            description=(
                "Profile visibility mode. Choose `visible` to let friends view your profile, "
                "or `invisible` to hide your profile from friends."
            ),
        )
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {
        "privacy": 1 if visibility == VisibilityEnum.VISIBLE else 2,
    }
    response = _require_dict_response(fetch_user_actgateway_post("battlereport/privacy/settings", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/season",
    name="api.user.season",
    response_model=UserSeasonResponse,
    summary="User Season List",
    description=(
        "Retrieve the authenticated player's season information using a valid JWT. "
        "Supports query parameter for localization (`lang`). Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes:\n"
        "- **sids**: List of season identifiers representing the seasons in which the player has participated "
        "or has tracked statistics.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying season history.\n"
        "- Linking performance data to specific seasons.\n"
        "- Enabling clients to fetch season-specific stats or achievements."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "74879d32961c1784a762671398979ac6",
                        "data": {
                            "sids": [40, 39, 38, 37]
                        }
                    }
                }
            }
        }
    }
)
def user_season(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {}
    response = _require_dict_response(fetch_user_actgateway("battlereport/season/list", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/matches",
    name="api.user.matches",
    response_model=UserMatchesResponse,
    summary="User Matches",
    description=(
        "Retrieve the authenticated player's recent matches information using a valid JWT. "
        "Supports query parameters for season filtering, pagination, and localization. Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **sid**: Season ID for filtering matches (must be a valid season ID from `/api/user/season`).\n"
        "- **limit**: Maximum number of matches to retrieve (minimum: 1).\n"
        "- **last_cursor**: Cursor for pagination. Use the value from `pageInfo.nextCursor` in the current response. "
        "If `pageInfo.hasNext` is `false` or `pageInfo.nextCursor` is empty, there is no next page.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes match details:\n"
        "- **sid**: Season ID.\n"
        "- **bid**: Battle ID (unique match reference).\n"
        "- **hid**: Hero ID used in the match.\n"
        "- **k**: Kills.\n"
        "- **d**: Deaths.\n"
        "- **a**: Assists.\n"
        "- **lid**: Lane ID (1 EXP, 2 Mid, 3 Roam, 4 Jungle, 5 Gold).\n"
        "- **s**: Score (performance rating for the match, s/100).\n"
        "- **mvp**: MVP flag (1 if MVP, 0 otherwise).\n"
        "- **res**: Result (1 = Win, 0 = Loss).\n"
        "- **ts**: Timestamp of the match.\n"
        "- **hid_e**: Hero entity metadata (hero ID, name, images).\n"
        "- **bid_s**: String battle ID representation.\n\n"
        "Pagination example:\n"
        "    First request: `/api/user/matches?sid=40&limit=10&lang=en` → response includes `pageInfo.nextCursor = 4139649383291049463`.\n"
        "    Second request: `/api/user/matches?sid=40&limit=10&last_cursor=4139649383291049463&lang=en` → retrieves the next page, "
        "using `pageInfo.nextCursor` from the current response.\n"
        "    Stop pagination when `pageInfo.hasNext = false` or `pageInfo.nextCursor` is empty.\n\n"
        "The response also includes pagination metadata:\n"
        "- **pageInfo.nextCursor**: Cursor value for the next page.\n"
        "- **pageInfo.hasNext**: Boolean flag indicating if more results are available.\n"
        "- **pageInfo.count**: Number of results returned in the current page.\n\n"
        "This endpoint is useful for:\n"
        "- Reconstructing match history.\n"
        "- Analyzing player performance.\n"
        "- Enabling clients to paginate reliably through a player's matches."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "53cd62802d24dc512ffd908e1d6d06bc",
                        "data": {
                            "pageInfo": {
                                "nextCursor": "4143043017340290910",
                                "hasNext": True,
                                "count": 1
                            },
                            "result": [
                                {
                                    "sid": 40,
                                    "bid": 4132717739868068400,
                                    "hid": 17,
                                    "k": 14,
                                    "d": 1,
                                    "a": 11,
                                    "lid": 4,
                                    "s": 1180,
                                    "mvp": 0,
                                    "res": 1,
                                    "ts": 1774857999,
                                    "hid_e": {
                                        "id": 17,
                                        "n": "Fanny",
                                        "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_ae8ca46da01da69619a6c03dc7069921.png",
                                        "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_74fabc6c0d5db065fbb836b6879f36ca.jpg"
                                    },
                                    "bid_s": "4132717739868068534"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
def user_matches(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    sid: Annotated[
        int,
        Query(
            title="Season ID",
            description="The season ID for filtering recent matches.",
        )
    ],
    limit: Annotated[
        int,
        Query(
            title="Limit",
            description="The maximum number of recent matches to retrieve.",
            ge=1,
        )
    ] = 10,
    last_cursor: Annotated[
        int | None,
        Query(
            title="Last Cursor",
            description="Pagination cursor from `pageInfo.nextCursor` of the current response.",
        )
    ] = None,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {
        "sid": sid,
        "limit": limit,
    }
    if last_cursor is not None:
        params["last_cursor"] = last_cursor

    response = _require_dict_response(fetch_user_actgateway("battlereport/matches/recent", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/matches/{match_id}",
    name="api.user.match_details",
    response_model=UserMatchDetailsResponse,
    summary="User Match Details",
    description=(
        "Retrieve the authenticated player's detailed match information using a valid JWT. "
        "Supports query parameters for season filtering and localization. Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Path parameters:\n"
        "- **match_id**: Unique identifier of the match (from `bid_s` in `/api/user/matches`).\n\n"
        "Query parameters:\n"
        "- **sid**: Season ID for filtering (must be a valid season ID from `/api/user/season`).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes per-player match details:\n"
        "- **f**: Team flag (1 = Team A, 2 = Team B).\n"
        "- **hid**: Hero ID used in the match.\n"
        "- **rid**: Role ID (unique player identifier).\n"
        "- **zid**: Zone ID (server region).\n"
        "- **k**: Kills.\n"
        "- **d**: Deaths.\n"
        "- **a**: Assists.\n"
        "- **tfr**: Team Fight Rate (contribution ratio in team fights, `tfr*100`%).\n"
        "- **o**: Output (total damage dealt or hero damage).\n"
        "- **op**: Output Percentage (damage contribution relative to team).\n"
        "- **s**: Score (performance rating, `s/100`).\n"
        "- **mvp**: MVP flag (1 if MVP, 0 otherwise).\n"
        "- **its**: Item IDs equipped during the match.\n"
        "- **its_e**: Item entity metadata:\n"
        "    - **id**: Item ID.\n"
        "    - **n**: Item name.\n"
        "    - **ix**: Item image URL.\n"
        "    - **i2x**: Large item image URL.\n"
        "- **eq**: Equipment slot indicator.\n"
        "- **ts**: Timestamp of the match.\n"
        "- **bd**: Battle duration (seconds).\n"
        "- **fk**: First Kill flag (total kills in a team).\n"
        "- **fw**: First Win flag (`1` for Win, `0` for Loss).\n"
        "- **hid_e**: Hero entity metadata:\n"
        "    - **id**: Hero ID.\n"
        "    - **n**: Hero name.\n"
        "    - **ix**: Hero image URL.\n"
        "    - **i2x**: Large hero image URL.\n"
        "- **hlvl**: Hero level reached in the match.\n"
        "- **rname**: Role name (localized string, e.g., 'ジャングラー').\n\n"
        "This endpoint provides a full breakdown of each participant in the match, including:\n"
        "    - Hero choice.\n"
        "    - Performance stats (kills, deaths, assists, damage).\n"
        "    - Items built with metadata.\n"
        "    - Role assignment and team contribution.\n\n"
        "It is useful for:\n"
        "    - Reconstructing match history.\n"
        "    - Analyzing team compositions.\n"
        "    - Evaluating player performance in detail."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "4d96357b092ade76774481366567bcaf",
                        "data": {
                            "result": [
                                {
                                    "f": 2,
                                    "hid": 31,
                                    "rid": 1880233572,
                                    "zid": 57027,
                                    "k": 4,
                                    "d": 9,
                                    "a": 6,
                                    "tfr": 0.4167,
                                    "o": 83974,
                                    "op": 0.2202,
                                    "s": 509,
                                    "mvp": 0,
                                    "its": [2305, 3002, 3005, 3015, 3003, 3013, 0],
                                    "eq": 0,
                                    "ts": 1773837471,
                                    "bd": 1292,
                                    "fk": 24,
                                    "fw": 0,
                                    "hid_e": {
                                        "id": 31,
                                        "n": "Moskov",
                                        "ix": "https://akmweb.youngjoygame.com/web/gms/image/5c4587c25e681be1aecfda0cfbe44714.png",
                                        "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_843f1c2c3a1b2d4da2fc2ec73cf47cfa.jpg"
                                    },
                                    "its_e": [
                                        {
                                            "id": 2305,
                                            "n": "Swift Boots",
                                            "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_b31a355cc85682eed8d9e0dc163fd756.png",
                                            "i2x": ""
                                        },
                                        None
                                    ],
                                    "hlvl": 15,
                                    "rname": "ᴵᵐŦungiℓ"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
def user_match_details(
    match_id: Annotated[
        int,
        Path(
            title="Match ID",
            description="The unique identifier of the match to retrieve details for.",
        )
    ],
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    sid: Annotated[
        int,
        Query(
            title="Season ID",
            description="The season ID for filtering recent matches.",
        )
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {
        "sid": sid
    }
    response = _require_dict_response(fetch_user_actgateway(f"battlereport/matches/{match_id}", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/heroes/frequent",
    name="api.user.frequent_heroes",
    response_model=UserFrequentHeroesResponse,
    summary="User Frequent Heroes",
    description=(
        "Retrieve the authenticated player's frequent heroes information using a valid JWT. "
        "Supports query parameters for season filtering, pagination, and localization. Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **sid**: Season ID for filtering frequent heroes (must be a valid season ID from `/api/user/season`).\n"
        "- **limit**: Maximum number of heroes to retrieve (minimum: 1).\n"
        "- **last_cursor**: Cursor for pagination. Use the value from `pageInfo.nextCursor` in the current response. "
        "If `pageInfo.hasNext` is `false` or `pageInfo.nextCursor` is empty, there is no next page.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes frequent hero usage details:\n"
        "- **hid**: Hero ID.\n"
        "- **tc**: Total Count (number of matches played with this hero).\n"
        "- **wc**: Win Count (number of matches won with this hero).\n"
        "- **bs**: Battle Score (average performance rating, `bs/100`).\n"
        "- **mr**: Match Rating (accumulated rating points).\n"
        "- **mrp**: Match Rating Percentage (rating contribution relative to overall performance).\n"
        "- **hid_e**: Hero entity metadata:\n"
        "    - **id**: Hero ID.\n"
        "    - **n**: Hero name.\n"
        "    - **ix**: Hero image URL.\n"
        "    - **i2x**: Large hero image URL.\n"
        "- **p**: Power score (weighted performance index for ranking frequent heroes, also called `MMR`).\n\n"
        "Pagination example:\n"
        "    First request: `/api/user/heroes/frequent?sid=37&limit=5&lang=en` → response includes `pageInfo.nextCursor = 11`.\n"
        "    Second request: `/api/user/heroes/frequent?sid=37&limit=5&last_cursor=11&lang=en` → retrieves the next page, "
        "using `pageInfo.nextCursor` from the current response.\n"
        "    Stop pagination when `pageInfo.hasNext = false` or `pageInfo.nextCursor` is empty.\n\n"
        "The response also includes pagination metadata:\n"
        "- **pageInfo.nextCursor**: Cursor value for the next page.\n"
        "- **pageInfo.hasNext**: Boolean flag indicating if more results are available.\n"
        "- **pageInfo.count**: Number of results returned in the current page.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing which heroes a player uses most often.\n"
        "- Tracking win rates and performance scores.\n"
        "- Comparing hero usage across different seasons."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "6b098c3c683f977217a91bb6c630e7be",
                        "data": {
                            "pageInfo": {
                                "nextCursor": "",
                                "hasNext": True,
                                "count": 0
                            },
                            "result": [
                                {
                                    "hid": 17,
                                    "tc": 8,
                                    "wc": 7,
                                    "bs": 844.875,
                                    "mr": 6626,
                                    "mrp": 0.6188,
                                    "hid_e": {
                                        "id": 17,
                                        "n": "Fanny",
                                        "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_ae8ca46da01da69619a6c03dc7069921.png",
                                        "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_74fabc6c0d5db065fbb836b6879f36ca.jpg"
                                    },
                                    "p": 1460
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
def user_frequent_heroes(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    sid: Annotated[
        int,
        Query(
            title="Season ID",
            description="The season ID for filtering frequent heroes.",
        )
    ],
    limit: Annotated[
        int,
        Query(
            title="Limit",
            description="The maximum number of frequent heroes to retrieve.",
            ge=1,
        )
    ] = 5,
    last_cursor: Annotated[
        int | None,
        Query(
            title="Last Cursor",
            description="Pagination cursor from `pageInfo.nextCursor` of the current response.",
        )
    ] = None,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {
        "sid": sid,
        "limit": limit,
    }
    if last_cursor is not None:
        params["last_cursor"] = last_cursor

    response = _require_dict_response(fetch_user_actgateway("battlereport/heros/frequent", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/matches/hero/{hero_identifier}",
    name="api.user.matches_by_hero",
    response_model=UserMatchesByHeroResponse,
    summary="User Matches by Hero",
    description=(
        "Retrieve the authenticated player's recent matches filtered by a specific hero using a valid JWT. "
        "Supports query parameters for season filtering, pagination, and localization. Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **sid**: Season ID for filtering matches (must be a valid season ID from `/api/user/season`).\n"
        "- **limit**: Maximum number of matches to retrieve (minimum: 1).\n"
        "- **last_cursor**: Cursor for pagination. Use the value from `pageInfo.nextCursor` in the current response. "
        "If `pageInfo.hasNext` is `false` or `pageInfo.nextCursor` is empty, there is no next page.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "Response structure:\n"
        "- **code**: Status code (0 indicates success).\n"
        "- **message**: Response message from upstream service.\n"
        "- **traceID**: Upstream trace identifier for request debugging/tracking.\n"
        "- **data**: Main payload object.\n"
        "    - **pageInfo**: Pagination metadata object.\n"
        "        - **nextCursor**: Cursor value for the next page, used for pagination.\n"
        "        - **hasNext**: Boolean flag indicating whether more results are available.\n"
        "        - **count**: Number of results returned in the current page.\n"
        "    - **hi**: Aggregated hero summary for the selected hero and season.\n"
        "        - **hid**: Hero ID.\n"
        "        - **tc**: Total Count (matches played with this hero).\n"
        "        - **wc**: Win Count (matches won with this hero).\n"
        "        - **bs**: Battle Score (average score; interpret as `bs/100` when non-zero).\n"
        "        - **mr**: Match Rating points for this hero.\n"
        "        - **mrp**: Match Rating percentage/contribution.\n"
        "        - **hid_e**: Hero metadata object.\n"
        "            - **id**: Hero ID metadata.\n"
        "            - **n**: Hero name.\n"
        "            - **ix**: Hero image URL.\n"
        "            - **i2x**: Large hero image URL.\n"
        "        - **p**: Hero power/MMR-style value.\n"
        "    - **result**: Array of match entries for this hero.\n"
        "        - **sid**: Season ID.\n"
        "        - **bid**: Battle ID (numeric).\n"
        "        - **hid**: Hero ID used in that match.\n"
        "        - **k**: Kills.\n"
        "        - **d**: Deaths.\n"
        "        - **a**: Assists.\n"
        "        - **lid**: Lane ID (1 EXP, 2 Mid, 3 Roam, 4 Jungle, 5 Gold).\n"
        "        - **s**: Match score/performance value (commonly interpreted as `s/100`).\n"
        "        - **mvp**: MVP flag (1 if MVP, 0 otherwise).\n"
        "        - **res**: Result (1 = Win, 0 = Loss).\n"
        "        - **ts**: Match timestamp (unix time).\n"
        "        - **hid_e**: Hero metadata object.\n"
        "            - **id**: Hero ID metadata.\n"
        "            - **n**: Hero name.\n"
        "            - **ix**: Hero image URL.\n"
        "            - **i2x**: Large hero image URL.\n"
        "        - **bid_s**: String battle ID.\n\n"
        "Pagination example:\n"
        "    First request: `/api/user/matches/hero/17?sid=40&limit=10&lang=en`\n"
        "    Next request: `/api/user/matches/hero/17?sid=40&limit=10&last_cursor=<pageInfo.nextCursor>&lang=en`\n"
        "    Stop pagination when `pageInfo.hasNext = false` or `pageInfo.nextCursor` is empty."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "15b79802139dd7766774f6e84ffc31bd",
                        "data": {
                            "pageInfo": {
                                "nextCursor": "",
                                "hasNext": False,
                                "count": 0
                            },
                            "hi": {
                                "hid": 17,
                                "tc": 9,
                                "wc": 8,
                                "bs": 0,
                                "mr": 6788,
                                "mrp": 0.6641,
                                "hid_e": {
                                    "id": 17,
                                    "n": "Fanny",
                                    "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_ae8ca46da01da69619a6c03dc7069921.png",
                                    "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_74fabc6c0d5db065fbb836b6879f36ca.jpg"
                                },
                                "p": 1496
                            },
                            "result": [
                                {
                                    "sid": 40,
                                    "bid": 4138442308503475824,
                                    "hid": 17,
                                    "k": 7,
                                    "d": 3,
                                    "a": 7,
                                    "lid": 4,
                                    "s": 810,
                                    "mvp": 0,
                                    "res": 1,
                                    "ts": 1774955310,
                                    "hid_e": {
                                        "id": 17,
                                        "n": "Fanny",
                                        "ix": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_ae8ca46da01da69619a6c03dc7069921.png",
                                        "i2x": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_74fabc6c0d5db065fbb836b6879f36ca.jpg"
                                    },
                                    "bid_s": "4138442308503475824"
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
def user_matches_by_hero(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    sid: Annotated[
        int,
        Query(
            title="Season ID",
            description="The season ID for filtering matches by hero.",
        )
    ],
    limit: Annotated[
        int,
        Query(
            title="Limit",
            description="The maximum number of matches to retrieve.",
            ge=1,
        )
    ] = 10,
    last_cursor: Annotated[
        int | None,
        Query(
            title="Last Cursor",
            description="Pagination cursor from `pageInfo.nextCursor` of the current response.",
        )
    ] = None,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    hero_id = _hero_id_or_404(
        hero_identifier,
        lang
    )
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {
        "hid": hero_id,
        "sid": sid,
        "limit": limit,
    }
    if last_cursor is not None:
        params["last_cursor"] = last_cursor

    response = _require_dict_response(fetch_user_actgateway("battlereport/hero/matches", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response


@router.get(
    path="/friends",
    name="api.user.friends",
    response_model=UserFriendsResponse,
    summary="User Friends",
    description=(
        "Retrieve the authenticated player's friends information using a valid JWT. "
        "Supports query parameters for season filtering and localization. Requires an Authorization header "
        "with the JWT from login.\n\n"
        "Headers:\n"
        "- **Authorization**: `Bearer <jwt>` (JWT obtained during login).\n\n"
        "Query parameters:\n"
        "- **sid**: Season ID for filtering friends (must be a valid season ID from `/api/user/season`).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes friend statistics and metadata:\n"
        "- **bfs**: Best Friends (highlighted or prioritized friends list, may be null).\n"
        "- **wfs**: Weekly Friends (friends interacted with recently, may be empty).\n"
        "- **fs**: Friends list entries, each containing:\n"
        "    - **f**: Friend object with identifiers:\n"
        "        - **rid**: Role ID (unique player identifier).\n"
        "        - **zid**: Zone ID (server region).\n"
        "        - **n**: Name (may be empty if private).\n"
        "        - **ax**: Avatar URL (may be empty).\n"
        "        - **pri**: Privacy flag (true if details are hidden).\n"
        "    - **frid**: Friend Role ID (unique identifier for the friend).\n"
        "    - **fzid**: Friend Zone ID (server region for the friend).\n"
        "    - **cl**: Current Level of the friend.\n"
        "    - **l**: Level (same as cl, sometimes duplicated).\n"
        "    - **tbc**: Total Battle Count (matches played together).\n"
        "    - **twc**: Total Win Count (matches won together).\n\n"
        "This endpoint is useful for:\n"
        "- Displaying a player's friend list.\n"
        "- Tracking shared match history.\n"
        "- Analyzing cooperative performance with friends across different seasons."
    ),
    deprecated=True,
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "e0516a11c845c6ca93a1a43178c2f510",
                        "data": {
                            "bfs": None,
                            "wfs": [],
                            "fs": [
                                {
                                    "f": {
                                        "rid": 0,
                                        "zid": 0,
                                        "n": "",
                                        "ax": "",
                                        "pri": True
                                    },
                                    "frid": 0,
                                    "fzid": 0,
                                    "cl": 42,
                                    "l": 42,
                                    "tbc": 7,
                                    "twc": 6
                                }
                            ]
                        }
                    }
                }
            }
        }
    }
)
def user_friends(
    jwt: Annotated[
        str,
        Depends(require_user_jwt),
    ],
    sid: Annotated[
        int,
        Query(
            title="Season ID",
            description="The season ID for filtering friends.",
        )
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH,
) -> object:
    headers = UpstreamHeaderBuilder.get_user_header(
        lang=lang,
        x_token=jwt,
    )
    params = {
        "sid": sid,
    }

    response = _require_dict_response(fetch_user_actgateway("battlereport/friends", headers, params))
    _require_key(response, "code")
    _require_key(response, "data")
    return response
