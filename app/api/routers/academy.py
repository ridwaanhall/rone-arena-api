from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import require_api_available

from app.services.academy import fetch_academy_post, fetch_ratings_all, fetch_ratings_subject
from app.schemas.academy import AcademyCollectionResponse, AcademyRatingsResponse

from app.core.errors import _hero_id_or_404

from app.core.enums import LanguageEnum, RankEnum, SortOrderEnum, HeroRoleEnum, HeroLaneEnum
from app.utils.client_ip import bind_client_ip
from app.utils.filters import (
    ROLE_MAP, LANE_MAP, validate_and_map_multi, validate_and_map_rank, validate_and_single
)

router = APIRouter(
    prefix="/api/academy",
    tags=["academy"],
    dependencies=[
        Depends(require_api_available),
        Depends(bind_client_ip)
    ]
)


@router.get(
    path="/meta/version",
    name="api.academy.meta_version",
    response_model=AcademyCollectionResponse,
    summary="Game Version Info",
    description=(
        "Fetch a list of game versions with their release dates. "
        "Supports query parameters for pagination, sorting, and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes game version data:\n"
        "- **records**: Array of version entries, each containing:\n"
        "    - **id**: Unique version record identifier.\n"
        "    - **uin**: User identifier associated with the record.\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **game_version**: Version string (e.g., `2.1.18`).\n"
        "    - **form**:\n"
        "        - **id**: Form ID reference.\n"
        "    - **vote_all** (optional): Voting metadata, if available:\n"
        "        - **target**: Target record ID.\n"
        "        - **vote**:\n"
        "            - **id**: Vote ID.\n\n"
        "This endpoint is useful for:\n"
        "- Tracking game version history.\n"
        "- Monitoring release cycles.\n"
        "- Ensuring compatibility with specific patches or updates."
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
                                    "createdAt": 1759044257232,
                                    "data": {
                                        "game_version": "2.1.18"
                                    },
                                    "form": {
                                        "id": 2777742
                                    },
                                    "id": 967057876869504,
                                    "uin": "1",
                                    "updatedAt": 1759044257232
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
def version(
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
            description="Sort order for results.",
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
        "pageIndex": index,
        "filters": [
            {
                "field": "formId",
                "operator": "eq",
                "value": 2777742
            }
        ],
        "sorts": [
            {
                "data":
                    {
                        "field": "createdAt",
                        "order": order
                    }
                ,
                "type": "sequence"
            }
        ],
        "type": "form.item.all",
        "object": [2675413],
    }
    return fetch_academy_post("2718124", payload, lang)


@router.get(
    path="/heroes/catalog",
    name="api.academy.heroes_catalog",
    response_model=AcademyCollectionResponse,
    summary="Hero Catalog",
    description=(
        "Supports query parameters for pagination and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero catalog data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **head**: Hero portrait image URL.\n"
        "        - **head_big**: Larger hero portrait image URL.\n"
        "        - **painting**: Hero splash art image URL.\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **name**: Hero name.\n"
        "                - **roadsort**: Lane assignment metadata:\n"
        "                    - **_id**: Unique identifier.\n"
        "                    - **caption**: Lane caption (localized).\n"
        "                    - **configId**: Configuration ID.\n"
        "                    - **createdAt**: Creation timestamp.\n"
        "                    - **createdUser**: Creator username.\n"
        "                    - **data**:\n"
        "                        - **road_sort_icon**: Lane icon URL.\n"
        "                        - **road_sort_id**: Lane ID.\n"
        "                        - **road_sort_title**: Lane title (e.g., Roam).\n"
        "                    - **updatedAt**: Last update timestamp.\n"
        "                    - **updatedUser**: Last updater username.\n"
        "        - **hero_id**: Unique hero identifier.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying hero collections.\n"
        "- Browsing available heroes.\n"
        "- Analyzing basic hero attributes.\n\n"
    ),
    deprecated=True,
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
                                        "head": "https://akmweb.youngjoygame.com/web/gms/image/e7aa2ab69d15fc168b2d60b0e5ed0a1e.jpg",
                                        "head_big": "https://akmweb.youngjoygame.com/web/gms/image/3542718f699058d42801d88ec9b8fb8b.jpg",
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
                                                ]
                                            }
                                        },
                                        "hero_id": 132,
                                        "painting": "https://akmweb.youngjoygame.com/web/gms/image/24c43180662d27aa5b62106b596fa4f7.webp"
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
def heroes_old(
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [],
        "sorts": [],
        "fields": ["head", "head_big", "hero.data.name", "hero.data.roadsort", "hero_id", "painting"],
        "object": [2667538],
    }
    return fetch_academy_post("2766683", payload, lang)


@router.get(
    path="/roles",
    name="api.academy.roles",
    response_model=AcademyCollectionResponse,
    summary="Roles",
    description=(
        "List all hero roles available in the game (Tank, Fighter, Assassin, Mage, Marksman, Support). "
        "Supports query parameters for pagination, sorting, and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes role data:\n"
        "- **records**: Array of role entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **caption**: Localized role caption (e.g., '坦克', '法师').\n"
        "    - **configId**: Configuration ID.\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **createdUser**: Creator username.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **updatedUser**: Last updater username.\n"
        "    - **data**:\n"
        "        - **emblem_id**: Emblem ID associated with the role.\n"
        "        - **emblem_title**: Emblem title (e.g., 'Tank', 'Mage').\n"
        "        - **emblem_icon**: Emblem icon URL.\n"
        "        - **emblem_detail**:\n"
        "            - **_id**: Emblem detail record ID.\n"
        "            - **_createdAt**: Creation timestamp.\n"
        "            - **_updatedAt**: Last update timestamp.\n"
        "            - **data**:\n"
        "                - **emblemid**: Emblem ID.\n"
        "                - **emblemname**: Emblem name (e.g., 'Assassin').\n"
        "                - **emblemattrid**: Attribute ID.\n"
        "                - **emblemattr**: Attribute bonuses (e.g., '+500 Extra Max HP').\n"
        "                - **attriicon**: Attribute icon URL.\n"
        "                - **attriicon2**: Secondary attribute icon URL (optional).\n"
        "                - **emblembg**: Background indicator.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying role categories.\n"
        "- Explaining role-specific attributes and emblem bonuses.\n"
        "- Guiding players in hero selection based on roles."
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
                                    "_id": "6698bd01613093b976b4a90b",
                                    "caption": "通用",
                                    "configId": 144237,
                                    "createdAt": 1721285889064,
                                    "createdUser": "nickjin",
                                    "data": {
                                        "_object": 2740627,
                                        "emblem_detail": {
                                            "_createdAt": 1723097697235,
                                            "_id": "66b46261f25dc3aacf517fa1",
                                            "_updatedAt": 1727436297890,
                                            "data": {
                                                "attriicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_4e0cd7364830b178279479bff1146e5e.png",
                                                "attriicon2": "",
                                                "emblemattr": {
                                                    "emblemattr": "+12 HP Regen\n+12 Mana Regen\n+275 Extra Max HP\n+22 Adaptive Attack\n",
                                                    "emblemattrid": "2000160",
                                                    "emblemname": "All"
                                                },
                                                "emblembg": 0,
                                                "emblemid": 20001,
                                                "emblemname": "All"
                                            },
                                            "id": 100050,
                                            "sourceId": 2718120
                                        },
                                        "emblem_icon": "https://akmweb.youngjoygame.com/web/gms/image/cf9a85ddcdc9d53f3a1b76f8d8965d53.svg",
                                        "emblem_id": 20001,
                                        "emblem_title": "All"
                                    },
                                    "dynamic": None,
                                    "id": 2740640,
                                    "linkId": [2740627],
                                    "sort": 0,
                                    "updatedAt": 1721287925214,
                                    "updatedUser": "nickjin"
                                }
                            ],
                            "total": 7
                        }
                    }
                }
            }
        }
    }
)
def roles(
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
            description="Sort order by emblem_id.",
        )
    ] = SortOrderEnum.ASCENDING,
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
        "pageIndex": index,
        "filters": [],
        "sorts": [
            {
                "data":
                    {
                        "field": "emblem_id",
                        "order": order
                    }
                ,
                "type": "sequence"
            }
        ],
        "object": [],
    }
    return fetch_academy_post("2740642", payload, lang)


@router.get(
    path="/equipment",
    name="api.academy.equipment",
    response_model=AcademyCollectionResponse,
    summary="Equipment (Items)",
    description=(
        "List all equipment (items). Supports query parameters for pagination and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes equipment data:\n"
        "- **records**: Array of equipment entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **equipid**: Equipment ID.\n"
        "        - **equipname**: Equipment name (e.g., 'Bud of Hope').\n"
        "        - **equipicon**: Equipment icon URL.\n"
        "    - **id**: Internal record ID.\n"
        "    - **sourceId**: Source reference ID.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying the full equipment catalog.\n"
        "- Browsing available items.\n"
        "- Analyzing basic item attributes."
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
                                    "_createdAt": 1762773906608,
                                    "_id": "6911cb92f45ef3d6c8c6340e",
                                    "_updatedAt": 1762773906608,
                                    "data": {
                                        "equipicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_e7f1b44153bd079824ececabb14cf901.png",
                                        "equipid": 10002,
                                        "equipname": "Bud of Hope"
                                    },
                                    "id": 101281,
                                    "sourceId": 2775075
                                }
                            ],
                            "total": 184
                        }
                    }
                }
            }
        }
    }
)
def equipment(
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [],
        "sorts": []
    }
    return fetch_academy_post("2775075", payload, lang)


