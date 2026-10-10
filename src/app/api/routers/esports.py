from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.dependencies import require_api_available
from app.api.params import LeagueLang
from app.core.enums import LeagueLanguageEnum
from app.schemas.esports import MatchDetailResponse, ScheduleResponse, StandingsResponse
from app.services.esports import indonesia, philippines
from app.services.esports.common import select_weeks
from app.utils.client_ip import bind_client_ip

router = APIRouter(
    prefix="/api/esports",
    tags=["esports"],
    dependencies=[Depends(require_api_available), Depends(bind_client_ip)],
)

Week = Annotated[
    int | None,
    Query(
        title="Week",
        description="Regular-season week to return. Omit it to get every week. The number of weeks varies by season.",
        ge=1,
    ),
]

_LOGO = "https://example.com/teams/evos.png"
_HERO_IMAGE = "https://mlbb-image.scoregg.com/hero_h/85.png"
_ASSET = {"id": "20003", "image": "https://mlbb-image.scoregg.com/emblem/20003.png"}

_SCHEDULE_EXAMPLE = {
    "weeks": [
        {
            "week": 1,
            "days": [
                {
                    "day": 1,
                    "label": "Friday, 14 August 2026",
                    "matches": [
                        {
                            "match_id": "1036",
                            "start_at": "2026-08-14T08:00:00+00:00",
                            "local_time": "15:00",
                            "team1": {"name": "EVOS", "full_name": None, "logo": _LOGO},
                            "team2": {"name": "RRQ", "full_name": None, "logo": _LOGO},
                            "score1": 2,
                            "score2": 0,
                            "replay_url": None,
                        }
                    ],
                }
            ],
        }
    ]
}

_STANDINGS_EXAMPLE = {
    "standings": [
        {
            "rank": 1,
            "team": {"name": "NAVI", "full_name": "NAVI", "logo": _LOGO},
            "match_point": 11,
            "match_wl": {"win": 11, "lose": 3},
            "net_game_win": 14,
            "game_wl": {"win": 23, "lose": 9},
        }
    ]
}

_PLAYER_EXAMPLE = {
    "name": "Rendyyy",
    "hero": {"name": "Dyrroth", "image": _HERO_IMAGE},
    "kills": 3,
    "deaths": 2,
    "assists": 3,
    "kda": 3.0,
    "items": [{"id": "3212", "image": "https://mlbb-image.scoregg.com/m/33/p/2511/0617014872193.png"}],
    "emblem": _ASSET,
    "talents": [{"id": "811", "image": "https://mlbb-image.scoregg.com/rune/811.png"}],
    "gold": 9316,
    "damage_dealt": 38859,
    "damage_taken": 126389,
    "tower_damage": 1699,
    "item_sequence": [],
}


def _match_example(match_id: str, duration: str | None, stats: dict[str, int], sequence: list[dict]) -> dict:
    return {
        "match_id": match_id,
        "games": [
            {
                "number": 1,
                "duration": duration,
                "timeline_minutes": [0, 2, 4] if sequence else [],
                "teams": [
                    {
                        "team": {"name": "EVOS", "full_name": None, "logo": _LOGO},
                        "winner": True if duration else None,
                        "kills": 11,
                        "stats": stats,
                        "players": [{**_PLAYER_EXAMPLE, "item_sequence": sequence}],
                    }
                ],
            }
        ],
    }


_ID_MATCH_EXAMPLE = _match_example("1036", "16:51", {}, [])
_PH_MATCH_EXAMPLE = _match_example(
    "rora-onic-20260821",
    None,
    {"total_gold": 34946, "total_damage": 82500, "red_buff": 4, "lord_kill": 0},
    [{"id": "1411", "image": "https://mlbb-image.scoregg.com/equip/1411.png", "tier": 1, "timeline_percent": 0.56}],
)


def _example(payload: dict) -> dict:
    return {200: {"description": "Successful Response", "content": {"application/json": {"example": payload}}}}


