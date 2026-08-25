from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import require_api_available

from app.services.heroes import fetch_hero_post
from app.schemas.heroes import HeroCollectionResponse

from app.core.enums import LanguageEnum, RankEnum, SortOrderEnum, HeroRoleEnum, HeroLaneEnum
from app.core.errors import _hero_id_or_404
from app.utils.client_ip import bind_client_ip
from app.utils.filters import (
    ROLE_MAP, LANE_MAP, validate_and_map_multi, validate_and_map_rank
)

router = APIRouter(prefix="/api", tags=["heroes"], dependencies=[Depends(require_api_available), Depends(bind_client_ip)])


@router.get(
    path="/heroes",
    name="api.heroes.hero_list",
    response_model=HeroCollectionResponse,
    summary="List Heroes",
    description=(
        "Retrieve a paginated list of all heroes with basic information. "
        "Supports query parameters for pagination (`size`, `index`), sorting (`order`), and localization (`lang`).\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero records:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **head**: Hero head image URL.\n"
        "                - **name**: Hero name.\n"
        "                - **smallmap**: Hero smallmap image URL.\n"
        "        - **hero_id**: Unique hero identifier.\n"
        "        - **relation**:\n"
        "            - **assist**:\n"
        "                - **target_hero_id**: Array of hero IDs assisted.\n"
        "            - **strong**:\n"
        "                - **target_hero_id**: Array of hero IDs this hero is strong against.\n"
        "            - **weak**:\n"
        "                - **target_hero_id**: Array of hero IDs this hero is weak against.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying hero collections.\n"
        "- Browsing hero details.\n"
        "- Analyzing hero relationships (assist, strong, weak)."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "data": {
                                        "hero": {
                                            "data": {
                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_2_1_42/100_df7603c292198bf4aa7b551d401ea5c1.png",
                                                "name": "Marcel",
                                                "smallmap": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_2_1_42/100_82e5c2646276cd907f69cc800057c737.png"
                                            }
                                        },
                                        "hero_id": 132,
                                        "relation": {
                                            "assist": {
                                                "target_hero_id": [60, 121]
                                            },
                                            "strong": {
                                                "target_hero_id": [18, 38]
                                            },
                                            "weak": {
                                                "target_hero_id": [84, 83]
                                            }
                                        }
                                    }
                                }
                            ],
                            "total": 132
                        }
                    }
                }
            }
        }
    }
)
def hero_list(
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    order: Annotated[
        SortOrderEnum,
        Query(
            title="Sort Order",
            description="Sort order by hero ID.",
        )
    ] = SortOrderEnum.DESCENDING,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    payload = {
        "pageSize": size,
        "sorts": [
            {
                "data":
                    {
                        "field": "hero_id",
                        "order": order
                    },
                    "type": "sequence"
            }
        ],
        "pageIndex": index,
        "fields": [
            "hero_id",
            "hero.data.head",
            "hero.data.name",
            "hero.data.smallmap"
        ],
    }
    return fetch_hero_post("2756564", payload, lang)


@router.get(
    path="/heroes/rank",
    name="api.heroes.hero_rank",
    response_model=HeroCollectionResponse,
    summary="Hero Rank Statistics",
    description=(
        "Fetch rank statistics for heroes over a specified time window. "
        "Supports query parameters for filtering by past days, rank tier, sorting, pagination, and localization.\n\n"
        "Query parameters:\n"
        "- **days**: Past day window. Allowed values: `1`, `3`, `7`, `15`, `30`.\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **sort_field**: Sort field. Allowed values: `pick_rate`, `ban_rate`, `win_rate`.\n"
        "- **sort_order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero rank statistics:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **main_hero**:\n"
        "            - **data**:\n"
        "                - **head**: Hero head image URL.\n"
        "                - **name**: Hero name.\n"
        "        - **main_heroid**: Unique hero identifier.\n"
        "        - **main_hero_channel**:\n"
        "            - **id**: Channel ID reference.\n"
        "        - **main_hero_appearance_rate**: Hero pick rate (appearance frequency).\n"
        "        - **main_hero_ban_rate**: Hero ban rate.\n"
        "        - **main_hero_win_rate**: Hero win rate.\n"
        "        - **sub_hero**: Array of related sub-heroes, each containing:\n"
        "            - **hero**:\n"
        "                - **data**:\n"
        "                    - **head**: Sub-hero head image URL.\n"
        "            - **heroid**: Sub-hero ID.\n"
        "            - **hero_channel**:\n"
        "                - **id**: Channel ID reference.\n"
        "            - **increase_win_rate**: Impact of sub-hero on win rate.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing hero performance trends across different ranks.\n"
        "- Tracking pick, ban, and win rates over time.\n"
        "- Understanding synergies and counters via sub-hero relationships."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "data": {
                                        "main_hero": {
                                            "data": {
                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_2_1_40/100_8143d7bbd4318d7c699908e808de885e.png",
                                                "name": "Sora"
                                            }
                                        },
                                        "main_hero_appearance_rate": 0.014228,
                                        "main_hero_ban_rate": 0.834702,
                                        "main_hero_channel": {
                                            "id": 3245715
                                        },
                                        "main_hero_win_rate": 0.506002,
                                        "main_heroid": 131,
                                        "sub_hero": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_6495be044c2d28106e200f6918391d54.png"
                                                    }
                                                },
                                                "hero_channel": {
                                                    "id": 2678835
                                                },
                                                "heroid": 99,
                                                "increase_win_rate": 0.061114
                                            }
                                        ]
                                    }
                                }
                            ],
                            "total": 132
                        }
                    }
                }
            }
        }
    }
)
def hero_rank(
    days: Annotated[
        Literal["1", "3", "7", "15", "30"],
        Query(
            title="Past Days",
            description="Past day window for rank statistics.",
        )
    ] = "1",
    rank: Annotated[
        RankEnum,
        Query(
            title="Rank",
            description="Rank filter for hero statistics.",
        ),
    ] = RankEnum.ALL,
    sort_field: Annotated[
        Literal["pick_rate", "ban_rate", "win_rate"],
        Query(
            title="Sort Field",
            description="Field to sort hero statistics.",
        )
    ] = "win_rate",
    sort_order: Annotated[
        SortOrderEnum,
        Query(
            title="Sort Order",
            description="Sort order by field.",
        )
    ] = SortOrderEnum.DESCENDING,
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    sort_field_map = {
        "pick_rate": "main_hero_appearance_rate",
        "ban_rate": "main_hero_ban_rate",
        "win_rate": "main_hero_win_rate",
    }

    url_map = {
        "1": "2756567",
        "3": "2756568",
        "7": "2756569",
        "15": "2756565",
        "30": "2756570",
    }

    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "bigrank",
                "operator": "eq",
                "value": validate_and_map_rank(rank),
            },
            {
                "field": "match_type",
                "operator": "eq",
                "value": "0",
            },
        ],
        "sorts": [
            {
                "data": {
                    "field": sort_field_map.get(sort_field, "main_hero_win_rate"),
                    "order": sort_order,
                },
                "type": "sequence",
            }
        ],
        "pageIndex": index,
        "fields": [
            "main_hero",
            "main_hero_appearance_rate",
            "main_hero_ban_rate",
            "main_hero_channel",
            "main_hero_win_rate",
            "main_heroid",
            "data.sub_hero.hero",
            "data.sub_hero.hero_channel",
            "data.sub_hero.increase_win_rate",
            "data.sub_hero.heroid",
        ],
    }

    url_key = url_map.get(days, "2756567")
    return fetch_hero_post(url_key, payload, lang)


