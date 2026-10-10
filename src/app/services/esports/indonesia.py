"""Scraper for the Indonesian league site: schedule, standings and match details."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape

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
    attr,
    fetch_page,
    kda_ratio,
    need,
    need_attr,
    need_tag,
    parse_html,
    parse_record,
    text_of,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

# The per-player "data" row has no labels, only icons; the icon names the figure.
_STAT_BY_ICON = {"sword": "damage_dealt", "shield": "damage_taken", "tower": "tower_damage", "money": "gold"}


def _standing(row: Tag) -> Standing:
    image = row.select_one(".team-logo img")
    match_point, match_wl, net_game_win, game_wl = (text_of(cell) for cell in row.find_all("td", recursive=False)[1:])
    return Standing(
        rank=to_int(text_of(row.select_one(".team-rank"))),
        team=Team(
            name=need_attr(image, "alt"),
            full_name=text_of(row.select_one(".team-name .d-none")),
            logo=attr(image, "src"),
        ),
        match_point=to_int(match_point),
        match_wl=parse_record(match_wl),
        net_game_win=to_int(net_game_win),
        game_wl=parse_record(game_wl),
    )


_WEEK_MARKER = '<div id="t-week-'
_STANDINGS_MARKER = 'id="standing-regular-season"'
_DIV_TAG = re.compile(r"<(/?)div\b")
# Markers in a week pane, in page order: a day heading, or the start of a match card.
_DAY_OR_CARD = re.compile(r'<div class="match (date|position-relative)[^"]*">')
_DAY_LABEL = re.compile(r"\s*(.*?)\s*</div>", re.S)
_TEAM = re.compile(r'class="team team([12])[^"]*"[^>]*>\s*<div class="logo">\s*<img[^>]*?src="([^"]*)"[^>]*>.*?<div class="name">\s*(.*?)\s*</div>', re.S)
_SCORE = re.compile(r'<div class="score[^"]*">\s*(.*?)\s*</div>', re.S)
_PLAY_TIME = re.compile(r'<div class="pt-1"[^>]*>\s*(.*?)\s*</div>', re.S)
_REPLAY_LINK = re.compile(r'<a [^>]*class="[^"]*\breplay\b[^"]*"[^>]*>')
_HREF = re.compile(r'href="([^"]*)"')
_MATCH_ID = re.compile(r"openMatchDetail\((\d+)\)")
_CALENDAR_START = re.compile(r"dates=(\d{8}T\d{6})/")


def _balanced_div(html: str, start: int) -> str:
    """The ``<div>`` that opens at ``start``, up to its closing tag, found by counting nested divs."""
    depth = 0
    for tag in _DIV_TAG.finditer(html, start):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html[start : html.index(">", tag.start()) + 1]
    raise AppError(
        status_code=502,
        code="UPSTREAM_PAGE_CHANGED",
        message="The league site returned a page in an unexpected format (a schedule block does not close).",
    )


def _week_panes(html: str) -> list[tuple[int, str]]:
    """(week number, markup) of each week pane.

    The schedule page is 2.4 MB and mostly pop-ups. Reading it with a DOM parser cost about 2 seconds
    of CPU on a Cloudflare Worker, which is the whole budget (error 1102), so the weeks are read
    straight from the text: each pane runs up to the start of the next one, and only the last
    pane is measured by counting nested divs.
    """
    starts = [(m.start(), int(m[1])) for m in re.finditer(r'<div id="t-week-(\d+)"', html)]
    panes = []
    for index, (start, week) in enumerate(starts):
        panes.append((week, html[start : starts[index + 1][0]] if index + 1 < len(starts) else _balanced_div(html, start)))
    return panes


def _text(value: str) -> str:
    return unescape(" ".join(value.split()))


def _scheduled_match(card: str) -> ScheduleMatch:
    teams = {m[1]: m for m in _TEAM.finditer(card)}
    scores = [_text(m[1]) for m in _SCORE.finditer(card)][:2]
    if "1" not in teams or "2" not in teams or len(scores) != 2:
        raise AppError(
            status_code=502,
            code="UPSTREAM_PAGE_CHANGED",
            message="The league site returned a page in an unexpected format (a match has no teams or scores).",
        )
    match_id = _MATCH_ID.search(card)
    started = _CALENDAR_START.search(card)
    time_box = _PLAY_TIME.search(card)
    replay = _REPLAY_LINK.search(card)
    replay_href = _HREF.search(replay[0]) if replay else None
    return ScheduleMatch(
        match_id=match_id[1] if match_id else None,
        start_at=datetime.strptime(started[1], "%Y%m%dT%H%M%S").replace(tzinfo=UTC).isoformat() if started else None,
        local_time=_text(time_box[1]) if time_box else "",
        team1=Team(name=_text(teams["1"][3]), logo=unescape(teams["1"][2])),
        team2=Team(name=_text(teams["2"][3]), logo=unescape(teams["2"][2])),
        score1=int(scores[0]) if scores[0] else None,
        score2=int(scores[1]) if scores[1] else None,
        replay_url=unescape(replay_href[1]) if replay_href else None,
    )


def _schedule_days(pane: str) -> list[ScheduleDay]:
    markers = list(_DAY_OR_CARD.finditer(pane))
    days: list[ScheduleDay] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(pane)
        if marker[1] == "date":
            label = _DAY_LABEL.match(pane, marker.end())
            days.append(ScheduleDay(label=_text(label[1]) if label else "", matches=[]))
        elif days:
            days[-1].matches.append(_scheduled_match(pane[marker.start() : end]))
    return days


def _standings(html: str) -> list[Standing]:
    start = html.find(_STANDINGS_MARKER)
    if start < 0:
        return []
    block = _balanced_div(html, html.rfind("<div", 0, start))
    return [_standing(row) for row in parse_html(block).select("tbody tr")]


@ttl_cache(CACHE_SECONDS)
def get_season(lang: str) -> tuple[list[ScheduleWeek], list[Standing]]:
    """Schedule weeks and standings, both read from one fetch of the schedule page in ``lang``."""
    html = fetch_page(EsportsSourceProvider.get_id_base_url(), f"/{lang}/schedule").text
    weeks = [ScheduleWeek(week=week, days=_schedule_days(pane)) for week, pane in _week_panes(html)]
    return weeks, _standings(html)


def _asset(image: Tag) -> Asset:
    return Asset(id=need_attr(image, "alt"), image=need_attr(image, "src"))


def _is_item(image: Tag) -> bool:
    source = need_attr(image, "src")
    return (attr(image, "alt") or "").isdigit() and "/emblem/" not in source and "/rune/" not in source


def _player(block: Tag) -> Player:
    images = block.find_all("img")
    hero = next(image for image in images if (alt := attr(image, "alt")) and not alt.isdigit())
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
        if icon in need_attr(cell.find("img"), "src")
    }
    return Player(
        name=name,
        hero=Hero(name=need_attr(hero, "alt"), image=need_attr(hero, "src")),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=kda_ratio(kills, deaths, assists),
        items=[_asset(image) for image in images if _is_item(image)],
        emblem=next((_asset(image) for image in images if "/emblem/" in need_attr(image, "src")), None),
        talents=[_asset(image) for image in images if "/rune/" in need_attr(image, "src")],
        gold=stats.get("gold"),
        damage_dealt=stats.get("damage_dealt"),
        damage_taken=stats.get("damage_taken"),
        tower_damage=stats.get("tower_damage"),
    )


def _game(number: int, pane: Tag) -> Game:
    header = need_tag(pane.find("div", recursive=False), "the game header")
    columns = need_tag(pane.select_one(".row"), "the player columns").find_all("div", recursive=False)
    teams = [
        GameTeam(
            team=Team(name=text_of(side.select_one(".mt-0")), logo=need_attr(side.select_one(".team-logo img"), "src")),
            winner="victory" in (attr(side, "class") or "").split(),
            kills=int(need(re.search(r"\d+", text_of(side.select_one(".pt-4"))), "a team's kills")[0]),
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