@router.get(
    path="/equipment/expanded",
    name="api.academy.equipment_expanded",
    response_model=AcademyCollectionResponse,
    summary="Equipment Expanded",
    description=(
        "Get detailed information about a specific equipment item. "
        "Supports query parameters for pagination and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes detailed equipment data:\n"
        "- **records**: Array of equipment entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **equipid**: Equipment ID.\n"
        "        - **equipname**: Equipment name (e.g., 'Demon Boots - Favor').\n"
        "        - **equipicon**: Equipment icon URL.\n"
        "        - **equiptype**: Equipment type ID.\n"
        "        - **equiptypename**: Equipment type name (e.g., 'Roam').\n"
        "        - **equipskill1-7**: Passive skills or effects (raw text segments).\n"
        "        - **equipskilldesc**: Full description of equipment skills and effects.\n"
        "        - **equiptips**: Item tips or stat bonuses (e.g., '+40 Movement Speed').\n"
        "        - **targetequipid**: Target equipment ID (if linked).\n"
        "    - **id**: Internal record ID.\n"
        "    - **sourceId**: Source reference ID.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying full item details.\n"
        "- Explaining equipment effects and passive skills.\n"
        "- Guiding players in equipment selection and strategy."
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
                                    "_createdAt": 1773221702699,
                                    "_id": "69b13746b58eb3622c8297a5",
                                    "_updatedAt": 1773221702699,
                                    "data": {
                                        "equipicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_ca2a5c2be6010eb0ecff954a27bf05db.png",
                                        "equipid": 3573,
                                        "equipname": "Demon Boots - Favor",
                                        "equipskill1": "\nPassive - Favor: ",
                                        "equipskill2": "\n: ",
                                        "equipskill3": "\nMysticism: Getting a kill or assist on an enemy Minion will restore 4% Mana. (An assist occurs when a Minion dies within 2s after taking damage from the hero.)",
                                        "equipskill4": "\n<font color=\"FFD700\">Devotion</font>: When near allied heroes, does not share Gold and EXP from minions and creep, but gains 35% Gold and EXP independently. Revealing enemies also grants Gold and EXP.\n A maximum of 2000 Gold can be gained through this skill. (Only triggers when you have the lowest Gold among all heroes with active Roaming Blessing on your team).",
                                        "equipskill5": "\n<font color=\"FFD700\">Thriving</font>: <font color=\"7f62fe\">Unique in Team</font>: Gain 6 Gold and 12 EXP every 5s. After 8 minutes into the match, gain an additional 66% boost (only triggers when you have the lowest Gold among all heroes with active Roaming Blessing on your team).",
                                        "equipskill6": "\n<font color=\"FFD700\">Blessing</font>: Accumulate 1000 Gold via Devotion and Thriving to unlock a skill.\n<font color=\"A4AAC7\">During the first 5 minutes, Minion rewards are reduced to 50% when earned alone. After 2 minutes, Roaming Blessing can no longer be enchanted.</font>",
                                        "equipskill7": "\n: ",
                                        "equipskilldesc": "\nPassive - Favor: \nMysticism: Getting a kill or assist on an enemy Minion will restore 4% Mana. (An assist occurs when a Minion dies within 2s after taking damage from the hero.)\n<font color=\"FFD700\">Devotion</font>: When near allied heroes, does not share Gold and EXP from minions and creep, but gains 35% Gold and EXP independently. Revealing enemies also grants Gold and EXP.\n A maximum of 2000 Gold can be gained through this skill. (Only triggers when you have the lowest Gold among all heroes with active Roaming Blessing on your team).\n<font color=\"FFD700\">Thriving</font>: <font color=\"7f62fe\">Unique in Team</font>: Gain 6 Gold and 12 EXP every 5s. After 8 minutes into the match, gain an additional 66% boost (only triggers when you have the lowest Gold among all heroes with active Roaming Blessing on your team).\n<font color=\"FFD700\">Blessing</font>: Accumulate 1000 Gold via Devotion and Thriving to unlock a skill.\n<font color=\"A4AAC7\">During the first 5 minutes, Minion rewards are reduced to 50% when earned alone. After 2 minutes, Roaming Blessing can no longer be enchanted.</font>",
                                        "equiptips": "+40 Movement Speed<br>+10 Mana Regen<br>",
                                        "equiptype": "5",
                                        "equiptypename": "Roam",
                                        "targetequipid": ""
                                    },
                                    "id": 106413,
                                    "sourceId": 2713995
                                }
                            ],
                            "total": 152
                        }
                    }
                }
            }
        }
    }
)
def equipment_expanded(
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [],
        "sorts": []
    }
    return fetch_academy_post("2713995", payload, lang)


@router.get(
    path="/spells",
    name="api.academy.spells",
    response_model=AcademyCollectionResponse,
    summary="Battle Spells",
    description=(
        "List all battle spells with details. Supports query parameters for pagination and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes battle spell data:\n"
        "- **records**: Array of spell entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **battleskillid**: Battle spell ID.\n"
        "        - **skillid**: Skill ID.\n"
        "        - **skillname**: Spell name (e.g., 'Arrival').\n"
        "        - **skillicon**: Spell icon URL.\n"
        "        - **skillshortdesc**: Short description (e.g., 'Long-range Support').\n"
        "        - **skilldesc**: Full description of spell effects.\n"
        "        - **skilldescemblem**: Emblem-specific description (if applicable).\n"
        "        - **skillvideo**: Video reference (if available).\n"
        "    - **id**: Internal record ID.\n"
        "    - **sourceId**: Source reference ID.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying the complete catalog of battle spells.\n"
        "- Explaining spell effects and mechanics.\n"
        "- Guiding players in spell selection and strategy."
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
                                    "_createdAt": 1723097697296,
                                    "_id": "66b46261f25dc3aacf517fb2",
                                    "_updatedAt": 1723097697296,
                                    "data": {
                                        "__data": {
                                            "skilldesc": "After channeling for 3s, teleport to the target allied Turret, Base, Minion, or trap and gain 60% extra Movement Speed (decays over 3s) afterward.\nIf the channeling is canceled or interrupted, 30s of the spell cooldown will be <font color=\"62f8fe\">refunded</font>.",
                                            "skilldescemblem": "After channeling for 3s, teleport to the target allied Turret, Base, Minion, or trap and gain 60% extra Movement Speed (decays over 3s) afterward.\nIf the channeling is canceled or interrupted, 30s of the spell cooldown will be <font color=\"62f8fe\">refunded</font>.",
                                            "skillicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_e4c101cdf5311dc1ce58bd8385c1c478.png",
                                            "skillid": 20160,
                                            "skillname": "Arrival"
                                        },
                                        "battleskillid": 20160,
                                        "skillicon": "@__data.skillicon",
                                        "skillname": "@__data.skillname1",
                                        "skillshortdesc": "Long-range Support",
                                        "skillvideo": ""
                                    },
                                    "id": 100059,
                                    "sourceId": 2718122
                                }
                            ],
                            "total": 12
                        }
                    }
                }
            }
        }
    }
)
def spells(
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [],
        "sorts": []
    }
    return fetch_academy_post("2718122", payload, lang)


@router.get(
    path="/emblems",
    name="api.academy.emblems",
    response_model=AcademyCollectionResponse,
    summary="Emblems",
    description=(
        "List all emblems with details. Supports query parameters for pagination and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes emblem data:\n"
        "- **records**: Array of emblem entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **giftid**: Emblem ID.\n"
        "        - **gifttiers**: Emblem tier level.\n"
        "        - **emblemskill**: Associated skill details:\n"
        "            - **skillid**: Skill ID.\n"
        "            - **skillid_lv**: Skill ID with level reference.\n"
        "            - **skillname**: Skill name (e.g., 'Weapons Master').\n"
        "            - **skillicon**: Skill icon URL.\n"
        "            - **skilldesc**: Full description of skill effects.\n"
        "            - **skilldesc_text**: Template-based description with placeholders.\n"
        "            - **skilldescemblem**: Emblem-specific description.\n"
        "            - **numdescribe**: Numeric effect values (e.g., '5%').\n"
        "    - **id**: Internal record ID.\n"
        "    - **sourceId**: Source reference ID.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying the full emblem catalog.\n"
        "- Explaining emblem effects and associated skills.\n"
        "- Guiding players in emblem selection and optimization."
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
                                    "_createdAt": 1736302497664,
                                    "_id": "677ddfa16cecfab942bd1208",
                                    "_updatedAt": 1736302497664,
                                    "data": {
                                        "emblemskill": {
                                            "numdescribe": "5%",
                                            "skilldesc": "Physical Attack and Magic Power gained from equipment, emblem, talents, and skills are increased by 5%.",
                                            "skilldesc_text": "Physical Attack and Magic Power gained from equipment, emblem, talents, and skills are increased by <%Num1>.",
                                            "skilldescemblem": "Physical Attack and Magic Power gained from equipment, emblem, talents, and skills are increased by 5%.",
                                            "skillicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_893891a86726cbf0b00401127a1f9486.png",
                                            "skillid": 61010,
                                            "skillid_lv": "61010/1",
                                            "skillname": "Weapons Master"
                                        },
                                        "giftid": 1221,
                                        "gifttiers": 2
                                    },
                                    "id": 100333,
                                    "sourceId": 2718121
                                }
                            ],
                            "total": 26
                        }
                    }
                }
            }
        }
    }
)
def emblems(
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [],
        "sorts": []
    }
    return fetch_academy_post("2718121", payload, lang)


@router.get(
    path="/ranks",
    name="api.academy.ranks",
    response_model=AcademyCollectionResponse,
    summary="Ranks List",
    description=(
        "Retrieve all rank information for Mobile Legends: Bang Bang. Supports query parameters for pagination and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes rank data:\n"
        "- **records**: Array of rank entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **configId**: Configuration ID.\n"
        "    - **caption**: Localized caption (e.g., '1-4勇士Ⅲ').\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **createdUser**: Creator username.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **updatedUser**: Last updater username.\n"
        "    - **data**:\n"
        "        - **bigrank**: Major rank ID (e.g., 1).\n"
        "        - **bigrank_name**: Major rank name (e.g., '勇士').\n"
        "        - **icon**: Rank icon URL.\n"
        "        - **minrank**: Minor rank ID (e.g., '1').\n"
        "        - **minrank_name**: Minor rank name (e.g., 'Ⅲ').\n"
        "        - **rankid_start**: Starting rank ID in the range.\n"
        "        - **rankid_end**: Ending rank ID in the range.\n"
        "    - **id**: Internal record ID.\n"
        "    - **sort**: Sorting index.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying the full rank progression system.\n"
        "- Explaining rank tiers and ranges.\n"
        "- Guiding players in understanding the game's ranking structure."
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
                                    "_id": "6908a30ee594c8676a88ed72",
                                    "configId": 144237,
                                    "id": 3210595,
                                    "caption": "1-4勇士Ⅲ",
                                    "data": {
                                        "_object": 3210429,
                                        "bigrank": 1,
                                        "bigrank_name": "勇士",
                                        "icon": "https://akmweb.youngjoygame.com/web/gms/image/e8659ed5040a378701beca13ebdc4fba.png",
                                        "minrank": "1",
                                        "minrank_name": "Ⅲ",
                                        "rankid_end": 4,
                                        "rankid_start": 1
                                    },
                                    "dynamic": None,
                                    "createdUser": "v_xyxu",
                                    "createdAt": 1762173710696,
                                    "updatedAt": 1762173714202,
                                    "updatedUser": "v_xyxu",
                                    "sort": 0
                                }
                            ],
                            "total": 29
                        }
                    }
                }
            }
        }
    }
)
def ranks(
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [],
        "sorts": [],
        "object": []
    }
    return fetch_academy_post("3210596", payload, lang)


