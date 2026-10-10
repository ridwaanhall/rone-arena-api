"""Scraper for the Indonesian league site: schedule, standings and match details."""
from __future__ import annotations

import re
from datetime import UTC, datetime

from bs4 import SoupStrainer
from bs4.element import Tag

from app.core.exceptions import AppError
from app.core.security import EsportsSourceProvider
from app.schemas.esports import (
    Asset,
    Game,
    GameTeam,
    Hero,
    MatchDetailResponse,
    Player,
    ScheduleDay,
    ScheduleMatch,
    ScheduleWeek,
    Standing,
    Team,
)
from app.services.esports.common import (
    CACHE_SECONDS,
    fetch_page,
    kda_ratio,
    parse_html,
    parse_record,
    text_of,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

_WEEK_ID = re.compile(r"^t-week-\d+$")
# Only the week panes and the standings table are needed from the (very large) schedule page.
_SEASON_PARTS = SoupStrainer(attrs={"id": re.compile(r"^(t-week-\d+|standing-regular-season)$")})
_MATCH_ID = re.compile(r"openMatchDetail\((\d+)\)")
_CALENDAR_START = re.compile(r"dates=(\d{8}T\d{6})/")
# The per-player "data" row has no labels, only icons; the icon names the figure.
_STAT_BY_ICON = {"sword": "damage_dealt", "shield": "damage_taken", "tower": "tower_damage", "money": "gold"}


def _team(element: Tag) -> Team:
    image = element.find("img")
    return Team(name=text_of(element.select_one(".name")), logo=image.get("src") if image else None)


def _score(element: Tag) -> int | None:
    value = text_of(element)
    return int(value) if value else None


def _start_at(card: Tag) -> str | None:
    found = _CALENDAR_START.search(str(card))
    if not found:
        return None
    return datetime.strptime(found.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=UTC).isoformat()


def _schedule_match(card: Tag) -> ScheduleMatch:
    match_id = _MATCH_ID.search(str(card))
    replay = card.select_one("a.replay")
    score1, score2 = card.select("div.score")
    return ScheduleMatch(
        match_id=match_id.group(1) if match_id else None,
        start_at=_start_at(card),
        local_time=text_of(card.select_one(".time .pt-1")),
        team1=_team(card.select_one(".team1")),
        team2=_team(card.select_one(".team2")),
        score1=_score(score1),
        score2=_score(score2),
        replay_url=replay.get("href") if replay else None,
    )


def _standing(row: Tag) -> Standing:
    image = row.select_one(".team-logo img")
    match_point, match_wl, net_game_win, game_wl = (text_of(cell) for cell in row.find_all("td", recursive=False)[1:])
    return Standing(
        rank=to_int(text_of(row.select_one(".team-rank"))),
        team=Team(
            name=image.get("alt"),
            full_name=text_of(row.select_one(".team-name .d-none")),
            logo=image.get("src"),
        ),
        match_point=to_int(match_point),
        match_wl=parse_record(match_wl),
        net_game_win=to_int(net_game_win),
        game_wl=parse_record(game_wl),
    )


@ttl_cache(CACHE_SECONDS)
def get_season() -> tuple[list[ScheduleWeek], list[Standing]]:
    """Schedule weeks and standings, both read from one fetch of the schedule page."""
    soup = parse_html(fetch_page(EsportsSourceProvider.get_id_base_url(), "/schedule").text, _SEASON_PARTS)
    weeks = [
        ScheduleWeek(
            week=int(pane["id"].rsplit("-", 1)[1]),
            days=[
                ScheduleDay(label=text_of(date), matches=[_schedule_match(card) for card in date.parent.select(".match:not(.date)")])
                for date in pane.select(".match.date")
            ],
        )
        for pane in soup.find_all(id=_WEEK_ID)
    ]
    standings = [_standing(row) for row in soup.select("#standing-regular-season tbody tr")]
    return weeks, standings


def _asset(image: Tag) -> Asset:
    return Asset(id=image["alt"], image=image["src"])


def _is_item(image: Tag) -> bool:
    return image.get("alt", "").isdigit() and "/emblem/" not in image["src"] and "/rune/" not in image["src"]


def _player(block: Tag) -> Player:
    images = block.find_all("img")
    hero = next(image for image in images if image.get("alt") and not image["alt"].isdigit())
    # Name and hero are the only plain text cells; the KDA and data rows are skipped.
    name = next(
        text_of(cell)
        for cell in block.find_all("div")
        if not cell.find(True) and text_of(cell) and not cell.find_parent(class_=("kda", "data"))
    )
    kills, deaths, assists = (int(part) for part in text_of(block.select_one(".kda-content")).split("/"))
    stats = {
        stat: to_int(text_of(cell))
        for cell in block.select(".data > div")
        for icon, stat in _STAT_BY_ICON.items()
        if icon in cell.find("img")["src"]
    }
    return Player(
        name=name,
        hero=Hero(name=hero["alt"], image=hero["src"]),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=kda_ratio(kills, deaths, assists),
        items=[_asset(image) for image in images if _is_item(image)],
        emblem=next((_asset(image) for image in images if "/emblem/" in image["src"]), None),
        talents=[_asset(image) for image in images if "/rune/" in image["src"]],
        **{stat: stats.get(stat) for stat in _STAT_BY_ICON.values()},
    )


def _game(number: int, pane: Tag) -> Game:
    header = pane.find("div", recursive=False)
    columns = pane.select_one(".row").find_all("div", recursive=False)
    teams = [
        GameTeam(
            team=Team(name=text_of(side.select_one(".mt-0")), logo=side.select_one(".team-logo img")["src"]),
            winner="victory" in side["class"],
            kills=int(re.search(r"\d+", text_of(side.select_one(".pt-4")))[0]),
            stats={},
            players=[_player(block) for block in column.find_all("div", recursive=False)],
        )
        for side, column in zip(header.select(".victory, .defeat"), columns)
    ]
    clock = header.find("img", src=re.compile("clock"))
    return Game(number=number, duration=text_of(clock.parent) if clock else None, teams=teams)


@ttl_cache(CACHE_SECONDS)
def get_match(match_id: int) -> MatchDetailResponse:
    soup = parse_html(fetch_page(EsportsSourceProvider.get_id_base_url(), f"/match-detail/{match_id}").text)
    panes = soup.select(".tab-content.match-detail")
    if not panes:
        raise AppError(status_code=404, code="MATCH_NOT_FOUND", message=f"No match details found for match {match_id}.")
    return MatchDetailResponse(match_id=str(match_id), games=[_game(number, pane) for number, pane in enumerate(panes, start=1)])
