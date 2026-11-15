from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Response
from fastapi.openapi.models import Example

from app.api.dependencies import require_api_available
from app.api.params import LeagueLang
from app.core.enums import LeagueEnum, LeagueLanguageEnum
from app.schemas.esports import (
    CalculateRequest,
    HeroPoolsResponse,
    HeroStatisticsResponse,
    MvpStandingsResponse,
    PlayerPoolsResponse,
    PlayerStatisticsResponse,
    SavageManiacResponse,
    TeamStatisticsResponse,
    MatchDetailResponse,
    PlayerDetailResponse,
    PlayoffsResponse,
    ScheduleResponse,
    SimulateRequest,
    StandingsResponse,
    StandingsSimulationResponse,
    TeamDetailResponse,
    TeamsResponse,
)
from app.services.esports import cambodia, indonesia, malaysia, philippines, simulation
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
                            "round": None,
                            "best_of": 3,
                            "status": "finished",
                            "winner": "team1",
                        }
                    ],
                }
            ],
        }
    ]
}

_PLAYOFFS_EXAMPLE = {
    "bracket_image": "https://wsrv.nl/?url=https://example.com/playoffs/bracket.png",
    "seeds": [{"seed": 1, "team": {"name": "TLID", "full_name": None, "logo": _LOGO}, "match_wl": {"win": 12, "lose": 4}}],
    "days": [
        {
            "day": None,
            "label": "Sunday, 8 November 2026",
            "matches": [
                {
                    "match_id": None,
                    "start_at": "2026-11-08T09:00:00+00:00",
                    "local_time": "16:00",
                    "team1": {"name": "TLID", "full_name": None, "logo": _LOGO},
                    "team2": {"name": "TBD", "full_name": None, "logo": None},
                    "score1": None,
                    "score2": None,
                    "replay_url": None,
                    "round": "Grand Finals",
                    "best_of": 7,
                    "status": "scheduled",
                    "winner": None,
                }
            ],
        }
    ],
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
                "duration_estimate": None if duration else "16:48",
                "duration_estimate_seconds": None if duration else 1008,
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
                "highlights": [],
                "screenshots": [],
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
    "- **team1** / **team2** with logo, and **score1** / **score2** (null until played).\n"
    "- **best_of** (3 in the regular season), **status** (`scheduled`, `in_progress` or `finished`, from the score) "
    "and **winner** (`team1`, `team2`, or null until finished).\n\n"
    "Data is read from the league's official public site and cached for 5 minutes."
)
_PLAYOFFS_DESCRIPTION = (
    "Playoffs of {league}: the bracket image, the playoff seeds and every playoff match, grouped by day.\n{lang_param}\n"
    "- **bracket_image**: The league's bracket picture, through the image proxy; null when none is published.\n"
    "- **seeds**: Regular-season rank and match win-lose of each playoff team, best first.{seeds_note}\n"
    "- **days** / **matches**: Same fields as the schedule endpoint. **best_of** is 5, and 7 for the lower bracket final "
    "and the grand final. A side that is not decided yet is named `TBD` with a null logo.{round_note}\n\n"
    "**match_id** works with the matches endpoint, as in the regular season. "
    "Data is read from the league's official public site and cached for 5 minutes."
)
_STANDINGS_DESCRIPTION = (
    "Regular-season standings of {league}: rank, team, match point, match win-lose, "
    "net game win and game win-lose.\n{lang_param}\nData is read from the league's official public site and cached for 5 minutes."
)
_TEAM_SUMMARY = {"team_id": "onic", "name": "ONIC", "full_name": "ONIC PH", "logo": _LOGO}
_TEAMS_EXAMPLE = {"teams": [_TEAM_SUMMARY]}
_MEMBER_EXAMPLE = {
    "name": "AJ",
    "role": "Mid Lane",
    "photo": "https://wsrv.nl/?url=https://example.com/players/aj.png",
    "archetype": "Flex Mid",
    "secondary_role": "Jungle",
    "tier": "B",
    "birth_date": "2001-07-10",
    "age": 25,
    "nationality": "Malaysia",
    "hometown": "Kedah",
    "previous_team": {"name": "CG (Free Agent)", "full_name": None, "logo": None},
    "socials": [{"platform": "instagram", "url": "https://www.instagram.com/example"}],
    "stats": {"matches": 22, "kills": 74, "deaths": 49, "assists": 66, "kda": 2.86, "savage": 0, "maniac": 0},
}
_TEAM_EXAMPLE = {
    **_TEAM_SUMMARY,
    "season": 18,
    "tagline": None,
    "description": "The OGs of the league are ready to lead the team back to the top.",
    "socials": [{"platform": "instagram", "url": "https://www.instagram.com/example"}],
    "team_photo": None,
    "gallery": [],
    "entrance_music": None,
    "achievements": [{"title": "M6 World Championship", "placement": "1st"}],
    "players": [_MEMBER_EXAMPLE],
    "staff": [{**_MEMBER_EXAMPLE, "name": "Pheww", "role": "Coach", "archetype": None, "secondary_role": None, "tier": None, "stats": None}],
    "standing": _STANDINGS_EXAMPLE["standings"][0],
    "matches": [
        {
            **_SCHEDULE_EXAMPLE["weeks"][0]["days"][0]["matches"][0],
            "stage": "regular_season",
            "week": 1,
            "day_label": "Friday, 14 August 2026",
            "opponent": {"name": "RRQ", "full_name": None, "logo": _LOGO},
            "result": "win",
        }
    ],
}
_TEAMS_DESCRIPTION = (
    "Teams of {league} this season: **team_id** (for the team endpoint), short **name** as the schedule and standings "
    "write it, **full_name** and **logo**.{note}\n\nData is read from the league's official public site and cached for 5 minutes."
)
_TEAM_DESCRIPTION = (
    "Everything {league} publishes about one team:\n"
    "- **season**, **socials** (`platform` and `url`){extra_team}\n"
    "- **players** and **staff** (coaches, analysts): **name**, **role** in one spelling for every league "
    "(`Gold Lane`, `EXP Lane`, `Mid Lane`, `Jungle`, `Roam`, `Coach`, `Assistant Coach`, `Analyst`) and **photo**.{extra_member}\n"
    "- **standing**: the team's row of the regular-season table (null before the league publishes it).\n"
    "- **matches**: every regular-season and playoff match of the team, with the schedule's fields plus **stage**, **week**, "
    "**day_label**, **opponent** and **result** (`win`, `loss`, or null until finished); **match_id** works with the matches endpoint.\n\n"
    "An unknown **team_id** returns 404 `TEAM_NOT_FOUND` with the league's ids. Data is cached for 5 minutes."
)
_TEAM_ID_HELP = "**team_id** from the teams endpoint{example}."