_LANG_PARAM = "- **lang**: Language of the site's text, such as day names: `en` (default) or `id`.\n"
_SCHEDULE_DESCRIPTION = (
    "Regular-season schedule of {league}, grouped by week and day.\n\n"
    "Query parameters:\n"
    "- **week**: Optional week number. Omit it to get every week; an unknown week returns 404.\n{lang_param}\n"
    "Each match has:\n"
    "- **match_id**: Value for the matches endpoint; null while no details page exists.\n"
    "- **start_at**: Start time in UTC (ISO 8601). **local_time** is the time as shown on the site.\n"
    "- **team1** / **team2** with logo, and **score1** / **score2** (null until played).\n\n"
    "Data is read from the league's public site and cached for 5 minutes."
)
_STANDINGS_DESCRIPTION = (
    "Regular-season standings of {league}: rank, team, match point, match win-lose, "
    "net game win and game win-lose.\n{lang_param}\nData is read from the league's public site and cached for 5 minutes."
)
_MATCH_DESCRIPTION = (
    "Full match history of one match of {league}: every game with both teams and all players "
    "(hero, KDA, items, emblem, talents, gold, damage dealt, damage taken and tower damage).{extra}\n\n"
    "Battle spells are not published by the league site. Data is cached for 5 minutes."
)


@router.get(
    path="/id/schedule",
    name="api.esports.id_schedule",
    response_model=ScheduleResponse,
    summary="Indonesia Regular Season Schedule",
    description=_SCHEDULE_DESCRIPTION.format(league="the Indonesian professional league", lang_param=_LANG_PARAM),
    responses=_example(_SCHEDULE_EXAMPLE),
)
def id_schedule(week: Week = None, lang: LeagueLang = LeagueLanguageEnum.ENGLISH) -> ScheduleResponse:
    return select_weeks(indonesia.get_season(lang.value)[0], week)


@router.get(
    path="/id/standings",
    name="api.esports.id_standings",
    response_model=StandingsResponse,
    summary="Indonesia Regular Season Standings",
    description=_STANDINGS_DESCRIPTION.format(league="the Indonesian professional league", lang_param=_LANG_PARAM),
    responses=_example(_STANDINGS_EXAMPLE),
)
def id_standings(lang: LeagueLang = LeagueLanguageEnum.ENGLISH) -> StandingsResponse:
    return StandingsResponse(standings=indonesia.get_season(lang.value)[1])


@router.get(
    path="/id/matches/{match_id}",
    name="api.esports.id_match",
    response_model=MatchDetailResponse,
    summary="Indonesia Match Details",
    description=_MATCH_DESCRIPTION.format(
        league="the Indonesian professional league",
        extra=" Each team also reports the game winner and its kills; the game has a duration.",
    ),
    responses=_example(_ID_MATCH_EXAMPLE),
)
def id_match(
    match_id: Annotated[int, Path(title="Match ID", description="**match_id** from the schedule endpoint.", ge=1)],
) -> MatchDetailResponse:
    return indonesia.get_match(match_id)


@router.get(
    path="/ph/schedule",
    name="api.esports.ph_schedule",
    response_model=ScheduleResponse,
    summary="Philippines Regular Season Schedule",
    description=_SCHEDULE_DESCRIPTION.format(league="the Philippine professional league", lang_param=""),
    responses=_example(_SCHEDULE_EXAMPLE),
)
def ph_schedule(week: Week = None) -> ScheduleResponse:
    return select_weeks(philippines.get_schedule(), week)


@router.get(
    path="/ph/standings",
    name="api.esports.ph_standings",
    response_model=StandingsResponse,
    summary="Philippines Regular Season Standings",
    description=_STANDINGS_DESCRIPTION.format(league="the Philippine professional league", lang_param=""),
    responses=_example(_STANDINGS_EXAMPLE),
)
def ph_standings() -> StandingsResponse:
    return StandingsResponse(standings=philippines.get_standings())


@router.get(
    path="/ph/matches/{match_slug}",
    name="api.esports.ph_match",
    response_model=MatchDetailResponse,
    summary="Philippines Match Details",
    description=_MATCH_DESCRIPTION.format(
        league="the Philippine professional league",
        extra=(
            " Each team also reports its totals (gold, damage, buffs, objectives) and every player has the "
            "**item_sequence**, the items in purchase order with their position on the timeline."
        ),
    ),
    responses=_example(_PH_MATCH_EXAMPLE),
)
def ph_match(
    match_slug: Annotated[
        str,
        Path(
            title="Match Slug",
            description="**match_id** from the schedule endpoint, e.g. `rora-onic-20260821`.",
            pattern=r"^[a-z0-9-]+$",
            max_length=80,
        ),
    ],
) -> MatchDetailResponse:
    return philippines.get_match(match_slug)