@router.get(
    path="/heroes/positions",
    name="api.heroes.hero_position",
    response_model=HeroCollectionResponse,
    summary="Hero Position Filters",
    description=(
        "Filter heroes by their position on the map using role and lane criteria. "
        "Supports multiple query parameters for roles and lanes, along with pagination, sorting, and localization.\n\n"
        "Query parameters:\n"
        "- **role**: Role filter (multi allowed). Values: `tank`, `fighter`, `assassin`, `mage`, `marksman`, `support`.\n"
        "    Example: `role=tank&role=fighter`\n"
        "- **lane**: Lane filter (multi allowed). Values: `exp`, `mid`, `roam`, `jungle`, `gold`.\n"
        "    Example: `lane=exp&lane=mid`\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero position data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **name**: Hero name.\n"
        "                - **smallmap**: Hero smallmap image URL.\n"
        "                - **roadsort**: Array of lane metadata objects:\n"
        "                    - **_id**: Unique identifier.\n"
        "                    - **caption**: Lane caption (localized).\n"
        "                    - **configId**: Configuration ID.\n"
        "                    - **createdAt**: Creation timestamp.\n"
        "                    - **createdUser**: Creator username.\n"
        "                    - **data**:\n"
        "                        - **_object**: Object reference ID.\n"
        "                        - **road_sort_icon**: Lane icon URL.\n"
        "                        - **road_sort_id**: Lane ID.\n"
        "                        - **road_sort_title**: Lane title (e.g., Roam).\n"
        "                    - **updatedAt**: Last update timestamp.\n"
        "                    - **updatedUser**: Last updater username.\n"
        "                - **sortid**: Array of role metadata objects:\n"
        "                    - **_id**: Unique identifier.\n"
        "                    - **caption**: Role caption (localized).\n"
        "                    - **configId**: Configuration ID.\n"
        "                    - **createdAt**: Creation timestamp.\n"
        "                    - **createdUser**: Creator username.\n"
        "                    - **data**:\n"
        "                        - **_object**: Object reference ID.\n"
        "                        - **sort_icon**: Role icon URL.\n"
        "                        - **sort_id**: Role ID.\n"
        "                        - **sort_title**: Role title (e.g., Support).\n"
        "                    - **updatedAt**: Last update timestamp.\n"
        "                    - **updatedUser**: Last updater username.\n"
        "        - **hero_id**: Unique hero identifier.\n"
        "        - **relation**:\n"
        "            - **assist**:\n"
        "                - **target_hero_id**: Array of hero IDs assisted.\n"
        "            - **strong**:\n"
        "                - **target_hero_id**: Array of hero IDs this hero is strong against.\n"
        "            - **weak**:\n"
        "                - **target_hero_id**: Array of hero IDs this hero is weak against.\n"
        "    - **id**: Record identifier.\n\n"
        "This endpoint is useful for:\n"
        "- Building filtered hero lists.\n"
        "- Analyzing hero roles and lane assignments.\n"
        "- Understanding hero relationships (assist, strong, weak)."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "data": {
                                        "hero": {
                                            "data": {
                                                "name": "Marcel",
                                                "roadsort": [
                                                    {
                                                        "_id": "66854202aa8e7f6ec4703d8f",
                                                        "caption": "辅助",
                                                        "configId": 144237,
                                                        "createdAt": 1720009218480,
                                                        "createdUser": "nickjin",
                                                        "data": {
                                                            "_object": 2732073,
                                                            "road_sort_icon": "https://akmweb.youngjoygame.com/web/gms/image/a3dbb075b4d8186c29f02f7d47da236a.svg",
                                                            "road_sort_id": "3",
                                                            "road_sort_title": "Roam"
                                                        },
                                                        "dynamic": None,
                                                        "id": 2732083,
                                                        "linkId": [2732073],
                                                        "sort": 0,
                                                        "updatedAt": 1723022949109,
                                                        "updatedUser": "nickjin"
                                                    },
                                                    ""
                                                ],
                                                "smallmap": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_2_1_42/100_82e5c2646276cd907f69cc800057c737.png",
                                                "sortid": [
                                                    {
                                                        "_id": "6698c06a613093b976b4a97c",
                                                        "caption": "6辅助",
                                                        "configId": 144237,
                                                        "createdAt": 1721286762785,
                                                        "createdUser": "nickjin",
                                                        "data": {
                                                            "_object": 2740651,
                                                            "sort_icon": "https://akmweb.youngjoygame.com/web/gms/image/1e4609b25a4cd63ee5a13015d4058159.png",
                                                            "sort_id": "6",
                                                            "sort_title": "support"
                                                        },
                                                        "dynamic": None,
                                                        "id": 2740666,
                                                        "linkId": [2740651],
                                                        "sort": 0,
                                                        "updatedAt": 1723023113317,
                                                        "updatedUser": "nickjin"
                                                    },
                                                    ""
                                                ]
                                            }
                                        },
                                        "hero_id": 132,
                                        "relation": {
                                            "assist": {
                                                "target_hero_id": [60, 121]
                                            },
                                            "strong": {
                                                "target_hero_id": [18, 38]
                                            },
                                            "weak": {
                                                "target_hero_id": [84, 83]
                                            }
                                        }
                                    },
                                    "id": 3280483
                                }
                            ],
                            "total": 132
                        }
                    }
                }
            }
        }
    }
)
def hero_position(
    role: Annotated[
        list[str],
        Query(
            title="Role",
            description="Filter heroes by role.",
        )
    ] = [
        HeroRoleEnum.TANK,
        HeroRoleEnum.FIGHTER,
        HeroRoleEnum.ASSASSIN,
        HeroRoleEnum.MAGE,
        HeroRoleEnum.MARKSMAN,
        HeroRoleEnum.SUPPORT,
    ],
    lane: Annotated[
        list[str],
        Query(
            title="Lane",
            description="Filter heroes by lane.",
        )
    ] = [
        HeroLaneEnum.EXP,
        HeroLaneEnum.MID,
        HeroLaneEnum.ROAM,
        HeroLaneEnum.JUNGLE,
        HeroLaneEnum.GOLD,
    ],
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    order: Annotated[
        SortOrderEnum,
        Query(
            title="Sort Order",
            description="Sort order by hero ID.",
        )
    ] = SortOrderEnum.DESCENDING,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    role_values = validate_and_map_multi(role, ROLE_MAP, [1,2,3,4,5,6], "role")
    lane_values = validate_and_map_multi(lane, LANE_MAP, [1,2,3,4,5], "lane")

    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "<hero.data.sortid>",
                "operator": "hasAnyOf",
                "value": role_values
            },
            {
                "field": "<hero.data.roadsort>",
                "operator": "hasAnyOf", 
                "value": lane_values
            },
        ],
        "sorts": [
            {
                "data": {
                    "field": "hero_id",
                    "order": order
                },
                "type": "sequence"
            }
        ],
        "pageIndex": index,
        "fields": [
            "id",
            "hero_id",
            "hero.data.name",
            "hero.data.smallmap",
            "hero.data.sortid",
            "hero.data.roadsort"
        ],
        "object": [],
    }
    return fetch_hero_post("2756564", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}",
    name="api.heroes.hero_detail",
    response_model=HeroCollectionResponse,
    summary="Hero Detail",
    description=(
        "Get detailed information for a specific hero by ID or name. "
        "Supports query parameters for pagination and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero details:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **caption**: Caption or localized label.\n"
        "    - **configId**: Configuration ID.\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **createdUser**: Creator username.\n"
        "    - **data**:\n"
        "        - **head**: Hero portrait image URL.\n"
        "        - **head_big**: Larger hero portrait image URL.\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **heroid**: Hero ID.\n"
        "                - **name**: Hero name.\n"
        "                - **story**: Hero lore or background story.\n"
        "                - **painting**: Hero splash art image URL.\n"
        "                - **speciality**: Array of hero specialties (e.g., Support, Crowd Control).\n"
        "                - **abilityshow**: Array of ability stats.\n"
        "                - **difficulty**: Difficulty rating.\n"
        "                - **heroskilllist**: Array of skill sets, each containing:\n"
        "                    - **skilllist**: Array of skills:\n"
        "                        - **skillid**: Skill ID.\n"
        "                        - **skillname**: Skill name.\n"
        "                        - **skilldesc**: Skill description.\n"
        "                        - **skillicon**: Skill icon URL.\n"
        "                        - **skillcd&cost**: Cooldown and mana cost.\n"
        "                        - **skilltag**: Array of tags:\n"
        "                            - **tagid**: Tag ID.\n"
        "                            - **tagname**: Tag name (e.g., Burst, CC).\n"
        "                            - **tagrgb**: Tag color.\n"
        "                        - **skillvideo**: Skill video URL (if available).\n"
        "                - **roadsort**: Lane assignment metadata:\n"
        "                    - **road_sort_id**: Lane ID.\n"
        "                    - **road_sort_title**: Lane title (e.g., Mid Lane).\n"
        "                    - **road_sort_icon**: Lane icon URL.\n"
        "                - **sortid**: Role assignment metadata:\n"
        "                    - **sort_id**: Role ID.\n"
        "                    - **sort_title**: Role title (e.g., Mage).\n"
        "                    - **sort_icon**: Role icon URL.\n"
        "                - **smallmap**: Hero smallmap image URL.\n"
        "                - **squarehead**: Square portrait image URL.\n"
        "                - **squareheadbig**: Larger square portrait image URL.\n"
        "        - **hero_id**: Unique hero identifier.\n"
        "        - **relation**:\n"
        "            - **assist**:\n"
        "                - **desc**: Description of assist synergy.\n"
        "                - **target_hero_id**: Array of hero IDs assisted.\n"
        "                - **target_hero**: Array of assisted hero metadata (images).\n"
        "            - **strong**:\n"
        "                - **desc**: Description of heroes countered.\n"
        "                - **target_hero_id**: Array of hero IDs countered.\n"
        "                - **target_hero**: Array of countered hero metadata (images).\n"
        "            - **weak**:\n"
        "                - **desc**: Description of heroes that counter this hero.\n"
        "                - **target_hero_id**: Array of hero IDs that counter.\n"
        "                - **target_hero**: Array of counter hero metadata (images).\n"
        "        - **url**: Official lore or profile URL.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying comprehensive hero profiles.\n"
        "- Analyzing hero abilities and skill tags.\n"
        "- Understanding hero synergies and counters.\n"
        "- Linking lane and role assignments to gameplay analysis."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "_id": "65f2e280fd1bb8e47d25e07b",
                                    "caption": "096珞翊",
                                    "configId": 144237,
                                    "createdAt": 1710416512439,
                                    "createdUser": "nickjin",
                                    "data": {
                                        "_object": 2667538,
                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/community/100_9dc55ccd4a972b721dfb8fadfb22fa34.png",
                                        "head_big": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_52c14752b29b6f9039da26a50e860c5c.jpg",
                                        "hero": {
                                            "_createdAt": 1724837697935,
                                            "_id": "66ceef41af5771f18c5009e1",
                                            "_updatedAt": 1773205501411,
                                            "data": {
                                                "abilityshow": ["20", "100", "40", "50"],
                                                "difficulty": "50",
                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_103541726507f5ce102689f04fe215e8.png",
                                                "heroid": 96,
                                                "heroskilllist": [
                                                    {
                                                        "skilllist": [
                                                            {
                                                                "skillcd&cost": "",
                                                                "skilldesc": "Luo Yi's skills can create <font color=\"a6aafb\">Sigils of Yin/Yang</font> on the battlefield. Each Sigil lasts up to 6s.\nSigils of opposite attributes will trigger <font color=\"a6aafb\">Yin-Yang Reaction</font> when they are within a certain distance, dealing 300 (+25*Hero Level) <font color=\"62f8fe\">(+190% Total Magic Power)</font> <font color=\"7f62fe\">Magic Damage</font> to the marked enemies, stunning them for 0.3s, and pulling them toward each other.\nEach time Luo Yi applies a new Sigil to a marked enemy, she gains a 300 (+10*Hero Level) <font color=\"62f8fe\">(+150% Total Magic Power)</font> shield (up to 3 stacks) and 50% extra Movement Speed that decays over 2s.",
                                                                "skillicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_55ccda55cadbf28d972b7878c6ed14fe.png",
                                                                "skillid": 9650,
                                                                "skillname": "Duality",
                                                                "skilltag": [
                                                                    {
                                                                        "tagid": 31,
                                                                        "tagname": "Burst",
                                                                        "tagrgb": "199,121,85"
                                                                    },
                                                                    {
                                                                        "tagid": 21,
                                                                        "tagname": "CC",
                                                                        "tagrgb": "205,93,109"
                                                                    }
                                                                ],
                                                                "skillvideo": ""
                                                            }
                                                        ],
                                                        "skilllistid": "961"
                                                    }
                                                ],
                                                "heroskin": None,
                                                "name": "Luo Yi",
                                                "painting": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_e8f1e6dd0d7864b66bda10ef65242dd6.png",
                                                "recommendlevel": ["3", "1", "2"],
                                                "recommendlevellabel": "3-1-2",
                                                "recommendmasterplan": [],
                                                "roadsort": [
                                                    {
                                                        "_id": "66854225aa8e7f6ec4703d93",
                                                        "caption": "中路",
                                                        "configId": 144237,
                                                        "createdAt": 1720009253985,
                                                        "createdUser": "nickjin",
                                                        "data": {
                                                            "_object": 2732073,
                                                            "road_sort_icon": "https://akmweb.youngjoygame.com/web/gms/image/facab1eacb218d767b5acb80304bfafd.svg",
                                                            "road_sort_id": "2",
                                                            "road_sort_title": "Mid Lane"
                                                        },
                                                        "dynamic": None,
                                                        "id": 2732084,
                                                        "linkId": [2732073],
                                                        "sort": 0,
                                                        "updatedAt": 1723022943932,
                                                        "updatedUser": "nickjin"
                                                    },
                                                    ""
                                                ],
                                                "roadsorticon1": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_1b414d1631fc57199315b998064c6722.png",
                                                "roadsorticon2": "",
                                                "roadsortlabel": ["Mid Lane", ""],
                                                "smallmap": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_74fe63bd31cc092aed923543a115b7bd.png",
                                                "sorticon1": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_50fbe091cc66ff01cef0fa6b82872510.png",
                                                "sorticon2": "",
                                                "sortid": [
                                                    {
                                                        "_id": "6698c015613093b976b4a974",
                                                        "caption": "4法师",
                                                        "configId": 144237,
                                                        "createdAt": 1721286677393,
                                                        "createdUser": "nickjin",
                                                        "data": {
                                                            "_object": 2740651,
                                                            "sort_icon": "https://akmweb.youngjoygame.com/web/gms/image/1c6985dd0caec2028ccb6d1b8ca95e0f.png",
                                                            "sort_id": "4",
                                                            "sort_title": "mage"
                                                        },
                                                        "dynamic": None,
                                                        "id": 2740663,
                                                        "linkId": [2740651],
                                                        "sort": 0,
                                                        "updatedAt": 1723023128824,
                                                        "updatedUser": "nickjin"
                                                    },
                                                    ""
                                                ],
                                                "sortlabel": ["Mage", ""],
                                                "speciality": ["Support", "Crowd Control"],
                                                "squarehead": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_45ed52f05d2288e0c87ca858d7f66f23.jpg",
                                                "squareheadbig": "https://akmweb.youngjoygame.com/web/svnres/file/mlbb/homepage/100_52c14752b29b6f9039da26a50e860c5c.jpg",
                                                "story": "Seeking to revive an ancient past, she is the sole being who has mastered the secrets of Yin and Yang.",
                                                "tale": ""
                                            },
                                            "id": 100465,
                                            "sourceId": 2756563
                                        },
                                        "hero_id": 96,
                                        "relation": {
                                            "assist": {
                                                "desc": "Luo Yi works best with Junglers who are often looking for fights around the map, such as Aamon and Karina, because she can use her Ultimate to cut down their travel time.",
                                                "target_hero": [
                                                    {
                                                        "data": {
                                                            "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_b3a7602fe7ffd1e54bf8ea79ceadfa72.png"
                                                        }
                                                    }
                                                ],
                                                "target_hero_id": [109, 8, 0]
                                            },
                                            "strong": {
                                                "desc": "Luo Yi counters heroes with low mobility such as Eudora and Gord because they are easy targets for her Sigils and Yin-Yang Reactions.",
                                                "target_hero": [
                                                    {
                                                        "data": {
                                                            "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_2_1_42/100_87b2a655b254c136dce8976e21935a80.png"
                                                        }
                                                    }
                                                ],
                                                "target_hero_id": [15, 23, 0, 0]
                                            },
                                            "weak": {
                                                "desc": "Luo Yi is countered by Fighters or Tanks with high HP recovery like Uranus and Fredrinn because she can't deal enough damage to finish them off quickly.",
                                                "target_hero": [
                                                    {
                                                        "data": {
                                                            "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_2e15a0a506aaecd9b3de40a8cc9f7ec7.png"
                                                        }
                                                    }
                                                ],
                                                "target_hero_id": [59, 117, 0, 0]
                                            }
                                        },
                                        "url": "https://play.mobilelegends.com/lore/hero/LuoYi"
                                    },
                                    "dynamic": None,
                                    "id": 2678832,
                                    "linkId": [2667538],
                                    "sort": 0,
                                    "updatedAt": 1726805352355,
                                    "updatedUser": "nickjin"
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
def hero_detail(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            )
        )
    ],
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "hero_id",
                "operator": "eq",
                "value": hero_id
            }
        ],
        "sorts": [],
        "pageIndex": index,
        "object": [],
    }
    return fetch_hero_post("2756564", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/stats",
    name="api.heroes.hero_detail_stats",
    response_model=HeroCollectionResponse,
    summary="Hero Detail Statistics",
    description=(
        "Get detailed statistics for a specific hero by ID or name. "
        "Supports query parameters for rank tier, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero statistics:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_hero**:\n"
        "            - **data**:\n"
        "                - **head**: Hero portrait image URL.\n"
        "                - **name**: Hero name.\n"
        "        - **main_heroid**: Hero ID.\n"
        "        - **main_hero_channel**:\n"
        "            - **id**: Channel ID reference.\n"
        "        - **main_hero_appearance_rate**: Hero pick rate (appearance frequency).\n"
        "        - **main_hero_ban_rate**: Hero ban rate.\n"
        "        - **main_hero_win_rate**: Hero win rate.\n"
        "        - **sub_hero**: Array of synergy heroes, each containing:\n"
        "            - **heroid**: Sub-hero ID.\n"
        "            - **hero_win_rate**: Sub-hero win rate.\n"
        "            - **hero_appearance_rate**: Sub-hero pick rate.\n"
        "            - **increase_win_rate**: Impact of sub-hero on win rate.\n"
        "            - **hero_channel**:\n"
        "                - **id**: Channel ID reference.\n"
        "            - **hero**:\n"
        "                - **data**:\n"
        "                    - **head**: Sub-hero portrait image URL.\n"
        "            - **min_win_rate6**: Win rate in matches ≤ 6 minutes, (`min_win_rate6*100`%).\n"
        "            - **min_win_rate6_8**: Win rate in matches 6-8 minutes, (`min_win_rate6_8*100`%).\n"
        "            - **min_win_rate8_10**: Win rate in matches 8-10 minutes, (`min_win_rate8_10*100`%).\n"
        "            - **min_win_rate10_12**: Win rate in matches 10-12 minutes, (`min_win_rate10_12*100`%).\n"
        "            - **min_win_rate12_14**: Win rate in matches 12-14 minutes, (`min_win_rate12_14*100`%).\n"
        "            - **min_win_rate14_16**: Win rate in matches 14-16 minutes, (`min_win_rate14_16*100`%).\n"
        "            - **min_win_rate16_18**: Win rate in matches 16-18 minutes, (`min_win_rate16_18*100`%).\n"
        "            - **min_win_rate18_20**: Win rate in matches 18-20 minutes, (`min_win_rate18_20*100`%).\n"
        "            - **min_win_rate20**: Win rate in matches ≥ 20 minutes, (`min_win_rate20*100`%).\n"
        "        - **sub_hero_last**: Array of negative synergy heroes, each containing:\n"
        "            - **heroid**: Sub-hero ID.\n"
        "            - **hero_win_rate**: Sub-hero win rate.\n"
        "            - **hero_appearance_rate**: Sub-hero pick rate.\n"
        "            - **increase_win_rate**: Negative impact on win rate.\n"
        "            - **min_win_rate6** through **min_win_rate20**: Win rate breakdown across match durations.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing hero performance trends across different ranks.\n"
        "- Tracking pick, ban, and win rates.\n"
        "- Understanding synergy with other heroes.\n"
        "- Identifying counters and negative synergies across match durations."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "_createdAt": 1724837698515,
                                    "_id": "66ceef43af5771f18c501841",
                                    "_updatedAt": 1774970102297,
                                    "data": {
                                        "bigrank": "101",
                                        "camp_type": "1",
                                        "main_hero": {
                                            "data": {
                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_da894b37bfb5cadb32307f371f31918a.png",
                                                "name": "Miya"
                                            }
                                        },
                                        "main_hero_appearance_rate": 0.024029,
                                        "main_hero_ban_rate": 0.030362,
                                        "main_hero_channel": {
                                            "id": 2667597
                                        },
                                        "main_hero_win_rate": 0.501098,
                                        "main_heroid": 1,
                                        "match_type": "1",
                                        "sub_hero": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_1_9_642/100_c472fe0233e5ef84a3ac9ba4a229d09f.png"
                                                    }
                                                },
                                                "hero_appearance_rate": 0.005875,
                                                "hero_channel": {
                                                    "id": 2678840
                                                },
                                                "hero_index": 1,
                                                "hero_win_rate": 0.559063,
                                                "heroid": 104,
                                                "increase_win_rate": 0.023307,
                                                "min_win_rate10_12": 0.597996,
                                                "min_win_rate12_14": 0.587859,
                                                "min_win_rate14_16": 0.588737,
                                                "min_win_rate16_18": 0.586709,
                                                "min_win_rate18_20": 0.588967,
                                                "min_win_rate20": 0.565267,
                                                "min_win_rate6": 1,
                                                "min_win_rate6_8": 0.481586,
                                                "min_win_rate8_10": 0.519894
                                            }
                                        ],
                                        "sub_hero_last": [
                                            {
                                                "hero_appearance_rate": 0.001634,
                                                "hero_index": 1,
                                                "hero_win_rate": 0.473376,
                                                "heroid": 89,
                                                "increase_win_rate": -0.088744,
                                                "min_win_rate10_12": 0.356784,
                                                "min_win_rate12_14": 0.345992,
                                                "min_win_rate14_16": 0.348178,
                                                "min_win_rate16_18": 0.433333,
                                                "min_win_rate18_20": 0.505051,
                                                "min_win_rate20": 0.50289,
                                                "min_win_rate6": 1,
                                                "min_win_rate6_8": 0.1,
                                                "min_win_rate8_10": 0.18
                                            }
                                        ]
                                    },
                                    "id": 103638,
                                    "sourceId": 2756567
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
def hero_detail_stats(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    rank: Annotated[
        RankEnum,
        Query(
            title="Rank",
            description="Rank filter for hero statistics.",
        ),
    ] = RankEnum.ALL,
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "main_heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "bigrank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            },
            {
                "field": "match_type",
                "operator": "eq",
                "value": "1"
            },
        ],
        "sorts": [],
        "pageIndex": index,
    }
    return fetch_hero_post("2756567", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/skill-combos",
    name="api.heroes.hero_skill_combo",
    response_model=HeroCollectionResponse,
    summary="Hero Skill Combos",
    description=(
        "Get the most effective skill combos for a specific hero by ID or name. "
        "Supports query parameters for pagination and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero skill combo details:\n"
        "- **records**: Array of combo entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **caption**: Caption or localized label (e.g., laning, teamfight).\n"
        "    - **configId**: Configuration ID.\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **createdUser**: Creator username.\n"
        "    - **data**:\n"
        "        - **hero_id**: Hero ID.\n"
        "        - **title**: Combo title (e.g., 'TEAMFIGHT COMBOS').\n"
        "        - **desc**: Descriptive instructions on how to execute the combo "
        "(e.g., laning phase or teamfight scenarios).\n"
        "        - **skill_id**: Array of skills in recommended sequence, each containing:\n"
        "            - **skillid**: Skill ID.\n"
        "            - **skillicon**: Skill icon URL.\n"
        "            - **_id**, **_createdAt**, **_updatedAt**: Metadata fields.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **updatedUser**: Last updater username.\n\n"
        "This endpoint is useful for:\n"
        "- Guiding players on optimal skill usage patterns.\n"
        "- Teaching effective combos for laning and teamfight scenarios.\n"
        "- Helping maximize hero performance in different situations."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "_id": "661fffbc17071f48448b1f76",
                                    "caption": "弥亚",
                                    "configId": 144237,
                                    "createdAt": 1713373116184,
                                    "createdUser": "rubickguo",
                                    "data": {
                                        "_object": 2684183,
                                        "desc": "In teamfights, use Miya's Ultimate first to conceal herself, then find an ideal position to attack the enemy and quickly stack her Passive. Utilize her 2nd Skill to immobilize the enemy and activate her 1st Skill to enhance her Basic Attacks to hit multiple targets at once.",
                                        "hero_id": 1,
                                        "skill_id": [
                                            {
                                                "_createdAt": 1730960697288,
                                                "_id": "672c5d399d856a6db37d936a",
                                                "_updatedAt": 1758787887535,
                                                "data": {
                                                    "skillicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_361546d795e6df7029a1cf1252e57ac8.png",
                                                    "skillid": 130
                                                },
                                                "id": 109690,
                                                "sourceId": 2674712
                                            }
                                        ],
                                        "title": "TEAMFIGHT COMBOS"
                                    },
                                    "dynamic": None,
                                    "id": 2694856,
                                    "linkId": [2684183],
                                    "sort": 0,
                                    "updatedAt": 1713373219943,
                                    "updatedUser": "rubickguo"
                                }
                            ],
                            "total": 2
                        }
                    }
                }
            }
        }
    }
)
def hero_skill_combo(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "hero_id",
                "operator": "eq",
                "value": hero_id
            }
        ],
        "sorts": [],
        "pageIndex": index,
        "object": [2684183],
    }
    return fetch_hero_post("2674711", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/trends",
    name="api.heroes.hero_rate",
    response_model=HeroCollectionResponse,
    summary="Hero Performance Trends",
    description=(
        "Get rate trends for a specific hero by ID or name over a specified time window. "
        "Supports query parameters for rank tier, past days window, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **past-days**: Rate window in days. Allowed values: `7`, `15`, `30`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero rate trend data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_heroid**: Hero ID.\n"
        "        - **bigrank**: Rank tier identifier.\n"
        "        - **camp_type**: Camp type indicator.\n"
        "        - **match_type**: Match type indicator.\n"
        "        - **win_rate**: Array of daily statistics, each containing:\n"
        "            - **date**: Date of record.\n"
        "            - **app_rate**: Appearance rate (pick frequency).\n"
        "            - **ban_rate**: Ban rate.\n"
        "            - **win_rate**: Win rate.\n\n"
        "This endpoint is useful for:\n"
        "- Tracking hero performance trends over time.\n"
        "- Monitoring hero popularity and ban frequency.\n"
        "- Comparing win rates across different ranks and time periods."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "_createdAt": 1719822297335,
                                    "_id": "668267db061f5179ffb909ac",
                                    "_updatedAt": 1774965307951,
                                    "data": {
                                        "bigrank": "101",
                                        "camp_type": "1",
                                        "main_heroid": 17,
                                        "match_type": "1",
                                        "win_rate": [
                                            {
                                                "app_rate": 0.00695,
                                                "ban_rate": 0.045781,
                                                "date": "2026-03-30",
                                                "win_rate": 0.439798
                                            }
                                        ]
                                    },
                                    "id": 158321,
                                    "sourceId": 2674709
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
def hero_rate(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    rank: Annotated[
        RankEnum,
        Query(
            title="Rank",
            description="Rank filter for hero statistics.",
        ),
    ] = RankEnum.ALL,
    past_days: Annotated[
        Literal["7", "15", "30"],
        Query(
            alias="past-days",
            title="Rate Window",
            description="Rate window in days.",
        ),
    ] = "7",
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    url_map = {
        "7": "2674709",
        "15": "2687909",
        "30": "2690860"
    }
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "main_heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "bigrank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            },
            {
                "field": "match_type",
                "operator": "eq",
                "value": "1"
            },
        ],
        "sorts": [],
        "pageIndex": index,
    }
    return fetch_hero_post(url_map.get(past_days, "2674709"), payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/relations",
    name="api.heroes.hero_relation",
    response_model=HeroCollectionResponse,
    summary="Hero Relations",
    description=(
        "Get information about the relations of a specific hero by ID or name. "
        "Supports query parameters for pagination and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero relation data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **name**: Hero name.\n"
        "        - **hero_id**: Unique hero identifier.\n"
        "        - **relation**:\n"
        "            - **assist**:\n"
        "                - **target_hero_id**: Array of hero IDs that synergize well.\n"
        "            - **strong**:\n"
        "                - **target_hero_id**: Array of hero IDs that are countered.\n"
        "            - **weak**:\n"
        "                - **target_hero_id**: Array of hero IDs that counter this hero.\n\n"
        "This endpoint is useful for:\n"
        "- Understanding hero synergies (assist).\n"
        "- Identifying heroes that are countered (strong).\n"
        "- Recognizing heroes that counter the selected hero (weak).\n"
        "- Building balanced team compositions."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "data": {
                                        "hero": {
                                            "data": {
                                                "name": "Miya"
                                            }
                                        },
                                        "hero_id": 1,
                                        "relation": {
                                            "assist": {
                                                "target_hero_id": [6, 70, 0]
                                            },
                                            "strong": {
                                                "target_hero_id": [3, 15, 27]
                                            },
                                            "weak": {
                                                "target_hero_id": [52, 101, 0]
                                            }
                                        }
                                    }
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
def hero_relation(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "hero_id",
                "operator": "eq",
                "value": hero_id
            }
        ],
        "sorts": [],
        "pageIndex": index,
        "fields": ["hero.data.name"],
        "object": [],
    }
    return fetch_hero_post("2756564", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/counters",
    name="api.heroes.hero_counter",
    response_model=HeroCollectionResponse,
    summary="Hero Counters",
    description=(
        "Get information about heroes that counter a specific hero by ID or name. "
        "Supports query parameters for rank tier, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- days: Time window for counter data. Allowed values: `1`, `3`, `7`, `15`, `30`.\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero counter data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_hero**:\n"
        "            - **data**:\n"
        "                - **head**: Main hero portrait image URL.\n"
        "                - **name**: Main hero name.\n"
        "        - **main_heroid**: Main hero ID.\n"
        "        - **main_hero_channel**:\n"
        "            - **id**: Channel ID reference.\n"
        "        - **main_hero_appearance_rate**: Pick rate of the main hero.\n"
        "        - **main_hero_ban_rate**: Ban rate of the main hero.\n"
        "        - **main_hero_win_rate**: Win rate of the main hero.\n"
        "        - **sub_hero**: Array of counter heroes, each containing:\n"
        "            - **heroid**: Counter hero ID.\n"
        "            - **hero_win_rate**: Counter hero win rate.\n"
        "            - **hero_appearance_rate**: Counter hero pick rate.\n"
        "            - **increase_win_rate**: Impact of counter hero on win rate.\n"
        "            - **hero_channel**:\n"
        "                - **id**: Channel ID reference.\n"
        "            - **hero**:\n"
        "                - **data**:\n"
        "                    - **head**: Counter hero portrait image URL.\n"
        "            - **min_win_rate6** through **min_win_rate20**: Win rate breakdown across match durations.\n"
        "        - **sub_hero_last**: Array of negative synergy heroes, each containing:\n"
        "            - **heroid**: Sub-hero ID.\n"
        "            - **hero_win_rate**: Sub-hero win rate.\n"
        "            - **hero_appearance_rate**: Sub-hero pick rate.\n"
        "            - **increase_win_rate**: Negative impact on win rate.\n"
        "            - **min_win_rate6** through **min_win_rate20**: Win rate breakdown across match durations.\n\n"
        "This endpoint is useful for:\n"
        "- Identifying which heroes are effective counters.\n"
        "- Analyzing matchup dynamics.\n"
        "- Understanding performance trends across different ranks and match durations."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "_createdAt": 1724837698334,
                                    "_id": "66ceef42af5771f18c500da2",
                                    "_updatedAt": 1774890906262,
                                    "data": {
                                        "bigrank": "9",
                                        "camp_type": "0",
                                        "main_hero": {
                                            "data": {
                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_3391df36d6dcc54dd1c417098e15ec59.png",
                                                "name": "Fanny"
                                            }
                                        },
                                        "main_hero_appearance_rate": 0.009896,
                                        "main_hero_ban_rate": 0.073593,
                                        "main_hero_channel": {
                                            "id": 2678753
                                        },
                                        "main_hero_win_rate": 0.458363,
                                        "main_heroid": 17,
                                        "match_type": "0",
                                        "sub_hero": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_474cea36a4bfdc7bf7d94530853a99b2.png"
                                                    }
                                                },
                                                "hero_appearance_rate": 0.002274,
                                                "hero_channel": {
                                                    "id": 2678756
                                                },
                                                "hero_index": 1,
                                                "hero_win_rate": 0.553658,
                                                "heroid": 20,
                                                "increase_win_rate": 0.048121,
                                                "min_win_rate10_12": 0.452088,
                                                "min_win_rate12_14": 0.439306,
                                                "min_win_rate14_16": 0.426901,
                                                "min_win_rate16_18": 0.493865,
                                                "min_win_rate18_20": 0.465217,
                                                "min_win_rate20": 0.486553,
                                                "min_win_rate6": 0.333333,
                                                "min_win_rate6_8": 0.5,
                                                "min_win_rate8_10": 0.355263
                                            }
                                        ],
                                        "sub_hero_last": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_ff39deb9c6afec3d977fdbe9d86f78cb.png"
                                                    }
                                                },
                                                "hero_appearance_rate": 0.002147,
                                                "hero_channel": {
                                                    "id": 2678748
                                                },
                                                "hero_index": 1,
                                                "hero_win_rate": 0.476658,
                                                "heroid": 12,
                                                "increase_win_rate": -0.045228,
                                                "min_win_rate10_12": 0.384454,
                                                "min_win_rate12_14": 0.456767,
                                                "min_win_rate14_16": 0.435701,
                                                "min_win_rate16_18": 0.459155,
                                                "min_win_rate18_20": 0.420792,
                                                "min_win_rate20": 0.450402,
                                                "min_win_rate6": 1,
                                                "min_win_rate6_8": 0.315789,
                                                "min_win_rate8_10": 0.5
                                            }
                                        ]
                                    },
                                    "id": 103076,
                                    "sourceId": 2756569
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
def hero_counter(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    days: Annotated[
        Literal["1", "3", "7", "15", "30"],
        Query(
            title="Past Days",
            description="Past day window for rank statistics.",
        )
    ] = "1",
    rank: Annotated[
        RankEnum,
        Query(
            title="Rank",
            description="Rank filter for hero statistics.",
        ),
    ] = RankEnum.ALL,
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    url_map = {"1": "2756567", "3": "2756568", "7": "2756569", "15": "2756565", "30": "2756570"}
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "match_type",
                "operator": "eq",
                "value": "0"
            },
            {
                "field": "main_heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "bigrank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            },
        ],
        "sorts": [],
        "pageIndex": index,
    }
    url_key = url_map.get(days, "2756567")
    return fetch_hero_post(url_key, payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/compatibility",
    name="api.heroes.hero_compatibility",
    response_model=HeroCollectionResponse,
    summary="Hero Compatibility",
    description=(
        "Get compatibility information for a specific hero by ID or name. "
        "Supports query parameters for rank tier, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **days**: Time window for compatibility data. Allowed values: `1`, `3`, `7`, `15`, `30`.\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero compatibility data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_hero**:\n"
        "            - **data**:\n"
        "                - **head**: Main hero portrait image URL.\n"
        "                - **name**: Main hero name.\n"
        "        - **main_heroid**: Main hero ID.\n"
        "        - **main_hero_channel**:\n"
        "            - **id**: Channel ID reference.\n"
        "        - **main_hero_appearance_rate**: Pick rate of the main hero.\n"
        "        - **main_hero_ban_rate**: Ban rate of the main hero.\n"
        "        - **main_hero_win_rate**: Win rate of the main hero.\n"
        "        - **sub_hero**: Array of compatible heroes, each containing:\n"
        "            - **heroid**: Compatible hero ID.\n"
        "            - **hero_win_rate**: Compatible hero win rate.\n"
        "            - **hero_appearance_rate**: Compatible hero pick rate.\n"
        "            - **increase_win_rate**: Positive synergy impact on win rate.\n"
        "            - **hero_channel**:\n"
        "                - **id**: Channel ID reference.\n"
        "            - **hero**:\n"
        "                - **data**:\n"
        "                    - **head**: Compatible hero portrait image URL.\n"
        "            - **min_win_rate6** through **min_win_rate20**: Win rate breakdown across match durations.\n"
        "        - **sub_hero_last**: Array of negative synergy heroes, each containing:\n"
        "            - **heroid**: Sub-hero ID.\n"
        "            - **hero_win_rate**: Sub-hero win rate.\n"
        "            - **hero_appearance_rate**: Sub-hero pick rate.\n"
        "            - **increase_win_rate**: Negative impact on win rate.\n"
        "            - **min_win_rate6** through **min_win_rate20**: Win rate breakdown across match durations.\n\n"
        "This endpoint is useful for:\n"
        "- Identifying which heroes pair well with the selected hero.\n"
        "- Analyzing synergy and team composition effectiveness.\n"
        "- Recognizing combinations that reduce performance.\n"
        "- Understanding matchup dynamics across ranks and match durations."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "OK",
                        "data": {
                            "records": [
                                {
                                    "_createdAt": 1724837698334,
                                    "_id": "66ceef42af5771f18c500d18",
                                    "_updatedAt": 1774890906262,
                                    "data": {
                                        "bigrank": "9",
                                        "camp_type": "1",
                                        "main_hero": {
                                            "data": {
                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_3391df36d6dcc54dd1c417098e15ec59.png",
                                                "name": "Fanny"
                                            }
                                        },
                                        "main_hero_appearance_rate": 0.009896,
                                        "main_hero_ban_rate": 0.073593,
                                        "main_hero_channel": {
                                            "id": 2678753
                                        },
                                        "main_hero_win_rate": 0.458363,
                                        "main_heroid": 17,
                                        "match_type": "1",
                                        "sub_hero": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_6495be044c2d28106e200f6918391d54.png"
                                                    }
                                                },
                                                "hero_appearance_rate": 0.001064,
                                                "hero_channel": {
                                                    "id": 2678835
                                                },
                                                "hero_index": 1,
                                                "hero_win_rate": 0.487066,
                                                "heroid": 99,
                                                "increase_win_rate": 0.080441,
                                                "min_win_rate10_12": 0.536232,
                                                "min_win_rate12_14": 0.616162,
                                                "min_win_rate14_16": 0.483333,
                                                "min_win_rate16_18": 0.534247,
                                                "min_win_rate18_20": 0.469388,
                                                "min_win_rate20": 0.525424,
                                                "min_win_rate6": 0,
                                                "min_win_rate6_8": 0,
                                                "min_win_rate8_10": 0.363636
                                            }
                                        ],
                                        "sub_hero_last": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage_1_9_47/100_d2d28d2fcb060726fa27553920ca1a33.png"
                                                    }
                                                },
                                                "hero_appearance_rate": 0.003218,
                                                "hero_channel": {
                                                    "id": 2678805
                                                },
                                                "hero_index": 1,
                                                "hero_win_rate": 0.447087,
                                                "heroid": 69,
                                                "increase_win_rate": -0.125309,
                                                "min_win_rate10_12": 0.096154,
                                                "min_win_rate12_14": 0.22973,
                                                "min_win_rate14_16": 0.25,
                                                "min_win_rate16_18": 0.342857,
                                                "min_win_rate18_20": 0.526316,
                                                "min_win_rate20": 0.531915,
                                                "min_win_rate6": 0,
                                                "min_win_rate6_8": 0,
                                                "min_win_rate8_10": 0.0625
                                            }
                                        ]
                                    },
                                    "id": 102938,
                                    "sourceId": 2756569
                                }
                            ],
                            "total": 1
                        }
                    }
                }
            }
        }
    }
)
def hero_compatibility(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    days: Annotated[
        Literal["1", "3", "7", "15", "30"],
        Query(
            title="Past Days",
            description="Past day window for rank statistics.",
        )
    ] = "1",
    rank: Annotated[
        RankEnum,
        Query(
            title="Rank",
            description="Rank filter for hero statistics.",
        ),
    ] = RankEnum.ALL,
    size: Annotated[
        int,
        Query(
            title="Page Size",
            description="Number of items per page.",
            ge=1,
        )
    ] = 20,
    index: Annotated[
        int,
        Query(
            title="Page Index",
            description="Page index for pagination.",
            ge=1,
        )
    ] = 1,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    hero_id = _hero_id_or_404(hero_identifier, lang)
    url_map = {"1": "2756567", "3": "2756568", "7": "2756569", "15": "2756565", "30": "2756570"}
    payload = {
        "pageSize": size,
        "filters": [
            {
                "field": "match_type",
                "operator": "eq",
                "value": "1"
            },
            {
                "field": "main_heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "bigrank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            },
        ],
        "sorts": [],
        "pageIndex": index,
    }
    url_key = url_map.get(days, "2756567")
    return fetch_hero_post(url_key, payload, lang)