def _team_id(example: str):
    return Annotated[
        str,
        Path(title="Team ID", description=_TEAM_ID_HELP.format(example=f", e.g. `{example}`"), pattern=r"^[a-z0-9-]+$", max_length=60),
    ]


IdTeamId = _team_id("onic")
PhTeamId = _team_id("tlph")
MyTeamId = _team_id("rrq-tora")
KhTeamId = _team_id("pro-esports")

_MATCH_DESCRIPTION = (
    "Full match history of one match of {league}: every game with both teams and all players "
    "(hero, KDA, items, emblem, talents, gold, damage dealt, damage taken and tower damage).{extra}\n\n"
    "Battle spells are not published by the league sites. Regular-season and playoff matches both work. Data is cached for 5 minutes."
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
    return select_weeks(indonesia.get_season(lang.value).weeks, week)


@router.get(
    path="/id/playoffs",
    name="api.esports.id_playoffs",
    response_model=PlayoffsResponse,
    summary="Indonesia Playoffs",
    description=_PLAYOFFS_DESCRIPTION.format(
        league="the Indonesian professional league",
        lang_param=_LANG_PARAM,
        seeds_note=" Read from the league's playoff table.",
        round_note=" Each match also has its **round**, as the league names it (`Round 1 Match 1`, `Upper Bracket Finals`...).",
    ),
    responses=_example(_PLAYOFFS_EXAMPLE),
)
def id_playoffs(lang: LeagueLang = LeagueLanguageEnum.ENGLISH) -> PlayoffsResponse:
    return indonesia.get_season(lang.value).playoffs


@router.get(
    path="/id/standings",
    name="api.esports.id_standings",
    response_model=StandingsResponse,
    summary="Indonesia Regular Season Standings",
    description=_STANDINGS_DESCRIPTION.format(league="the Indonesian professional league", lang_param=_LANG_PARAM),
    responses=_example(_STANDINGS_EXAMPLE),
)
def id_standings(lang: LeagueLang = LeagueLanguageEnum.ENGLISH) -> StandingsResponse:
    return StandingsResponse(standings=indonesia.get_season(lang.value).standings)


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
    path="/id/teams",
    name="api.esports.id_teams",
    response_model=TeamsResponse,
    summary="Indonesia Teams",
    description=_TEAMS_DESCRIPTION.format(league="the Indonesian professional league", note=" **full_name** is on the team endpoint."),
    responses=_example(_TEAMS_EXAMPLE),
)
def id_teams() -> TeamsResponse:
    return TeamsResponse(teams=indonesia.get_teams())