@router.get(
    path="/ranks/{rank_id}",
    name="api.academy.ranks_details",
    response_model=AcademyCollectionResponse,
    summary="Ranks Details",
    description=(
        "Retrieve details for a specific rank in Mobile Legends: Bang Bang by rank ID. "
        "Supports query parameter for localization.\n\n"
        "Path parameters:\n"
        "- **rank_id**: Rank ID (validated dynamically from current rank list). "
        "Minimum: 1, Maximum: 9999.\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes detailed rank data:\n"
        "- **records**: Array of rank entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **configId**: Configuration ID.\n"
        "    - **caption**: Localized caption (e.g., '236-9999荣耀神话').\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **createdUser**: Creator username.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **updatedUser**: Last updater username.\n"
        "    - **data**:\n"
        "        - **bigrank**: Major rank ID (e.g., 7).\n"
        "        - **bigrank_name**: Major rank name (e.g., '荣耀神话').\n"
        "        - **icon**: Rank icon URL.\n"
        "        - **rankid_start**: Starting rank ID in the range.\n"
        "        - **rankid_end**: Ending rank ID in the range.\n"
        "    - **id**: Internal record ID.\n"
        "    - **linkId**: Linked object references.\n"
        "    - **sort**: Sorting index.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying detailed information about a single rank tier.\n"
        "- Explaining its position in the progression system.\n"
        "- Guiding players in understanding the game's ranking structure."
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
                                    "_id": "6908a30ee594c8676a88ed08",
                                    "configId": 144237,
                                    "id": 3210567,
                                    "caption": "236-9999荣耀神话",
                                    "data": {
                                        "_object": 3210429,
                                        "bigrank": 7,
                                        "bigrank_name": "荣耀神话",
                                        "icon": "https://akmweb.youngjoygame.com/web/gms/image/191257b84f57be74430d1964c4b01c8b.png",
                                        "rankid_end": 9999,
                                        "rankid_start": 236
                                    },
                                    "dynamic": None,
                                    "createdUser": "v_xyxu",
                                    "createdAt": 1762173710344,
                                    "updatedAt": 1762173748966,
                                    "updatedUser": "v_xyxu",
                                    "linkId": [3210429],
                                    "sort": 0
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
def ranks_details(
    rank_id: Annotated[
        int,
        Path(
            title="Rank ID",
            description="Rank ID. Maximum is validated dynamically from current rank list.",
            ge=1,
            le=9999
        )
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    payload = {
        "pageSize": 1,
        "pageIndex": 1,
        "filters": [
            {
                "field": "rankid_start",
                "operator": "lte",
                "value": rank_id
            },
            {
                "field": "rankid_end",
                "operator": "gte",
                "value": rank_id
            }
        ],
        "sorts": [],
        "object": []
    }
    return fetch_academy_post("3210596", payload, lang)


@router.get(
    path="/recommended",
    name="api.academy.recommended",
    response_model=AcademyCollectionResponse,
    summary="Recommended Content",
    description=(
        "List recommended content for players. Supports query parameters for pagination, sorting, and localization.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes recommended content data:\n"
        "- **records**: Array of recommended entries, each containing:\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **channels**: Content channels (e.g., 'UGC', 'recommend').\n"
        "        - **type**: Content type (e.g., 'ugc_hero').\n"
        "        - **state**: Content state (e.g., 'release').\n"
        "        - **data**:\n"
        "            - **hero**: Hero metadata including:\n"
        "                - **hero_id**: Hero ID.\n"
        "                - **hero_lane**: Lane assignment.\n"
        "                - **hero_overview**: Overview description.\n"
        "                - **hero_strength**: Strengths.\n"
        "                - **hero_weakness**: Weaknesses.\n"
        "                - **hero_tags**: Array of tag IDs.\n"
        "            - **equips**: Recommended equipment builds.\n"
        "            - **emblems**: Recommended emblem sets.\n"
        "            - **spell**: Recommended battle spell.\n"
        "            - **cooperates**: Cooperative hero synergies.\n"
        "            - **counters**: Counter heroes.\n"
        "            - **dominants**: Dominant strategies or tips.\n"
        "            - **recommend**: General recommendation notes.\n"
        "            - **snapshot**: Snapshot image URL.\n"
        "            - **game_version**: Version reference.\n"
        "            - **language**: Content language.\n"
        "            - **pages**: Content sections (e.g., 'hero', 'spell', 'equip').\n"
        "            - **title**: Guide or build title.\n"
        "        - **user**: Author metadata including:\n"
        "            - **name**: Author name.\n"
        "            - **avatar**: Author avatar URL.\n"
        "            - **level**: Author level.\n"
        "            - **roleId**: Role ID.\n"
        "            - **zoneId**: Zone ID.\n"
        "        - **dynamic**: Engagement metrics:\n"
        "            - **views**: Total views.\n"
        "            - **votes**: Total votes.\n"
        "            - **hot**: Hotness score.\n"
        "            - **views_by_4h_total_24h**: Views in last 24h.\n"
        "        - **vote_all**: Voting metadata:\n"
        "            - **average**: Average rating.\n"
        "            - **count**: Vote count.\n"
        "            - **total**: Total votes.\n"
        "            - **user_count**: Number of users voted.\n"
        "            - **vote**: Vote ID reference.\n\n"
        "This endpoint is useful for:\n"
        "- Surfacing community guides and builds.\n"
        "- Providing personalized hero strategies.\n"
        "- Highlighting cooperative and counter hero recommendations.\n"
        "- Guiding players with contextual tips and strategic insights."
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
                                    "createdAt": 1774497670372,
                                    "data": {
                                        "channels": ["UGC", "recommend"],
                                        "data": {
                                            "cooperates": [
                                                {
                                                    "cooperate_desc": "Best With: Long-range heroes like Pharsa, Yve, or Granger who can stand outside his Ultimate circle and fire into it while the enemies are frozen.",
                                                    "cooperate_hero_id": 101,
                                                    "cooperate_rate": 100
                                                },
                                                {
                                                    "cooperate_desc": "Best With: Long-range heroes like Pharsa, Yve, or Granger who can stand outside his Ultimate circle and fire into it while the enemies are frozen.",
                                                    "cooperate_hero_id": 52,
                                                    "cooperate_rate": 100
                                                }
                                            ],
                                            "counters": [
                                                {
                                                    "counter_desc": "Weak Against: Diggie (can't cleanse the freeze, but can shield through the aftermath) and Karrie (True Damage ignores his high defense).",
                                                    "counter_hero_id": 48,
                                                    "counter_rate": 20
                                                }
                                            ],
                                            "data_version": 1,
                                            "dominants": [
                                                {
                                                    "dominant_desc": "Focus on annoying the enemy Jungler or Marksman. Use your passive \"snaps\" to poke and gain shields. You are surprisingly tanky at level 1.",
                                                    "dominant_title": "Early Game"
                                                },
                                                {
                                                    "dominant_desc": "Roam with your Mid-laner. Use Skill 2 to scout bushes. Your job is to set up \"Frames\" (Skill 1) for your damage dealers.",
                                                    "dominant_title": "Mid Game"
                                                },
                                                {
                                                    "dominant_desc": "You are the ultimate disruptor. Wait for the enemy to commit their big Ultimates (like Terizla or Guinevere), then use Golden Hour to negate their entire initiation.",
                                                    "dominant_title": "Late Game"
                                                }
                                            ],
                                            "emblems": [
                                                {
                                                    "emblem_desc": "\n✨ Agility / Vitality: Higher movement speed helps you position your camera shots perfectly.\n\n✨ Tenacity: Increases physical and magic defense when HP is low—since your damage scales with defense, this actually makes you stronger when you're \"losing.\"\n\n✨ Focusing Mark: When you hit an enemy (which Clemar does automatically), your teammates deal 6% more damage to them. Perfect for a support.\n\n",
                                                    "emblem_gifts": [811, 321, 831],
                                                    "emblem_id": 20001,
                                                    "emblem_title": "Emblem: Support Emblem (for Cooldown and Movement Speed) or Tank Emblem (for pure scaling)."
                                                }
                                            ],
                                            "equips": [
                                                {
                                                    "equip_desc": "Rapid Boots/Tough Boots: Roam blessing (Encourage or Conceal).  \n\nThunder Belt: This is his core item. It provides True Damage and scales with his defensive stats.\n\nDominance Ice: Essential for anti-heal and more defense scaling.\n\nOracle: Boosts the shields he gets from his passive.\n\nAthena's Shield / Antique Cuirass: Standard defense based on enemy composition.\n\nImmortality: For late-game insurance.",
                                                    "equip_ids": [3562, 2212, 3206, 3204, 3205, 3207],
                                                    "equip_title": "MARCEL'S BUILD ITEMS"
                                                }
                                            ],
                                            "game_version": "2.1.18",
                                            "hero": {
                                                "hero_id": 132,
                                                "hero_lane": "3",
                                                "hero_overview": "Marcel, the \"Soul Photographer\" of the Paxley family. Released on March 11, 2026, he is the 132nd hero in Mobile Legends: Bang Bang. Marcel is a unique Support/Tank who introduces the \"Frozen Moment\" mechanic—literally pausing time for friends and foes alike.  Marcel carries a sentient camera named Clemar. He does not just stun enemies; he freezes them in stasis. Interestingly, Marcel is a \"HP-to-Defense\" converter, meaning he gains tankiness from health items but scales his damage and shields through his defensive stats. \n\n\nHERO SKILLS:\n\n📸 Passive (Platinum Snap): Marcel cannot Crit and doesn't benefit from extra Attack Speed. Instead, Extra HP is converted into 1.5% Hybrid Defense. Clemar automatically \"snaps\" photos of nearby enemies, dealing True Damage based on their Max HP and granting Marcel a shield.\n\n📷 Skill 1 (Framed Moment): Clemar takes a delayed shot in an area. After a short delay, enemies inside are immobilized and take physical damage that scales with Marcel's Physical and Magic Defense.\n\n📷 Skill 2 (Tracking Shot): A mobility skill. Marcel enters a \"Tracking Haste\" state, gaining movement speed that increases as he nears enemies. Recasting allows him to dash, leaving a phantom behind. \n\n📸 Ultimate (Golden Hour): Marcel creates a massive wide-angle stasis field. Everything inside—enemies, allies, lord, turrets, and even flying projectiles—is frozen in time. Only Marcel can move and deal damage inside.\n\n\nStandard Combo:\nSkill 2 (Approach) > Skill 1 (Position) > Basic Attacks > Ultimate (to secure the kill or reset the fight).",
                                                "hero_strength": "✨Anti-Projectile: His Ultimate can literally stop a Franco hook or a Novaria blast mid-air.\n\n✨Insane Durability: Because his HP converts to Hybrid Defense, he becomes incredibly difficult to kill with standard penetration.\n\n✨Objective Control: He can freeze the enemy Jungler to prevent them from using Retribution on the Lord.",
                                                "hero_tags": [3, 14, 10],
                                                "hero_weakness": "✨Double-Edged Sword: A poorly timed Ultimate can freeze your own teammates, ruining their big plays.  \n\n✨Zero Burst: He relies on sustained True Damage and CC; he cannot \"delete\" enemies quickly.\n\n✨Vulnerable to True Damage: Since he relies on high Defense stats rather than massive HP pools, heroes like Karrie or Gord can melt him."
                                            },
                                            "language": "en",
                                            "pages": ["hero", "spell", "emblem", "equip", "dominant", "cooperate"],
                                            "recommend": "Marcel Comprehensive Guide You Have Been Waiting For!",
                                            "snapshot": "https://akmweb.youngjoygame.com/web/academy/image/fca9cfad744e7627f963e19dd8a74cd7.jpeg",
                                            "spell": {
                                                "spell_desc": "📸 Flicker: Essential for \"Flash-Ult\" plays to catch the entire enemy backline.\n\nOTHER BATTLE SPELLS: \n📷 Vengeance: Great for soaking up damage while you wait for your Skill 1 or Ultimate to trigger.\n\n📷 Revitalize: Works well if you are playing a more \"stay-at-home\" support style.",
                                                "spell_id": 20100
                                            },
                                            "title": "Frame the Meta: A Grandmaster's Guide to Marcel"
                                        },
                                        "state": "release",
                                        "type": "ugc_hero"
                                    },
                                    "dynamic": {
                                        "hot": 1530.06,
                                        "views": 368,
                                        "views_by_4h_0": 5,
                                        "views_by_4h_1": 8,
                                        "views_by_4h_2": 3,
                                        "views_by_4h_3": 1,
                                        "views_by_4h_4": 1,
                                        "views_by_4h_total_24h": 19,
                                        "votes": 20
                                    },
                                    "form": {
                                        "id": 2737553
                                    },
                                    "id": 1093652237288192,
                                    "item_uin": [
                                        {
                                            "count": 1,
                                            "item": {
                                                "access": "all",
                                                "desc": "MLBB Academy Top Creators Reward",
                                                "icon": "https://akmweb.youngjoygame.com/web/gms/image/222cad2f3870af05c1e45b5a4f2eba03.png",
                                                "id": 2758031,
                                                "tags": ["badge", "2"],
                                                "title": "Creative Star",
                                                "usage": {
                                                    "mode": "manual"
                                                }
                                            },
                                            "uin": "mlbb:10022:581066511",
                                            "user": {
                                                "avatar": "https://akmpicture.youngjoygame.com/dist/face/10022/11/65/4_new_574293fa-09f9-4f11-bc78-a29e13b8f040.jpg",
                                                "historyRankLevel": 436,
                                                "level": 139,
                                                "module": "mlbb",
                                                "name": " coco",
                                                "registerCountry": "ph",
                                                "registerTime": 1575135242,
                                                "roleId": 581066511,
                                                "zoneId": 10022
                                            }
                                        }
                                    ],
                                    "uin": "mlbb:10022:581066511",
                                    "updatedAt": 1774498623794,
                                    "user": {
                                        "avatar": "https://akmpicture.youngjoygame.com/dist/face/10022/11/65/4_new_574293fa-09f9-4f11-bc78-a29e13b8f040.jpg",
                                        "historyRankLevel": 436,
                                        "level": 139,
                                        "module": "mlbb",
                                        "name": " coco",
                                        "roleId": 581066511,
                                        "zoneId": 10022
                                    },
                                    "vote_all": {
                                        "average": 1,
                                        "count": 20,
                                        "target": "1093652237288192",
                                        "total": 20,
                                        "user_count": 20,
                                        "vote": {
                                            "id": 2758890
                                        }
                                    }
                                }
                            ],
                            "total": 10000
                        }
                    }
                }
            }
        }
    }
)
def recommended(
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
            description="Order by trending and creation date.",
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
        "pageIndex": index,
        "filters": [
            {
                "field": "formId",
                "operator": "eq",
                "value": 2737553
            },
            {
                "field": "data.state",
                "operator": "eq",
                "value": "release"
            },
            {
                "field": "data.channels",
                "operator": "in",
                "value": ["recommend"]
            },
            {
                "field": "uin",
                "operator": "contain",
                "value": "/.*/"
            },
            {
                "field": "data.data.game_version",
                "operator": "contain",
                "value": "/.*/"
            },
            {
                "field": "data.data.language",
                "operator": "eq",
                "value": lang
            },
            {
                "field": "createdAt",
                "operator": "gte",
                "value": 1
            },
        ],
        "sorts": [
            {
                "data":
                {
                    "field": "dynamic.hot",
                    "order": order
                },
                "type": "sequence"
            },
            {
                "data":
                {
                    "field": "createdAt",
                    "order": order
                },
                "type": "sequence"
            },
        ],
        "type": "form.item.all",
        "object": [2675413],
    }
    return fetch_academy_post("2718124", payload, lang)


