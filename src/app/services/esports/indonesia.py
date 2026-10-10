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
_PANE_START = re.compile(r'<div\b[^>]*\bid="(?:t-week-\d+|standing-regular-season)"')
_DIV_TAG = re.compile(r"<(/?)div\b")
_BETWEEN_TAGS = re.compile(r">\s+<")
_MATCH_ID = re.compile(r"openMatchDetail\((\d+)\)")
_CALENDAR_START = re.compile(r"dates=(\d{8}T\d{6})/")
# The per-player "data" row has no labels, only icons; the icon names the figure.
_STAT_BY_ICON = {"sword": "damage_dealt", "shield": "damage_taken", "tower": "tower_damage", "money": "gold"}


def _team(element: Tag) -> Team:
    image = element.find("img")
    return Team(name=text_of(element.find(class_="name")), logo=image.get("src") if image else None)


def _score(element: Tag) -> int | None:
    value = text_of(element)
    return int(value) if value else None


def _start_at(calendar_href: str | None) -> str | None:
    found = _CALENDAR_START.search(calendar_href) if calendar_href else None
    if not found:
        return None
    return datetime.strptime(found.group(1), "%Y%m%dT%H%M%S").replace(tzinfo=UTC).isoformat()


def _schedule_match(card: Tag) -> ScheduleMatch:
    # One walk over the card's tags, taking the first of each kind. Separate find() calls cost
    # about ten walks per match, and CPU time is what the Cloudflare Worker is short of.
    opener = calendar = replay = time_box = team1 = team2 = None
    scores: list[Tag] = []
    for tag in card.find_all(True):
        classes = tag.get("class") or ()
        if tag.name == "a":
            if opener is None and _MATCH_ID.search(tag.get("onclick", "")):
                opener = tag
            if calendar is None and _CALENDAR_START.search(tag.get("href", "")):
                calendar = tag
            if replay is None and "replay" in classes:
                replay = tag
        elif tag.name == "div" and "score" in classes:
            scores.append(tag)
        if "time" in classes and time_box is None:
            time_box = tag
        if "team1" in classes and team1 is None:
            team1 = tag
        if "team2" in classes and team2 is None:
            team2 = tag
    match_id = _MATCH_ID.search(opener["onclick"]) if opener else None
    score1, score2 = scores
    return ScheduleMatch(
        match_id=match_id.group(1) if match_id else None,
        start_at=_start_at(calendar["href"] if calendar else None),
        local_time=text_of(time_box.find(class_="pt-1") if time_box else None),
        team1=_team(team1),
        team2=_team(team2),
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


def _season_panes(html: str) -> str:
    """The week panes and the standings table cut out of the page, as one small document.

    The schedule page is about 2.4 MB and most of it (match pop-ups and the like) is not read.
    Parsing is the cost that matters on a Cloudflare Worker, so each wanted ``<div>`` is cut out
    by counting its nested divs and only those pieces are parsed. If a pane is not closed
    properly the whole page is returned, which is slower but gives the same result.
    """
    panes: list[str] = []
    for start in _PANE_START.finditer(html):
        depth = 0
        for tag in _DIV_TAG.finditer(html, start.start()):
            depth += -1 if tag.group(1) else 1
            if depth == 0:
                panes.append(html[start.start() : html.index(">", tag.start()) + 1])
                break
        else:
            return html
    if not panes:
        return html
    # Half of the markup is indentation; dropping the blanks between tags saves the parser a text node for each.
    return _BETWEEN_TAGS.sub("><", "".join(panes))


@ttl_cache(CACHE_SECONDS)
def get_season(lang: str) -> tuple[list[ScheduleWeek], list[Standing]]:
    """Schedule weeks and standings, both read from one fetch of the schedule page in ``lang``."""
    soup = parse_html(_season_panes(fetch_page(EsportsSourceProvider.get_id_base_url(), f"/{lang}/schedule").text))
    weeks = [
        ScheduleWeek(
            week=int(pane["id"].rsplit("-", 1)[1]),
            days=[
                ScheduleDay(
                    label=text_of(date),
                    matches=[_schedule_match(card) for card in date.parent.find_all(class_="match") if "date" not in card["class"]],
                )
                for date in pane.find_all(class_="match") if "date" in date["class"]
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