@router.get(
    path="/id/teams/{team_id}",
    name="api.esports.id_team",
    response_model=TeamDetailResponse,
    summary="Indonesia Team Details",
    description=_TEAM_DESCRIPTION.format(
        league="the Indonesian professional league",
        extra_team=". The league publishes no description or achievements.",
        extra_member=" Photos are served through this API.",
    ),
    responses=_example(_TEAM_EXAMPLE),
)
def id_team(team_id: IdTeamId) -> TeamDetailResponse:
    return indonesia.get_team(team_id)


@router.get(path="/id/images/{team_id}/{name}", name="api.esports.id_image", include_in_schema=False)
def id_image(
    team_id: Annotated[str, Path(pattern=r"^[a-z0-9-]+$", max_length=60)],
    name: Annotated[str, Path(pattern=r"^[\w%. ()-]+\.(?:webp|png|jpe?g)$", max_length=120)],
) -> Response:
    """A roster photo of the Indonesian league, served from here so the league's file host never appears in an answer."""
    content, media_type = indonesia.get_player_photo(team_id, name)
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})



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
    path="/ph/playoffs",
    name="api.esports.ph_playoffs",
    response_model=PlayoffsResponse,
    summary="Philippines Playoffs",
    description=_PLAYOFFS_DESCRIPTION.format(
        league="the Philippine professional league",
        lang_param="",
        seeds_note=" The site publishes none, so these are the top of the regular-season standings (all but the bottom 2).",
        round_note=" The league names no rounds, so **round** is null.",
    ),
    responses=_example(_PLAYOFFS_EXAMPLE),
)
def ph_playoffs() -> PlayoffsResponse:
    return philippines.get_playoffs()


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
            "**item_sequence**, the items in purchase order with their position on the timeline. The site gives no game clock, "
            "so each game has **duration_estimate** (`m:ss`) and **duration_estimate_seconds**: total gold over gold per minute, "
            "averaged over both teams, close to the real length but not exact. **highlights** (video links) and "
            "**screenshots** are filled when the league attaches them."
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

@router.get(
    path="/ph/teams",
    name="api.esports.ph_teams",
    response_model=TeamsResponse,
    summary="Philippines Teams",
    description=_TEAMS_DESCRIPTION.format(league="the Philippine professional league", note=""),
    responses=_example(_TEAMS_EXAMPLE),
)
def ph_teams() -> TeamsResponse:
    return TeamsResponse(teams=philippines.get_teams())


@router.get(
    path="/ph/teams/{team_id}",
    name="api.esports.ph_team",
    response_model=TeamDetailResponse,
    summary="Philippines Team Details",
    description=_TEAM_DESCRIPTION.format(
        league="the Philippine professional league",
        extra_team=", the league's **description** of the team and its **achievements** (`title` and `placement`, as the league writes them).",
        extra_member="",
    ),
    responses=_example(_TEAM_EXAMPLE),
)
def ph_team(team_id: PhTeamId) -> TeamDetailResponse:
    return philippines.get_team(team_id)



@router.get(
    path="/my/schedule",
    name="api.esports.my_schedule",
    response_model=ScheduleResponse,
    summary="Malaysia Regular Season Schedule",
    description=_SCHEDULE_DESCRIPTION.format(league="the Malaysian professional league", lang_param=""),
    responses=_example(_SCHEDULE_EXAMPLE),
)
def my_schedule(week: Week = None) -> ScheduleResponse:
    return select_weeks(malaysia.get_season().weeks, week)


@router.get(
    path="/my/playoffs",
    name="api.esports.my_playoffs",
    response_model=PlayoffsResponse,
    summary="Malaysia Playoffs",
    description=_PLAYOFFS_DESCRIPTION.format(
        league="the Malaysian professional league",
        lang_param="",
        seeds_note=" The teams the league's standings mark as playoff teams (6 of 8).",
        round_note=(
            " Each match also has its **round** as the league names it (`Upper Bracket QuarterFinals`...), and **best_of** "
            "is the series length the league states for that round. The league publishes no bracket picture."
        ),
    ),
    responses=_example(_PLAYOFFS_EXAMPLE),
)
def my_playoffs() -> PlayoffsResponse:
    return malaysia.get_season().playoffs