@router.get(
    path="/recommended/{recommended_id}",
    name="api.academy.recommended_detail",
    response_model=AcademyCollectionResponse,
    summary="Recommended Detail",
    description=(
        "Get details for a specific recommended content item by its identifier. "
        "Supports query parameters for pagination and localization.\n\n"
        "Path parameters:\n"
        "- **recommended_id**: Identifier for the recommended post (minimum: 1).\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes detailed recommended content data:\n"
        "- **records**: Array of recommended entries, each containing:\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **channels**: Content channels (e.g., 'UGC', 'recommend').\n"
        "        - **type**: Content type (e.g., 'ugc_hero').\n"
        "        - **state**: Content state (e.g., 'release').\n"
        "        - **data**:\n"
        "            - **hero**: Hero metadata including:\n"
        "                - **hero_id**: Hero ID.\n"
        "                - **hero_lane**: Lane assignment.\n"
        "                - **hero_overview**: Overview description.\n"
        "                - **hero_strength**: Strengths.\n"
        "                - **hero_weakness**: Weaknesses.\n"
        "                - **hero_tags**: Array of tag IDs.\n"
        "            - **equips**: Recommended equipment builds with IDs and descriptions.\n"
        "            - **emblems**: Recommended emblem sets with IDs and descriptions.\n"
        "            - **spell**: Recommended battle spell with ID and description.\n"
        "            - **cooperates**: Cooperative hero synergies with descriptions and rates.\n"
        "            - **counters**: Counter heroes with descriptions and rates.\n"
        "            - **dominants**: Dominant strategies or tips.\n"
        "            - **recommend**: General recommendation notes.\n"
        "            - **snapshot**: Snapshot image URL.\n"
        "            - **game_version**: Version reference.\n"
        "            - **language**: Content language.\n"
        "            - **pages**: Content sections (e.g., 'hero', 'spell', 'equip').\n"
        "            - **title**: Guide or build title.\n"
        "        - **user**: Author metadata including:\n"
        "            - **name**: Author name.\n"
        "            - **avatar**: Author avatar URL.\n"
        "            - **level**: Author level.\n"
        "            - **roleId**: Role ID.\n"
        "            - **zoneId**: Zone ID.\n"
        "        - **dynamic**: Engagement metrics:\n"
        "            - **views**: Total views.\n"
        "            - **votes**: Total votes.\n"
        "            - **hot**: Hotness score.\n"
        "            - **views_by_4h_total_24h**: Views in last 24h.\n"
        "        - **vote_all**: Voting metadata:\n"
        "            - **average**: Average rating.\n"
        "            - **count**: Vote count.\n"
        "            - **total**: Total votes.\n"
        "            - **user_count**: Number of users voted.\n"
        "            - **vote**: Vote ID reference.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying full details of a single guide or build.\n"
        "- Explaining strategic recommendations.\n"
        "- Surfacing community-generated content for Mobile Legends: Bang Bang players."
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
                                    "createdAt": 1774497670372,
                                    "data": {
                                        "channels": ["UGC", "recommend"],
                                        "data": {
                                            "cooperates": [
                                                {
                                                    "cooperate_desc": "Best With: Long-range heroes like Pharsa, Yve, or Granger who can stand outside his Ultimate circle and fire into it while the enemies are frozen.",
                                                    "cooperate_hero_id": 101,
                                                    "cooperate_rate": 100
                                                }
                                            ],
                                            "counters": [
                                                {
                                                    "counter_desc": "Weak Against: Diggie (can't cleanse the freeze, but can shield through the aftermath) and Karrie (True Damage ignores his high defense).",
                                                    "counter_hero_id": 48,
                                                    "counter_rate": 20
                                                }
                                            ],
                                            "data_version": 1,
                                            "dominants": [
                                                {
                                                    "dominant_desc": "Focus on annoying the enemy Jungler or Marksman. Use your passive \"snaps\" to poke and gain shields. You are surprisingly tanky at level 1.",
                                                    "dominant_title": "Early Game"
                                                }
                                            ],
                                            "emblems": [
                                                {
                                                    "emblem_desc": "\n✨ Agility / Vitality: Higher movement speed helps you position your camera shots perfectly.\n\n✨ Tenacity: Increases physical and magic defense when HP is low—since your damage scales with defense, this actually makes you stronger when you're \"losing.\"\n\n✨ Focusing Mark: When you hit an enemy (which Clemar does automatically), your teammates deal 6% more damage to them. Perfect for a support.\n\n",
                                                    "emblem_gifts": [811, 321, 831],
                                                    "emblem_id": 20001,
                                                    "emblem_title": "Emblem: Support Emblem (for Cooldown and Movement Speed) or Tank Emblem (for pure scaling)."
                                                }
                                            ],
                                            "equips": [
                                                {
                                                    "equip_desc": "Rapid Boots/Tough Boots: Roam blessing (Encourage or Conceal).  \n\nThunder Belt: This is his core item. It provides True Damage and scales with his defensive stats.\n\nDominance Ice: Essential for anti-heal and more defense scaling.\n\nOracle: Boosts the shields he gets from his passive.\n\nAthena's Shield / Antique Cuirass: Standard defense based on enemy composition.\n\nImmortality: For late-game insurance.",
                                                    "equip_ids": [3562, 2212, 3206, 3204, 3205, 3207],
                                                    "equip_title": "MARCEL'S BUILD ITEMS"
                                                }
                                            ],
                                            "game_version": "2.1.18",
                                            "hero": {
                                                "hero_id": 132,
                                                "hero_lane": "3",
                                                "hero_overview": "Marcel, the \"Soul Photographer\" of the Paxley family. Released on March 11, 2026, he is the 132nd hero in Mobile Legends: Bang Bang. Marcel is a unique Support/Tank who introduces the \"Frozen Moment\" mechanic—literally pausing time for friends and foes alike.  Marcel carries a sentient camera named Clemar. He does not just stun enemies; he freezes them in stasis. Interestingly, Marcel is a \"HP-to-Defense\" converter, meaning he gains tankiness from health items but scales his damage and shields through his defensive stats. \n\n\nHERO SKILLS:\n\n📸 Passive (Platinum Snap): Marcel cannot Crit and doesn't benefit from extra Attack Speed. Instead, Extra HP is converted into 1.5% Hybrid Defense. Clemar automatically \"snaps\" photos of nearby enemies, dealing True Damage based on their Max HP and granting Marcel a shield.\n\n📷 Skill 1 (Framed Moment): Clemar takes a delayed shot in an area. After a short delay, enemies inside are immobilized and take physical damage that scales with Marcel's Physical and Magic Defense.\n\n📷 Skill 2 (Tracking Shot): A mobility skill. Marcel enters a \"Tracking Haste\" state, gaining movement speed that increases as he nears enemies. Recasting allows him to dash, leaving a phantom behind. \n\n📸 Ultimate (Golden Hour): Marcel creates a massive wide-angle stasis field. Everything inside—enemies, allies, lord, turrets, and even flying projectiles—is frozen in time. Only Marcel can move and deal damage inside.\n\n\nStandard Combo:\nSkill 2 (Approach) > Skill 1 (Position) > Basic Attacks > Ultimate (to secure the kill or reset the fight).",
                                                "hero_strength": "✨Anti-Projectile: His Ultimate can literally stop a Franco hook or a Novaria blast mid-air.\n\n✨Insane Durability: Because his HP converts to Hybrid Defense, he becomes incredibly difficult to kill with standard penetration.\n\n✨Objective Control: He can freeze the enemy Jungler to prevent them from using Retribution on the Lord.",
                                                "hero_tags": [3, 14, 10],
                                                "hero_weakness": "✨Double-Edged Sword: A poorly timed Ultimate can freeze your own teammates, ruining their big plays.  \n\n✨Zero Burst: He relies on sustained True Damage and CC; he cannot \"delete\" enemies quickly.\n\n✨Vulnerable to True Damage: Since he relies on high Defense stats rather than massive HP pools, heroes like Karrie or Gord can melt him."
                                            },
                                            "language": "en",
                                            "pages": ["hero", "spell", "emblem", "equip", "dominant", "cooperate"],
                                            "recommend": "Marcel Comprehensive Guide You Have Been Waiting For!",
                                            "snapshot": "https://akmweb.youngjoygame.com/web/academy/image/fca9cfad744e7627f963e19dd8a74cd7.jpeg",
                                            "spell": {
                                                "spell_desc": "📸 Flicker: Essential for \"Flash-Ult\" plays to catch the entire enemy backline.\n\nOTHER BATTLE SPELLS: \n📷 Vengeance: Great for soaking up damage while you wait for your Skill 1 or Ultimate to trigger.\n\n📷 Revitalize: Works well if you are playing a more \"stay-at-home\" support style.",
                                                "spell_id": 20100
                                            },
                                            "title": "Frame the Meta: A Grandmaster's Guide to Marcel"
                                        },
                                        "state": "release",
                                        "type": "ugc_hero"
                                    },
                                    "dynamic": {
                                        "hot": 1530.06,
                                        "views": 368,
                                        "views_by_4h_0": 5,
                                        "views_by_4h_1": 8,
                                        "views_by_4h_3": 1,
                                        "views_by_4h_4": 1,
                                        "views_by_4h_total_24h": 18,
                                        "votes": 20
                                    },
                                    "form": {
                                        "id": 2737553
                                    },
                                    "id": 1093652237288192,
                                    "item_uin": [
                                        {
                                            "count": 1,
                                            "item": {
                                                "access": "all",
                                                "desc": "MLBB Academy Top Creators Reward",
                                                "icon": "https://akmweb.youngjoygame.com/web/gms/image/222cad2f3870af05c1e45b5a4f2eba03.png",
                                                "id": 2758031,
                                                "tags": ["badge", "2"],
                                                "title": "Creative Star",
                                                "usage": {
                                                    "mode": "manual"
                                                }
                                            },
                                            "uin": "mlbb:10022:581066511",
                                            "user": {
                                                "avatar": "https://akmpicture.youngjoygame.com/dist/face/10022/11/65/4_new_574293fa-09f9-4f11-bc78-a29e13b8f040.jpg",
                                                "historyRankLevel": 436,
                                                "level": 139,
                                                "module": "mlbb",
                                                "name": " coco",
                                                "registerCountry": "ph",
                                                "registerTime": 1575135242,
                                                "roleId": 581066511,
                                                "zoneId": 10022
                                            }
                                        }
                                    ],
                                    "uin": "mlbb:10022:581066511",
                                    "updatedAt": 1774498623794,
                                    "user": {
                                        "avatar": "https://akmpicture.youngjoygame.com/dist/face/10022/11/65/4_new_574293fa-09f9-4f11-bc78-a29e13b8f040.jpg",
                                        "historyRankLevel": 436,
                                        "level": 139,
                                        "module": "mlbb",
                                        "name": " coco",
                                        "roleId": 581066511,
                                        "zoneId": 10022
                                    },
                                    "vote_all": {
                                        "average": 1,
                                        "count": 20,
                                        "target": "1093652237288192",
                                        "total": 20,
                                        "user_count": 20,
                                        "vote": {
                                            "id": 2758890
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
def recommended_detail(
    recommended_id: Annotated[
        int,
        Path(
            title="Recommended Post ID",
            description="The ID of the recommended post to retrieve.",
            ge=1
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
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [
            {
                "field": "formId",
                "operator": "eq",
                "value": 2737553
            },
            {
                "field": "id",
                "operator": "eq",
                "value": recommended_id
            },
            {
                "field": "data.state",
                "operator": "eq",
                "value": "release"
            },
        ],
        "sorts": [],
        "type": "form.item.all",
        "object": [2675413],
    }
    return fetch_academy_post("2718124", payload, lang)


@router.get(
    path="/heroes",
    name="api.academy.heroes",
    response_model=AcademyCollectionResponse,
    summary="Hero Filters",
    description=(
        "Retrieve a list of heroes with filtering options for role and lane. "
        "Supports query parameters for role, lane, pagination, sorting, and localization.\n\n"
        "Query parameters:\n"
        "- **role**: Role filter. Multi allowed: `tank`, `fighter`, `assassin`, `mage`, `marksman`, `support`. "
        "Example: `role=tank&role=fighter`.\n"
        "- **lane**: Lane filter. Multi allowed: `exp`, `mid`, `roam`, `jungle`, `gold`. "
        "Example: `lane=exp&lane=mid`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for results. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero filter data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **hero_id**: Unique hero identifier.\n"
        "        - **head**: Hero portrait image URL.\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **name**: Hero name (e.g., 'Miya').\n\n"
        "This endpoint is useful for:\n"
        "- Filtering heroes by gameplay role.\n"
        "- Filtering heroes by lane assignment.\n"
        "- Displaying customized hero lists in the in-game Academy."
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
                                        "head": "https://akmweb.youngjoygame.com/web/gms/image/299d8aab8de508fff88c1f1e935017cb.jpg",
                                        "hero": {
                                            "data": {
                                                "name": "Miya"
                                            }
                                        },
                                        "hero_id": 1
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
def heroes(
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
    ] = SortOrderEnum.ASCENDING,
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    role_values = validate_and_map_multi(role, ROLE_MAP, [1, 2, 3, 4, 5, 6], "role")
    lane_values = validate_and_map_multi(lane, LANE_MAP, [1, 2, 3, 4, 5], "lane")
    
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [
            {
                "field":"<hero.data.sortid>",
                "operator": "hasAnyOf",
                "value": role_values
            },
            {
                "field":"<hero.data.roadsort>",
                "operator": "hasAnyOf",
                "value": lane_values
            },
        ],
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
        "fields": ["head", "hero_id", "hero.data.name"],
        "object": [],
    }
    return fetch_academy_post("2766683", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/stats",
    name="api.academy.heroes_stats",
    response_model=AcademyCollectionResponse,
    summary="Hero Statistics",
    description=(
        "Retrieve performance statistics for a specific hero by rank. "
        "Supports query parameters for rank, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero statistics data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_hero**:\n"
        "            - **data**:\n"
        "                - **hero**:\n"
        "                    - **data**:\n"
        "                        - **head**: Main hero portrait image URL.\n"
        "                        - **name**: Main hero name.\n"
        "        - **main_heroid**: Main hero ID.\n"
        "        - **main_hero_appearance_rate**: Pick rate of the main hero.\n"
        "        - **main_hero_ban_rate**: Ban rate of the main hero.\n"
        "        - **main_hero_win_rate**: Win rate of the main hero.\n"
        "        - **sub_hero**: Array of synergy heroes, each containing:\n"
        "            - **heroid**: Hero ID.\n"
        "            - **hero_win_rate**: Win rate of the synergy hero.\n"
        "            - **hero_appearance_rate**: Pick rate of the synergy hero.\n"
        "            - **increase_win_rate**: Positive synergy impact on win rate.\n"
        "            - **min_win_rate6-20**: Win rate breakdown across match durations.\n"
        "            - **hero**:\n"
        "                - **data**:\n"
        "                    - **hero**:\n"
        "                        - **data**:\n"
        "                            - **head**: Synergy hero portrait image URL.\n"
        "        - **sub_hero_last**: Array of negative synergy heroes, each containing:\n"
        "            - **heroid**: Hero ID.\n"
        "            - **hero_win_rate**: Win rate of the sub-hero.\n"
        "            - **hero_appearance_rate**: Pick rate of the sub-hero.\n"
        "            - **increase_win_rate**: Negative impact on win rate.\n"
        "            - **min_win_rate6-20**: Win rate breakdown across match durations.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing hero performance across different ranks.\n"
        "- Understanding meta trends.\n"
        "- Guiding players in hero selection and strategy."
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
                                    "_createdAt": 1725607499154,
                                    "_id": "66daae4baf5771f18c504066",
                                    "_updatedAt": 1774890906305,
                                    "data": {
                                        "bigrank": "101",
                                        "camp_type": "1",
                                        "main_hero": {
                                            "data": {
                                                "hero": {
                                                    "data": {
                                                        "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_3391df36d6dcc54dd1c417098e15ec59.png",
                                                        "name": "Fanny"
                                                    }
                                                }
                                            }
                                        },
                                        "main_hero_appearance_rate": 0.007866,
                                        "main_hero_ban_rate": 0.042957,
                                        "main_hero_win_rate": 0.442515,
                                        "main_heroid": 17,
                                        "match_type": "1",
                                        "sub_hero": [
                                            {
                                                "hero": {
                                                    "data": {
                                                        "hero": {
                                                            "data": {
                                                                "head": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_da02742f59013365923b216420bc4082.png"
                                                            }
                                                        }
                                                    }
                                                },
                                                "hero_appearance_rate": 0.007849,
                                                "hero_index": 1,
                                                "hero_win_rate": 0.540854,
                                                "heroid": 107,
                                                "increase_win_rate": 0.02013,
                                                "min_win_rate10_12": 0.5543,
                                                "min_win_rate12_14": 0.510571,
                                                "min_win_rate14_16": 0.479701,
                                                "min_win_rate16_18": 0.476889,
                                                "min_win_rate18_20": 0.474236,
                                                "min_win_rate20": 0.4885,
                                                "min_win_rate6": 0.79602,
                                                "min_win_rate6_8": 0.594158,
                                                "min_win_rate8_10": 0.660306
                                            }
                                        ],
                                        "sub_hero_last": [
                                            {
                                                "hero_appearance_rate": 0.002212,
                                                "hero_index": 1,
                                                "hero_win_rate": 0.473875,
                                                "heroid": 84,
                                                "increase_win_rate": -0.147216,
                                                "min_win_rate10_12": 0.116807,
                                                "min_win_rate12_14": 0.191547,
                                                "min_win_rate14_16": 0.253222,
                                                "min_win_rate16_18": 0.357298,
                                                "min_win_rate18_20": 0.410104,
                                                "min_win_rate20": 0.488372,
                                                "min_win_rate6": 0.312,
                                                "min_win_rate6_8": 0.137931,
                                                "min_win_rate8_10": 0.092857
                                            }
                                        ]
                                    },
                                    "id": 102827,
                                    "sourceId": 2755183
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
def heroes_stats(
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
        "pageIndex": index,
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
                "value": 1
            }
        ],
        "sorts": [],
    }
    return fetch_academy_post("2755183", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/lane",
    name="api.academy.heroes_lane",
    response_model=AcademyCollectionResponse,
    summary="Hero Lane Distribution",
    description=(
        "Retrieve lane distribution information for a specific hero. "
        "Supports query parameters for pagination and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero lane distribution data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **data**:\n"
        "        - **hero_id**: Unique hero identifier.\n"
        "        - **hero**:\n"
        "            - **data**:\n"
        "                - **roadsort**: Array of lane assignments, each containing:\n"
        "                    - **_id**: Unique record identifier.\n"
        "                    - **caption**: Localized lane caption (e.g., '打野').\n"
        "                    - **configId**: Configuration ID.\n"
        "                    - **createdAt**: Creation timestamp.\n"
        "                    - **createdUser**: Creator username.\n"
        "                    - **updatedAt**: Last update timestamp.\n"
        "                    - **updatedUser**: Last updater username.\n"
        "                    - **data**:\n"
        "                        - **road_sort_id**: Lane ID (e.g., '4').\n"
        "                        - **road_sort_title**: Lane title (e.g., 'Jungle').\n"
        "                        - **road_sort_icon**: Lane icon URL.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing hero lane preferences.\n"
        "- Understanding optimal lane assignments.\n"
        "- Guiding players in hero positioning strategies."
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
                                                "roadsort": [
                                                    {
                                                        "_id": "668541caaa8e7f6ec4703d8a",
                                                        "caption": "打野",
                                                        "configId": 144237,
                                                        "createdAt": 1720009162509,
                                                        "createdUser": "nickjin",
                                                        "data": {
                                                            "_object": 2732073,
                                                            "road_sort_icon": "https://akmweb.youngjoygame.com/web/gms/image/de611167c7310681135f0b4198137bfa.svg",
                                                            "road_sort_id": "4",
                                                            "road_sort_title": "Jungle"
                                                        },
                                                        "dynamic": None,
                                                        "id": 2732080,
                                                        "linkId": [2732073],
                                                        "sort": 0,
                                                        "updatedAt": 1723022951463,
                                                        "updatedUser": "nickjin"
                                                    },
                                                    ""
                                                ]
                                            }
                                        },
                                        "hero_id": 17
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
def heroes_lane(
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
        "pageIndex": index,
        "filters": [
            {
                "field": "hero_id",
                "operator": "eq",
                "value": hero_id
            }
        ],
        "sorts": [],
        "fields": ["hero_id", "hero.data.roadsort"],
        "object": [],
    }
    return fetch_academy_post("2766683", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/win-rate/timeline",
    name="api.academy.heroes_time_win_rate",
    response_model=AcademyCollectionResponse,
    summary="Hero Lane Time-based Win Rate",
    description=(
        "Retrieve time-based win rate statistics for a specific hero in a given lane. "
        "Supports query parameters for rank, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **lane**: Lane. Allowed values: `exp`, `mid`, `roam`, `jungle`, `gold`. from `/api/academy/heroes/{hero_identifier}/lane` \n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero lane time-based win rate data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **heroid**: Hero ID.\n"
        "        - **hero_name**: Hero name.\n"
        "        - **real_road**: Lane ID (e.g., 4 for Jungle).\n"
        "        - **total_win_rate**: Overall win rate for the hero in this lane.\n"
        "        - **time_win_rate**: Array of segmented win rates by match duration:\n"
        "            - **time_min**: Minimum time interval (minutes).\n"
        "            - **time_max**: Maximum time interval (minutes).\n"
        "            - **win_rate**: Win rate within that time range.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing hero performance progression over match duration.\n"
        "- Understanding lane-specific strengths.\n"
        "- Guiding players in timing strategies for optimal hero usage."
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
                                    "_createdAt": 1774890905268,
                                    "_id": "69caaf9b54ae2bda46ed0aeb",
                                    "_updatedAt": 1774890905268,
                                    "data": {
                                        "big_rank": "101",
                                        "hero_name": "梵妮",
                                        "heroid": 17,
                                        "real_road": 1,
                                        "time_win_rate": [
                                            {
                                                "time_max": 12,
                                                "time_min": 10,
                                                "win_rate": 0.3304550611370226
                                            }
                                        ],
                                        "total_win_rate": 0.4135894042088245
                                    },
                                    "id": 4234813,
                                    "sourceId": 2777027
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
def heroes_time_win_rate(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`. "
                "Name matching ignores spaces/symbols and is case-insensitive (e.g., `Luo Yi` to `luoyi`)."
            ),
        )
    ],
    lane: Annotated[
        HeroLaneEnum,
        Query(
            title="Lane",
            description="Filter heroes by lane `/api/academy/heroes/{hero_identifier}/lane`.",
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
    lane_value = validate_and_single([lane], LANE_MAP, "lane")
    
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [
            {
                "field": "heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "big_rank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            },
            {
                "field": "real_road",
                "operator": "eq",
                "value": lane_value
            },
        ],
        "sorts": [],
    }
    return fetch_academy_post("2777027", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/builds",
    name="api.academy.heroes_builds",
    response_model=AcademyCollectionResponse,
    summary="Hero Recommended Builds",
    description=(
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **lane**: Lane. Allowed values: `exp`, `mid`, `roam`, `jungle`, `gold`. from `/api/academy/heroes/{hero_identifier}/lane` \n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero build data:\n"
        "- **records**: Array of build entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **heroid**: Hero ID.\n"
        "        - **hero_name**: Hero name.\n"
        "        - **real_road**: Lane assignment ID.\n"
        "        - **build**: Array of recommended builds, each containing:\n"
        "            - **equipid**: List of equipment IDs.\n"
        "            - **emblem**: Emblem configuration:\n"
        "                - **emblemid**: Emblem ID.\n"
        "                - **emblemname**: Emblem name.\n"
        "                - **emblemattr**: Emblem attributes (e.g., '+10% Spell Vamp').\n"
        "                - **attriicon**: Emblem attribute icon URL.\n"
        "            - **battleskill**: Battle spell configuration:\n"
        "                - **battleskillid**: Battle spell ID.\n"
        "                - **skillname**: Spell name (e.g., 'Retribution').\n"
        "                - **skillshortdesc**: Short description.\n"
        "                - **skilldesc**: Full description of spell effects.\n"
        "                - **skillicon**: Spell icon URL.\n"
        "            - **runeid**: Rune ID.\n"
        "            - **new_rune_skill**: Array of rune skill IDs.\n"
        "            - **build_pick_rate**: Pick rate of the build.\n"
        "            - **build_win_rate**: Win rate of the build.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying historical or community-recommended builds.\n"
        "- Providing backward compatibility for older integrations.\n"
        "- Should be replaced with newer endpoints for up-to-date build recommendations."
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
                                    "_createdAt": 1774899901345,
                                    "_id": "69cad2be54ae2bda46ed4019",
                                    "_updatedAt": 1774899901345,
                                    "data": {
                                        "big_rank": "9",
                                        "build": [
                                            {
                                                "battleskill": {
                                                    "data": {
                                                        "__data": {
                                                            "skilldesc": "Deal 520 (+80*Hero Level) <font color=\"ffe63c\">True Damage</font> to the target Creep or Minion.\n<font color=\"62f8fe\">Passive</font>: Increases Creep rewards by 60% and reduces damage taken from basic Creeps by 40%. Also grants 15% additional Damage Reduction in the allied jungle during the first 2 min. Cannot share Minion rewards with allied heroes in the first 5 min.\n<font color=\"62f8fe\">Blessing:</font> Accumulate 5 Creep kills, hero kills, or assists to upgrade the spell according to the Jungling Boots' Blessing, and <Num9> kills or assists to gain <Num10> Physical Attack and Magic Power and <Num11> Max HP.",
                                                            "skilldescemblem": "Deal 520 (+80*Hero Level) <font color=\"ffe63c\">True Damage</font> to the target Creep or Minion.\n<font color=\"62f8fe\">Passive</font>: Increases Creep rewards by 60% and reduces damage taken from basic Creeps by 40%. Also grants 15% additional Damage Reduction in the allied jungle during the first 2 min. Cannot share Minion rewards with allied heroes in the first 5 min.\n<font color=\"62f8fe\">Blessing:</font> Accumulate 5 Creep kills, hero kills, or assists to upgrade the spell according to the Jungling Boots' Blessing, and <Num9> kills or assists to gain <Num10> Physical Attack and Magic Power and <Num11> Max HP.",
                                                            "skillicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_2cd084a2661c121c347facb060a80377.png",
                                                            "skillid": 20020,
                                                            "skillname": "Retribution"
                                                        },
                                                        "battleskillid": 20020,
                                                        "skillshortdesc": "Jungle Special"
                                                    }
                                                },
                                                "build_pick_rate": 0.0128607932777792,
                                                "build_win_rate": 0.6308437856328392,
                                                "emblem": {
                                                    "data": {
                                                        "attriicon": "https://akmweb.youngjoygame.com/web/svnres/img/mlbb/homepage/100_ae89ce5b37dcd804686133c8d7044430.png",
                                                        "emblemattr": {
                                                            "emblemattr": "+14 Adaptive Penetration\n+10 Adaptive Attack\n+3% Movement Speed\n",
                                                            "emblemattrid": "2000560",
                                                            "emblemname": "Assassin"
                                                        },
                                                        "emblemid": 20005,
                                                        "emblemname": "Assassin"
                                                    }
                                                },
                                                "equipid": [3007, 3001, 2013],
                                                "new_rune_skill": [112, 122, 631],
                                                "runeid": 20005,
                                                "skillid": 20020
                                            }
                                        ],
                                        "hero_name": "梵妮",
                                        "heroid": 17,
                                        "real_road": 4
                                    },
                                    "id": 4236127,
                                    "sourceId": 2776688
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
def heroes_builds(
    hero_identifier: Annotated[
        str,
        Path(
            title="Hero Identifier",
            description=(
                "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`."
            ),
        )
    ],
    lane: Annotated[
        HeroLaneEnum,
        Query(
            title="Lane",
            description="Filter heroes by lane (`/api/academy/heroes/{hero_identifier}/lane`).",
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
    lane_value = validate_and_single([lane], LANE_MAP, "lane")
    payload = {
        "pageSize": size,
        "pageIndex": index,
        "filters": [
            {
                "field": "heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "real_road",
                "operator": "eq",
                "value": lane_value
            },
            {
                "field": "big_rank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            }
        ],
        "sorts": [],
    }
    return fetch_academy_post("2776688", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/counters",
    name="api.academy.heroes_counters",
    response_model=AcademyCollectionResponse,
    summary="Hero Counters",
    description=(
        "Retrieve counter information for a specific hero. "
        "Supports query parameters for rank, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
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
        "        - **main_heroid**: Target hero ID.\n"
        "        - **main_hero_ban_rate**: Ban rate of the target hero.\n"
        "        - **main_hero_pick_rate**: Pick rate of the target hero.\n"
        "        - **main_hero_win_rate**: Win rate of the target hero.\n"
        "        - **sub_hero**: Array of counter heroes, each containing:\n"
        "            - **heroid**: Counter hero ID.\n"
        "            - **hero_win_rate**: Win rate of the counter hero.\n"
        "            - **increase_win_rate**: Impact value showing how much this hero improves or reduces win rate against the target.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing which heroes perform well against the target hero.\n"
        "- Understanding matchup dynamics.\n"
        "- Guiding players in drafting strategies."
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
                                    "_createdAt": 1774899901719,
                                    "_id": "69cad2be54ae2bda46ed3d55",
                                    "_updatedAt": 1774899901719,
                                    "data": {
                                        "big_rank": "9",
                                        "camp_type": "0",
                                        "main_hero_ban_rate": 0.08109399676322937,
                                        "main_hero_pick_rate": 0.010181000456213951,
                                        "main_hero_win_rate": 0.4657759964466095,
                                        "main_heroid": 17,
                                        "sub_hero": [
                                            {
                                                "hero_win_rate": 0.428453,
                                                "heroid": 39,
                                                "increase_win_rate": -0.011633
                                            }
                                        ]
                                    },
                                    "id": 1756034,
                                    "sourceId": 2777391
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
def heroes_counters(
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
        "pageIndex": index,
        "filters": [
            {
                "field": "main_heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "camp_type",
                "operator": "eq",
                "value": 0
            },
            {
                "field": "big_rank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            }
        ],
        "sorts": [],
    }
    return fetch_academy_post("2777391", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/teammates",
    name="api.academy.heroes_teammates",
    response_model=AcademyCollectionResponse,
    summary="Hero Teammates",
    description=(
        "Retrieve teammate information for a specific hero. "
        "Supports query parameters for rank, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero teammate data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_heroid**: Target hero ID.\n"
        "        - **main_hero_ban_rate**: Ban rate of the target hero.\n"
        "        - **main_hero_pick_rate**: Pick rate of the target hero.\n"
        "        - **main_hero_win_rate**: Win rate of the target hero.\n"
        "        - **sub_hero**: Array of teammate heroes, each containing:\n"
        "            - **heroid**: Teammate hero ID.\n"
        "            - **hero_win_rate**: Win rate of the teammate hero.\n"
        "            - **increase_win_rate**: Impact value showing how much this hero improves or reduces win rate when paired with the target.\n\n"
        "This endpoint is useful for:\n"
        "- Analyzing which heroes synergize well with the target hero.\n"
        "- Understanding team composition dynamics.\n"
        "- Guiding players in drafting strategies."
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
                                    "_createdAt": 1774899901719,
                                    "_id": "69cad2be54ae2bda46ed3ce7",
                                    "_updatedAt": 1774899901719,
                                    "data": {
                                        "big_rank": "9",
                                        "camp_type": "1",
                                        "main_hero_ban_rate": 0.08109399676322937,
                                        "main_hero_pick_rate": 0.010181000456213951,
                                        "main_hero_win_rate": 0.4657759964466095,
                                        "main_heroid": 17,
                                        "sub_hero": [
                                            {
                                                "hero_win_rate": 0.442802,
                                                "heroid": 69,
                                                "increase_win_rate": -0.114625
                                            }
                                        ]
                                    },
                                    "id": 1755924,
                                    "sourceId": 2777391
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
def heroes_teammates(
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
        "pageIndex": index,
        "filters": [
            {
                "field": "main_heroid",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "camp_type",
                "operator": "eq",
                "value": "1"
            },
            {
                "field": "big_rank",
                "operator": "eq",
                "value": validate_and_map_rank(rank)
            }
        ],
        "sorts": [],
    }
    return fetch_academy_post("2777391", payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/trends",
    name="api.academy.heroes_trends",
    response_model=AcademyCollectionResponse,
    summary="Hero Performance Trends",
    description=(
        "Retrieve trend information for a specific hero over a selected time window. "
        "Supports query parameters for days, rank, pagination, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **days**: Trend window in days. Allowed values: `7`, `15`, `30`.\n"
        "- **rank**: Rank filter. Allowed values: `all`, `epic`, `legend`, `mythic`, `honor`, `glory`.\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero performance trend data:\n"
        "- **records**: Array of hero entries, each containing:\n"
        "    - **_id**: Unique record identifier.\n"
        "    - **_createdAt**: Creation timestamp.\n"
        "    - **_updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **main_heroid**: Hero ID.\n"
        "        - **bigrank**: Rank context ID.\n"
        "        - **camp_type**: Camp type indicator.\n"
        "        - **match_type**: Match type indicator.\n"
        "        - **win_rate**: Array of daily statistics, each containing:\n"
        "            - **date**: Date of record.\n"
        "            - **app_rate**: Appearance rate.\n"
        "            - **ban_rate**: Ban rate.\n"
        "            - **win_rate**: Win rate.\n\n"
        "This endpoint is useful for:\n"
        "- Tracking hero performance changes over time.\n"
        "- Identifying meta shifts across ranks.\n"
        "- Guiding players in understanding how a hero’s effectiveness evolves across different ranks and timeframes."
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
                                    "_createdAt": 1725607498066,
                                    "_id": "66daae4b2bc97a5ed5c98d29",
                                    "_updatedAt": 1774965307654,
                                    "data": {
                                        "bigrank": "9",
                                        "camp_type": "1",
                                        "main_heroid": 17,
                                        "match_type": "1",
                                        "win_rate": [
                                            {
                                                "app_rate": 0.00919,
                                                "ban_rate": 0.058604,
                                                "date": "2026-03-30",
                                                "win_rate": 0.450255
                                            }
                                        ]
                                    },
                                    "id": 104186,
                                    "sourceId": 2755185
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
def heroes_trends(
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
        Literal["7", "15", "30"],
        Query(
            title="Trend Window (Days)",
            description=(
                "Time window for trend data in days."
            ),

        ),
    ] = "7",
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
    day_map = {
        "7": "2755185",
        "15": "2755186",
        "30": "2755187"
    }
    payload = {
        "pageSize": size,
        "pageIndex": index,
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
                "value": 1
            }
        ],
        "sorts": [],
    }
    return fetch_academy_post(day_map.get(days, "2755185"), payload, lang)


@router.get(
    path="/heroes/{hero_identifier}/recommended",
    name="api.academy.heroes_recommended",
    response_model=AcademyCollectionResponse,
    summary="Hero Recommended Content",
    description=(
        "Retrieve recommended content for a specific hero. "
        "Supports query parameters for pagination, sorting, and localization.\n\n"
        "Path parameters:\n"
        "- **hero_identifier**: Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`.\n\n"
        "Query parameters:\n"
        "- **size**: Number of items per page (minimum: 1).\n"
        "- **index**: Page index (starting from 1).\n"
        "- **order**: Sort order for recommendation hotness or creation time. Allowed values: `asc`, `desc`.\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero recommended content data:\n"
        "- **records**: Array of recommended entries, each containing:\n"
        "    - **createdAt**: Creation timestamp.\n"
        "    - **updatedAt**: Last update timestamp.\n"
        "    - **data**:\n"
        "        - **channels**: Content channels (e.g., 'UGC', 'recommend').\n"
        "        - **type**: Content type (e.g., 'ugc_hero').\n"
        "        - **state**: Content state (e.g., 'release').\n"
        "        - **data**:\n"
        "            - **hero**: Hero metadata including:\n"
        "                - **hero_id**: Hero ID.\n"
        "                - **hero_lane**: Lane assignment.\n"
        "                - **hero_tags**: Array of tag IDs.\n"
        "            - **equips**: Recommended equipment builds with IDs and descriptions.\n"
        "            - **emblems**: Recommended emblem sets with IDs and descriptions.\n"
        "            - **spell**: Recommended battle spell with ID and description.\n"
        "            - **cooperates**: Cooperative hero synergies with descriptions and rates.\n"
        "            - **counters**: Counter heroes with descriptions and rates.\n"
        "            - **dominants**: Dominant strategies or tips.\n"
        "            - **recommend**: General recommendation notes.\n"
        "            - **snapshot**: Snapshot image URL.\n"
        "            - **game_version**: Version reference.\n"
        "            - **language**: Content language.\n"
        "            - **pages**: Content sections (e.g., 'hero', 'spell', 'equip').\n"
        "            - **title**: Guide or build title.\n"
        "        - **user**: Author metadata including:\n"
        "            - **name**: Author name.\n"
        "            - **avatar**: Author avatar URL.\n"
        "            - **level**: Author level.\n"
        "            - **roleId**: Role ID.\n"
        "            - **zoneId**: Zone ID.\n"
        "        - **dynamic**: Engagement metrics:\n"
        "            - **views**: Total views.\n"
        "            - **hot**: Hotness score.\n"
        "            - **votes**: Total votes.\n"
        "            - **views_by_4h_total_24h**: Views in last 24h.\n"
        "        - **vote_all**: Voting metadata:\n"
        "            - **target**: Target content ID.\n"
        "            - **vote**: Vote ID reference.\n\n"
        "This endpoint is useful for:\n"
        "- Surfacing curated or community-recommended hero guides.\n"
        "- Providing builds, emblems, and strategies tailored to a hero.\n"
        "- Highlighting cooperative and counter hero recommendations.\n"
        "- Guiding players with contextual tips and shared experiences."
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
                                    "createdAt": 1774934989925,
                                    "data": {
                                        "channels": ["UGC", "recommend"],
                                        "data": {
                                            "cooperates": [
                                                {
                                                    "cooperate_desc": "Tigreal's ulti helps a lot to finished up squishy hero like mm or mage.",
                                                    "cooperate_hero_id": 6,
                                                    "cooperate_rate": 80
                                                }
                                            ],
                                            "counters": [
                                                {
                                                    "counter_desc": "One shot saber is very dangerous for late game fanny",
                                                    "counter_hero_id": 3,
                                                    "counter_rate": 60
                                                }
                                            ],
                                            "data_version": 1,
                                            "dominants": [
                                                {
                                                    "dominant_desc": "practice using her steel cables efficiently by aiming at walls to move faster and avoid wasting energy. Always secure the blue buff early, as Fanny depends heavily on energy to keep attacking and moving. Focus on targeting low-health backline heroes like marksmen and mages, and avoid engaging when enemy crowd control skills are available. Use quick in-and-out combos to finish enemies and escape safely, and constantly watch the map to plan your movement paths. With proper timing, energy management, and positioning, Fanny can dominate the game as a deadly finisher.",
                                                    "dominant_title": "Cable mastery"
                                                }
                                            ],
                                            "emblems": [
                                                {
                                                    "emblem_desc": "Fanny benefits greatly from a custom Assassin Emblem setup with Rapture, Seasoned Hunter, and Lethal Ignition in Mobile Legends: Bang Bang because it maximizes her jungle efficiency and burst potential. Rapture provides additional physical penetration, allowing Fanny to deal higher damage even against slightly tanky targets. Seasoned Hunter boosts her damage to jungle monsters and objectives like Turtle and Lord, helping her farm faster and secure objectives more reliably—crucial for maintaining energy through blue buff. Meanwhile, Lethal Ignition adds an extra burst of damage after consecutive hits, perfectly complementing her cable combo playstyle to quickly finish off enemies. This setup makes her more effective in both early-game farming and late-game assassinations.",
                                                    "emblem_gifts": [511, 122, 631],
                                                    "emblem_id": 20005,
                                                    "emblem_title": "Farming and Damage"
                                                }
                                            ],
                                            "equips": [
                                                {
                                                    "equip_desc": "This build is very effective for finished off the low hp heros like marksman and mages. Its one shot at middle of the game.",
                                                    "equip_ids": [3007, 3522, 2014, 3001, 3012, 3008],
                                                    "equip_title": "Brust - one shot"
                                                }
                                            ],
                                            "game_version": "2.1.18",
                                            "hero": {
                                                "hero_id": 17,
                                                "hero_lane": "4",
                                                "hero_overview": "Fanny is a high-skill Assassin in Mobile Legends: Bang Bang, known for her incredible mobility using steel cables that let her fly across the battlefield. Once a determined soldier from the Moniyan Empire who trained relentlessly to protect her homeland, Fanny developed her unique combat style to strike enemies with unmatched speed and precision. As a jungler, she excels at fast farming routes—typically starting from the blue buff to sustain her energy, then quickly clearing nearby camps and rotating to secure kills or objectives.\nWith an aggressive, high-risk gameplay style, Fanny thrives as a finisher who dives into the backline to eliminate low-health enemies instantly. Her burst damage combined with precise cable control allows skilled players to snowball early and dominate the map. However, mastering her energy management and execution is crucial, as a single mistake can leave her vulnerable to crowd control and quick elimination.",
                                                "hero_strength": "Fanny excels as one of the most mobile and explosive assassins in Mobile Legends: Bang Bang, with the ability to traverse the map at incredible speed using her steel cables. Her greatest strength lies in her high burst damage, allowing her to quickly eliminate squishy backline targets like marksmen and mages. Fanny also has exceptional snowball potential, meaning a strong early game can let her dominate the entire match. In skilled hands, she becomes extremely hard to catch or counter, making her a constant threat who can engage and disengage fights effortlessly.",
                                                "hero_tags": [4, 2, 7],
                                                "hero_weakness": "Fanny has several significant weaknesses in Mobile Legends: Bang Bang, mainly due to her high skill dependency and energy limitations. She relies heavily on precise cable control and proper energy management, meaning even a small mistake can leave her unable to escape or deal damage. Fanny is also extremely vulnerable to crowd control effects like stun or suppression, which can instantly shut her down. Additionally, she struggles if she falls behind early, as she depends on snowballing to stay effective, making her a risky pick for inexperienced players."
                                            },
                                            "language": "en",
                                            "pages": ["hero", "spell", "emblem", "equip", "dominant", "cooperate"],
                                            "recommend": "It's only for damage build jungler fanny role.",
                                            "snapshot": "https://akmweb.youngjoygame.com/web/academy/image/2f2418601c0e1999393b45c90087991b.jpeg",
                                            "spell": {
                                                "spell_desc": "Fanny requires Retribution as a jungler in Mobile Legends: Bang Bang because it significantly boosts her farming speed and overall efficiency in the early game. Since Fanny depends heavily on securing the blue buff to maintain her energy for continuous cable usage, Retribution helps her clear jungle camps faster and safely secure objectives like buffs, Turtle, and Lord. This spell also enhances her ability to snowball by allowing quicker rotations and level advantage, which is crucial for her aggressive playstyle as a finisher. Without Retribution, her jungle clear becomes slower and less reliable, making it harder for her to dominate the map.",
                                                "spell_id": 20020
                                            },
                                            "title": "Aggressive Fanny game style"
                                        },
                                        "state": "release",
                                        "type": "ugc_hero"
                                    },
                                    "dynamic": {
                                        "hot": 174.92,
                                        "views": 1,
                                        "views_by_4h_1": 1,
                                        "views_by_4h_total_24h": 1
                                    },
                                    "form": {
                                        "id": 2737553
                                    },
                                    "id": 1097234759066688,
                                    "uin": "mlbb:2534:102531841",
                                    "updatedAt": 1774936017556,
                                    "user": {
                                        "avatar": "https://akmpicture.youngjoygame.com/dist/face/2534/41/18/31_new_37cc2e29-a6ff-43c5-a0ec-f126a7a5c96a.jpg",
                                        "historyRankLevel": 209,
                                        "level": 123,
                                        "module": "mlbb",
                                        "name": "Ɖѻñäs",
                                        "roleId": 102531841,
                                        "zoneId": 2534
                                    },
                                    "vote_all": {
                                        "target": "1097234759066688",
                                        "vote": {
                                            "id": 2758890
                                        }
                                    }
                                }
                            ],
                            "total": 359
                        }
                    }
                }
            }
        }
    }
)
def heroes_recommended(
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
    order: Annotated[
        SortOrderEnum,
        Query(
            title="Sort Order",
            description="Sort order for recommendation hotness and creation time.",
        ),
    ] = SortOrderEnum.DESCENDING,
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
        "pageIndex": index,
        "filters": [
            {
                "field": "formId",
                "operator": "eq",
                "value": 2737553
            },
            {
                "field": "data.state",
                "operator": "eq",
                "value": "release"
            },
            {
                "field": "data.data.hero.hero_id",
                "operator": "eq",
                "value": hero_id
            },
            {
                "field": "data.data.language",
                "operator": "eq",
                "value": lang
            },
        ],
        "sorts": [
            {
                "data":
                    {
                        "field": "data.sort",
                        "order": order
                    },
                "type": "sequence"
            },
            {
                "data":
                    {
                        "field": "createdAt",
                        "order": order
                    },
                "type": "sequence"
            }
        ],
        "type": "form.item.all",
        "object": [2675413],
    }
    return fetch_academy_post("2718124", payload, lang)


@router.get(
    path="/heroes/ratings",
    name="api.academy.heroes_ratings",
    response_model=AcademyRatingsResponse,
    summary="Hero Ratings Index",
    description=(
        "Retrieve a list of all hero ratings and community polls. "
        "Supports query parameter for localization.\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero ratings data:\n"
        "- **list**: Array of rating subjects, each containing:\n"
        "    - **subject**: Poll subject ID.\n"
        "    - **title**: Poll title (e.g., 'Vote for MLBB's Charismatic Queens!').\n"
        "    - **desc**: Poll description.\n"
        "    - **comment_count**: Number of comments.\n"
        "    - **ranking**: Array of ranked hero entries, each containing:\n"
        "        - **object**: Hero object ID.\n"
        "        - **title**: Hero name.\n"
        "        - **image**: Hero image URL.\n"
        "        - **image_big**: Larger hero image URL.\n"
        "        - **channel**: Array of channel IDs.\n"
        "        - **score**: Hero score value (e.g., '9.1').\n"
        "        - **score_total**: Total score points accumulated.\n"
        "        - **score_count**: Number of votes.\n"
        "        - **hot_comment**: Highlighted comment.\n"
        "        - **hashtags**: Optional hashtags associated with the poll.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying community-driven hero ratings.\n"
        "- Tracking popularity trends.\n"
        "- Surfacing thematic polls such as 'Most Charismatic Hero' or 'Top Jungler'."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "5eddcf24147754aadd27438d7634f630",
                        "data": {
                            "total": 12,
                            "list": [
                                {
                                    "subject": 3275335,
                                    "title": "Vote for MLBB's Charismatic Queens! Which female hero in the Land of Dawn has the most mature charm?",
                                    "desc": "They are battlefield leaders with commanding presence; mysterious, mature sages; and pillars of strength hiding their edge behind gentleness. With their unshakeable aura and mature elegance, these female heroes command attention the moment they enter the fray. Which MLBB female hero best embodies both mature charm and strength for you? Vote now to crown the Land of Dawn's ultimate Queen of Charisma!",
                                    "comment_count": 890,
                                    "ranking": [
                                        {
                                            "object": "3209965",
                                            "title": "Zetian",
                                            "image": "https://akmweb.youngjoygame.com/web/gms/image/20a263b2adb23ad40cd955b9abf4bbb0.jpg",
                                            "image_big": "https://akmweb.youngjoygame.com/web/gms/image/b617a6b4d9e2c22a5bc24d886e453399.jpg",
                                            "channel": [3168724, 3168728],
                                            "score": "9.2",
                                            "score_total": 2398,
                                            "score_count": 262,
                                            "hot_comment": "Gugu"
                                        }
                                    ]
                                }
                            ],
                            "has_more": True
                        }
                    }
                }
            }
        }
    }
)
def heroes_ratings(
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    return fetch_ratings_all(lang)


@router.get(
    path="/heroes/ratings/{subject}",
    name="api.academy.heroes_ratings_subject",
    response_model=AcademyRatingsResponse,
    summary="Hero Ratings by Subject",
    description=(
        "Retrieve hero ratings for a specific subject from the ratings index. "
        "Supports query parameter for localization.\n\n"
        "Path parameters:\n"
        "- **subject**: Rating subject key from the ratings index response (7 characters).\n\n"
        "Query parameters:\n"
        "- **lang**: Language code for localized content (default: `en`).\n\n"
        "The response includes hero rating data for the chosen subject:\n"
        "- **list**: Array of hero entries, each containing:\n"
        "    - **object**: Hero object ID.\n"
        "    - **title**: Hero name (e.g., 'Fanny').\n"
        "    - **image**: Hero image URL.\n"
        "    - **image_big**: Larger hero image URL.\n"
        "    - **channel**: Array of channel IDs.\n"
        "    - **score**: Hero score value (e.g., '8.8').\n"
        "    - **score_total**: Total score points accumulated.\n"
        "    - **score_count**: Number of votes.\n"
        "    - **hot_comment**: Highlighted community comment.\n"
        "    - **hashtags**: Optional hashtags associated with the poll.\n\n"
        "This endpoint is useful for:\n"
        "- Displaying detailed ratings within a chosen poll or theme.\n"
        "- Allowing players to explore community sentiment.\n"
        "- Surfacing popularity for heroes in specific categories (e.g., 'Top Jungler', 'Most Charismatic Hero')."
    ),
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "Success",
                        "traceID": "69cf858d38125ea8f27eef33d6330a9d",
                        "data": {
                            "total": 20,
                            "list": [
                                {
                                    "object": "3209965",
                                    "title": "Zetian",
                                    "image": "https://akmweb.youngjoygame.com/web/gms/image/20a263b2adb23ad40cd955b9abf4bbb0.jpg",
                                    "image_big": "https://akmweb.youngjoygame.com/web/gms/image/b617a6b4d9e2c22a5bc24d886e453399.jpg",
                                    "channel": [3168724, 3168728],
                                    "score": "9.2",
                                    "score_total": 2398,
                                    "score_count": 262,
                                    "hot_comment": "Gugu"
                                }
                            ],
                            "subject": {
                                "id": "3275335",
                                "title": "Vote for MLBB's Charismatic Queens! Which female hero in the Land of Dawn has the most mature charm?",
                                "desc": "They are battlefield leaders with commanding presence; mysterious, mature sages; and pillars of strength hiding their edge behind gentleness. With their unshakeable aura and mature elegance, these female heroes command attention the moment they enter the fray. Which MLBB female hero best embodies both mature charm and strength for you? Vote now to crown the Land of Dawn's ultimate Queen of Charisma!"
                            }
                        }
                    }
                }
            }
        }
    }
)
def heroes_ratings_subject(
    subject: Annotated[
        str,
        Path(
            title="Rating Subject",
            description="Rating subject ID from the ratings index response.",
            min_length=7,
            max_length=7,
        )
    ],
    lang: Annotated[
        LanguageEnum,
        Query(
            title="Language",
            description="Language code for localized content.",
        )
    ] = LanguageEnum.ENGLISH
) -> object:
    return fetch_ratings_subject(lang, subject)