@router.get(
    path="/my/standings",
    name="api.esports.my_standings",
    response_model=StandingsResponse,
    summary="Malaysia Regular Season Standings",
    description=_STANDINGS_DESCRIPTION.format(league="the Malaysian professional league", lang_param=""),
    responses=_example(_STANDINGS_EXAMPLE),
)
def my_standings() -> StandingsResponse:
    return StandingsResponse(standings=malaysia.get_season().standings)


@router.get(
    path="/my/matches/{match_id}",
    name="api.esports.my_match",
    response_model=MatchDetailResponse,
    summary="Malaysia Match Details",
    description=_MATCH_DESCRIPTION.format(
        league="the Malaysian professional league",
        extra=(
            " Each team also reports the game winner and its kills; the game has a duration. **emblem** and **talents** "
            "are null and empty: the league site shows the same set for both players of a lane, so it cannot be told whose it is."
        ),
    ),
    responses=_example(_ID_MATCH_EXAMPLE),
)
def my_match(
    match_id: Annotated[int, Path(title="Match ID", description="**match_id** from the schedule endpoint.", ge=1)],
) -> MatchDetailResponse:
    return malaysia.get_match(match_id)

@router.get(
    path="/my/teams",
    name="api.esports.my_teams",
    response_model=TeamsResponse,
    summary="Malaysia Teams",
    description=_TEAMS_DESCRIPTION.format(league="the Malaysian professional league", note=""),
    responses=_example(_TEAMS_EXAMPLE),
)
def my_teams() -> TeamsResponse:
    return TeamsResponse(teams=malaysia.get_teams())


@router.get(
    path="/my/teams/{team_id}",
    name="api.esports.my_team",
    response_model=TeamDetailResponse,
    summary="Malaysia Team Details",
    description=_TEAM_DESCRIPTION.format(
        league="the Malaysian professional league",
        extra_team=", **tagline**, **description**, **team_photo**, the **gallery** and **entrance_music** (a signed link that expires within hours).",
        extra_member=(
            " The Malaysian league also gives each member's **birth_date**, **age**, **nationality**, **hometown**, **previous_team**, "
            "**socials**, and for players the **archetype** (`Flex Jungler`...), **secondary_role**, **tier** (the league's rating) and "
            "season **stats** (matches, kills, deaths, assists, KDA, savages and maniacs, as the league counts them)."
        ),
    ),
    responses=_example(_TEAM_EXAMPLE),
)
def my_team(team_id: MyTeamId) -> TeamDetailResponse:
    return malaysia.get_team(team_id)



@router.get(
    path="/kh/schedule",
    name="api.esports.kh_schedule",
    response_model=ScheduleResponse,
    summary="Cambodia Regular Season Schedule",
    description=_SCHEDULE_DESCRIPTION.format(league="the Cambodian professional league", lang_param="")
    + " The Cambodian season is a single round robin (every pair meets once), and the league publishes no match details, "
    "so **match_id** is always null. A match on today's card shows no time while it is live or about to start.",
    responses=_example(_SCHEDULE_EXAMPLE),
)
def kh_schedule(week: Week = None) -> ScheduleResponse:
    return select_weeks(cambodia.get_schedule(week), week)


@router.get(
    path="/kh/playoffs",
    name="api.esports.kh_playoffs",
    response_model=PlayoffsResponse,
    summary="Cambodia Playoffs",
    description=_PLAYOFFS_DESCRIPTION.format(
        league="the Cambodian professional league",
        lang_param="",
        seeds_note=" The site publishes none, so these are the top of the regular-season standings (6 of 10, the league's usual format).",
        round_note=" The league names no rounds, so **round** is null; **days** stays empty until the league publishes the bracket.",
    ),
    responses=_example(_PLAYOFFS_EXAMPLE),
)
def kh_playoffs() -> PlayoffsResponse:
    return cambodia.get_playoffs()


@router.get(
    path="/kh/standings",
    name="api.esports.kh_standings",
    response_model=StandingsResponse,
    summary="Cambodia Regular Season Standings",
    description=_STANDINGS_DESCRIPTION.format(league="the Cambodian professional league", lang_param=""),
    responses=_example(_STANDINGS_EXAMPLE),
)
def kh_standings() -> StandingsResponse:
    return StandingsResponse(standings=cambodia.get_standings())


_KH_PLAYER_EXAMPLE = {
    "player_id": "d7",
    "name": "D7",
    "role": "Roam",
    "photo": "https://wsrv.nl/?url=https://arena.rone.dev/api/esports/kh/images/players/D7.webp",
    "team": {"team_id": "vigor-apex", "name": "VGR", "full_name": "Vigor Apex", "logo": _LOGO},
    "profile": {"full_name": "D7", "based": "Cambodia"},
    "team_history": [{"team_id": "vigor-apex", "name": "Vigor Apex", "period": "2026 – Present"}],
    "stats": [
        {
            "label": "MPL KH S11",
            "heroes_played": 4,
            "mvp_points": 0,
            "matches_played": 3,
            "games_played": 8,
            "kills": 5,
            "assists": 68,
            "gold": 65592,
            "gold_per_min": 555,
            "damage_dealt": 189093,
            "damage_taken": 852688,
            "tower_damage": 2252,
        }
    ],
}


@router.get(
    path="/kh/teams",
    name="api.esports.kh_teams",
    response_model=TeamsResponse,
    summary="Cambodia Teams",
    description=_TEAMS_DESCRIPTION.format(league="the Cambodian professional league", note=""),
    responses=_example(_TEAMS_EXAMPLE),
)
def kh_teams() -> TeamsResponse:
    return TeamsResponse(teams=cambodia.get_teams())


@router.get(
    path="/kh/teams/{team_id}",
    name="api.esports.kh_team",
    response_model=TeamDetailResponse,
    summary="Cambodia Team Details",
    description=_TEAM_DESCRIPTION.format(
        league="the Cambodian professional league",
        extra_team=(
            ", the league's **description**, **achievements** (`title`, `placement`, `date`, `tier`, `prize`; the league types "
            "them by hand, so a few read oddly), **profile** facts it lists (`region`, `owner`, `manager`) and **stats**: season "
            "and career totals (matches and games played, match and game win-lose, win rate, kills, gold, damage, lords, "
            "turtles and towers). The league publishes no social links."
        ),
        extra_member=" Each member also has a **player_id** for the player endpoint. Photos and logos are served through this API.",
    ),
    responses=_example(_TEAM_EXAMPLE),
)
def kh_team(team_id: KhTeamId) -> TeamDetailResponse:
    return cambodia.get_team(team_id)


@router.get(
    path="/kh/players/{player_id}",
    name="api.esports.kh_player",
    response_model=PlayerDetailResponse,
    summary="Cambodia Player Details",
    description=(
        "One player of the Cambodian professional league: **name**, **role**, **photo**, current **team**, **profile** "
        "(`full_name`, `based`...), **team_history** (team and period) and **stats**, the season and career totals "
        "(heroes played, MVP points, matches and games played, kills, assists, gold, gold per minute, damage dealt, "
        "damage taken and tower damage). An unknown **player_id** returns 404 `PLAYER_NOT_FOUND`. Data is cached for 5 minutes."
    ),
    responses=_example(_KH_PLAYER_EXAMPLE),
)
def kh_player(
    player_id: Annotated[
        str,
        Path(title="Player ID", description="**player_id** from the team endpoint, e.g. `d7`.", pattern=r"^[a-z0-9-]+$", max_length=80),
    ],
) -> PlayerDetailResponse:
    return cambodia.get_player(player_id)


@router.get(path="/kh/images/{name:path}", name="api.esports.kh_image", include_in_schema=False)
def kh_image(
    name: Annotated[str, Path(pattern=r"^(?:(?:teams|players|heroes/square)/)?[\w%. ()-]+\.(?:webp|png|jpe?g)$", max_length=160)],
) -> Response:
    """A Cambodian team logo or player photo, served from here so the league's image host never appears in an answer."""
    content, media_type = cambodia.get_image(name)
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})


# ---- season statistics

_STAT_TEAM = {"name": "TLID", "full_name": "TEAM LIQUID ID", "logo": _LOGO}
_STAT_HERO = {"name": "Hirara", "image": _HERO_IMAGE}
_TEAM_STATS_EXAMPLE = {
    "teams": [
        {"team": _STAT_TEAM, "kills": 606, "deaths": 499, "assists": 1595, "gold": 2644312, "damage": 10852558, "lord": 75, "tortoise": 96, "tower": 333}
    ]
}
_PLAYER_STATS_EXAMPLE = {
    "leaderboards": [
        {
            "title": "Top 5 Kills",
            "entries": [{"rank": 1, "name": "NNAEL", "team": _STAT_TEAM, "photo": None, "hero": None, "value": 305}],
        }
    ],
    "players": [
        {
            "name": "MORENOOO",
            "team": _STAT_TEAM,
            "role": "Mid Lane",
            "games": 67,
            "kills": 155,
            "deaths": 109,
            "assists": 505,
            "avg_kills": 2.31,
            "avg_deaths": 1.63,
            "avg_assists": 7.54,
            "kda": 6.06,
            "kill_participation": 78.0,
        }
    ],
}
_HERO_STATS_EXAMPLE = {
    "leaderboards": [
        {"title": "Top 5 Pick", "entries": [{"rank": 1, "name": "Hirara", "team": None, "photo": None, "hero": _STAT_HERO, "value": 103}]}
    ],
    "heroes": [{"hero": _STAT_HERO, "picks": 103, "bans": 40, "wins": 55, "pick_rate": None, "ban_rate": None, "win_rate": 53.0}],
}
_STATS_NOTE = " Data is read from the league's official public site and cached for 5 minutes."
_STAT_LEAGUES = {
    "id": ("Indonesia", "the Indonesian professional league", indonesia),
    "ph": ("Philippines", "the Philippine professional league", philippines),
    "my": ("Malaysia", "the Malaysian professional league", malaysia),
    "kh": ("Cambodia", "the Cambodian professional league", cambodia),
}
_PLAYER_STATS_NOTES = {
    "id": " Leaderboards: the top 5 by kills, assists and average KDA (at least 5 games). Each player has a **role**.",
    "ph": " Leaderboards: the top 5 by average kills, average assists and KDA. The league gives no games played or role.",
    "my": " The league publishes no leaderboards. Each player's **role** comes from the league's lane filter.",
    "kh": " Leaderboards: the top 5 by kills, assists and average KDA (at least 5 games). Each player has a **role**; photos and logos are served through this API.",
}
_HERO_STATS_NOTES = {
    "id": " Leaderboards: the top 5 heroes by picks, bans and win rate.",
    "ph": " Leaderboards: the top 5 heroes by picks, bans and win rate. Only this league also gives **pick_rate** and **ban_rate**.",
    "my": " The league publishes no leaderboards.",
    "kh": " Leaderboards: the top 5 heroes by picks, bans and win rate. Only heroes picked or banned this season are listed; hero images are served through this API.",
}


def _statistics_routes(league: str) -> None:
    country, name, service = _STAT_LEAGUES[league]
    router.add_api_route(
        f"/{league}/statistics/teams",
        service.get_team_statistics,
        name=f"api.esports.{league}_team_statistics",
        response_model=TeamStatisticsResponse,
        summary=f"{country} Team Statistics",
        description=(
            f"Season totals of every team of {name}: kills, deaths, assists, gold, damage, lords, turtles (**tortoise**) and "
            "towers destroyed." + _STATS_NOTE
        ),
        responses=_example(_TEAM_STATS_EXAMPLE),
    )
    router.add_api_route(
        f"/{league}/statistics/players",
        service.get_player_statistics,
        name=f"api.esports.{league}_player_statistics",
        response_model=PlayerStatisticsResponse,
        summary=f"{country} Player Statistics",
        description=(
            f"Season statistics of every player of {name}: games, total and average kills, deaths and assists, KDA and kill "
            "participation (percent), with the player's team, and the league's **leaderboards** (each entry's **value** is the figure "
            "the board ranks). A figure the league leaves out, or a substitute who has not played, is null."
            + _PLAYER_STATS_NOTES[league]
            + _STATS_NOTE
        ),
        responses=_example(_PLAYER_STATS_EXAMPLE),
    )
    router.add_api_route(
        f"/{league}/statistics/heroes",
        service.get_hero_statistics,
        name=f"api.esports.{league}_hero_statistics",
        response_model=HeroStatisticsResponse,
        summary=f"{country} Hero Statistics",
        description=f"Picks, bans, wins and win rate (percent) of every hero in {name} this season." + _HERO_STATS_NOTES[league] + _STATS_NOTE,
        responses=_example(_HERO_STATS_EXAMPLE),
    )


for _league in _STAT_LEAGUES:
    _statistics_routes(_league)


_HERO_POOLS_EXAMPLE = {
    "players": [
        {
            "name": "MORENOOO",
            "team": _STAT_TEAM,
            "role": "Mid Lane",
            "total": 12,
            "heroes": [{"hero": {"name": "Selena", "image": _HERO_IMAGE}, "picks": 18, "win_rate": 33.0}],
        }
    ]
}
_PLAYER_POOLS_EXAMPLE = {
    "heroes": [
        {
            "hero": {"name": "Miya", "image": _HERO_IMAGE},
            "total": 10,
            "players": [{"name": "Zeonn", "team": _STAT_TEAM, "photo": None, "picks": 7, "win_rate": 71.0}],
        }
    ]
}
_MVP_EXAMPLE = {"standings": [{"rank": 1, "name": "KEVIN", "team": _STAT_TEAM, "photo": None, "points": 151}]}


def _pool_routes(league: str) -> None:
    """Hero pools, player pools and the MVP race: published by the Indonesian and Cambodian leagues."""
    country, name, service = _STAT_LEAGUES[league]
    router.add_api_route(
        f"/{league}/statistics/hero-pools",
        service.get_hero_pools,
        name=f"api.esports.{league}_hero_pools",
        response_model=HeroPoolsResponse,
        summary=f"{country} Hero Pools",
        description=(
            f"Every hero each player of {name} has played this season: the player, team and **role**, **total** different heroes, "
            "and per hero the **picks** and **win_rate** (percent)." + _STATS_NOTE
        ),
        responses=_example(_HERO_POOLS_EXAMPLE),
    )
    router.add_api_route(
        f"/{league}/statistics/player-pools",
        service.get_player_pools,
        name=f"api.esports.{league}_player_pools",
        response_model=PlayerPoolsResponse,
        summary=f"{country} Player Pools",
        description=(
            f"For every hero, the players of {name} who have played it this season: **total** different players, and per player "
            "the team, **photo** (served through this API), **picks** and **win_rate** (percent)." + _STATS_NOTE
        ),
        responses=_example(_PLAYER_POOLS_EXAMPLE),
    )
    router.add_api_route(
        f"/{league}/statistics/mvp",
        service.get_mvp_standings,
        name=f"api.esports.{league}_mvp_standings",
        response_model=MvpStandingsResponse,
        summary=f"{country} MVP Standings",
        description=f"The MVP race of {name}: rank, player, team, **photo** and **points**." + _STATS_NOTE,
        responses=_example(_MVP_EXAMPLE),
    )


for _league in ("id", "kh"):
    _pool_routes(_league)


@router.get(
    path="/my/statistics/savage-maniac",
    name="api.esports.my_savage_maniac",
    response_model=SavageManiacResponse,
    summary="Malaysia Savage and Maniac",
    description="How many savages and maniacs each player of the Malaysian professional league has this season, with the team." + _STATS_NOTE,
    responses=_example({"players": [{"name": "Innocent", "team": _STAT_TEAM, "savage": 1, "maniac": 1}]}),
)
def my_savage_maniac() -> SavageManiacResponse:
    return malaysia.get_savage_maniac()


# ---- standings tools

_RULES = (
    "Matches are first to 2 games, so a finished match is 2-0, 2-1, 1-2 or 0-2 (a 1-1 needs a deciding game). "
    "A team gets 1 match point per match won. Teams are ranked by match points, then net game wins "
    "(games won minus games lost), then head-to-head among the tied teams; a tie that survives all three "
    "is reported as `unresolved`. The same rules reproduce the official Indonesian, Philippine, Malaysian and Cambodian tables.\n\n"
    "Each team also gets a **status** from what it can still reach: `clinched` (certain to be in the playoffs), "
    "`eliminated` (certain to miss them) or `alive`. The status is exact once the season is over and "
    "conservative before that, so a decided team can still read `alive`, never the other way round.\n\n"
    "Each team also has **playoff_probability**, its chance in percent, with every decimal the simulation gives, of finishing in the playoff spots. "
    "It comes from simulating the matches still to play: with **model** `form` (default) a team's chance in a match follows its record "
    "so far, with `even` every match is a coin flip, and the winner takes the match 2-0 in 62% of cases (the real share). "
    "**simulations** sets how many seasons are simulated; omit it to let the server choose. Clinched teams read 100 and eliminated teams 0. "
    "The same request always returns the same numbers, and with the default sample they are accurate to about one percentage point.\n\n"
    "To edit results, send them in **results** as `week`, `team1`, `team2`, `score1`, `score2`; "
    "either team order works, and leaving both scores out clears a match. Matches you do not mention keep their real result."
)
_SIMULATE_DESCRIPTION = (
    "Re-rank a professional league's regular season after changing match results, to see what a different "
    "result would do to the table and the playoff line.\n\n"
    "The schedule and real results are the league's live ones (see the schedule endpoints). "
    "Send `{\"results\": []}` to get the current table with statuses. **eliminated** is how many teams at the bottom miss the "
    "playoffs; it defaults to 3 for Indonesia (`id`), 2 for the Philippines (`ph`), 2 for Malaysia (`my`) and 4 for Cambodia (`kh`).\n\n"
    + _RULES
    + "\n\nThe real schedule is cached for 5 minutes."
)
_CALCULATE_DESCRIPTION = (
    "The same calculator for any league: give the team names (or just a count) and enter match results. "
    "The schedule is generated as a double round robin with as many weeks as teams, each week with one fewer "
    "match than teams, like the professional leagues. Nothing is fetched from a league site.\n\n"
    "Only **teams** matters for the schedule (omit it and send **team_count** instead to get Team A, Team B, ...). **eliminated** defaults to 3, or less in a small league.\n\n"
    + _RULES
)

_SIM_TEAM = {"name": "NAVI", "full_name": "NAVI", "logo": _LOGO}
_SIMULATION_EXAMPLE = {
    "teams": 9,
    "weeks_count": 9,
    "playoff_spots": 6,
    "eliminated": 3,
    "matches_played": 61,
    "matches_remaining": 11,
    "edited_matches": 1,
    "probability_model": "form",
    "probability_simulations": 10909,
    "weeks": [
        {
            "week": 8,
            "matches": [
                {"team1": _SIM_TEAM, "team2": {"name": "TLID", "full_name": "TLID", "logo": _LOGO}, "score1": 0, "score2": 2, "state": "edited"}
            ],
        }
    ],
    "standings": [
        {
            "rank": 1,
            "team": _SIM_TEAM,
            "match_point": 10,
            "match_wl": {"win": 10, "lose": 4},
            "net_game_win": 12,
            "game_wl": {"win": 21, "lose": 9},
            "played": 14,
            "remaining": 4,
            "max_match_point": 14,
            "tiebreak": "net_game_win",
            "status": "alive",
            "in_playoffs_zone": True,
            "playoff_probability": 97.33944954128441,
        }
    ],
}
_SIMULATE_BODIES: dict[str, Example] = {
    "indonesia": {
        "summary": "Indonesia: flip one result",
        "value": {"results": [{"week": 8, "team1": "NAVI", "team2": "TLID", "score1": 0, "score2": 2}], "eliminated": 3},
    },
    "philippines": {
        "summary": "Philippines: flip one result",
        "value": {"results": [{"week": 8, "team1": "RORA", "team2": "TWIS", "score1": 0, "score2": 2}], "eliminated": 2},
    },
    "malaysia": {
        "summary": "Malaysia: flip one result",
        "value": {"results": [{"week": 8, "team1": "VMS", "team2": "SRG", "score1": 2, "score2": 0}], "eliminated": 2},
    },
    "cambodia": {
        "summary": "Cambodia: flip one result",
        "value": {"results": [{"week": 4, "team1": "VGR", "team2": "FLKH", "score1": 0, "score2": 2}], "eliminated": 4},
    },
    "current": {"summary": "Current table, no changes", "value": {"results": []}},
}
_CALCULATE_BODIES: dict[str, Example] = {
    "default": {
        "summary": "8 teams with one result",
        "value": {
            "teams": ["Team A", "Team B", "Team C", "Team D", "Team E", "Team F", "Team G", "Team H"],
            "eliminated": 3,
            "results": [{"week": 1, "team1": "Team A", "team2": "Team H", "score1": 2, "score2": 0}],
        },
    },
    "small": {
        "summary": "4 named teams",
        "value": {"teams": ["Alpha", "Bravo", "Charlie", "Delta"], "eliminated": 1, "results": []},
    },
}


@router.post(
    path="/{league}/standings/simulate",
    name="api.esports.simulate_standings",
    response_model=StandingsSimulationResponse,
    summary="Simulate League Standings",
    description=_SIMULATE_DESCRIPTION,
    responses=_example(_SIMULATION_EXAMPLE),
)
def simulate_standings(
    league: Annotated[LeagueEnum, Path(title="League", description="`id` for Indonesia, `ph` for the Philippines, `my` for Malaysia or `kh` for Cambodia.")],
    body: Annotated[SimulateRequest, Body(openapi_examples=_SIMULATE_BODIES)],
) -> StandingsSimulationResponse:
    return simulation.simulate_league(league, body)


@router.post(
    path="/standings/calculate",
    name="api.esports.calculate_standings",
    response_model=StandingsSimulationResponse,
    summary="Calculate Custom League Standings",
    description=_CALCULATE_DESCRIPTION,
    responses=_example(_SIMULATION_EXAMPLE),
)
def calculate_standings(
    body: Annotated[CalculateRequest, Body(openapi_examples=_CALCULATE_BODIES)],
) -> StandingsSimulationResponse:
    return simulation.calculate(body)
