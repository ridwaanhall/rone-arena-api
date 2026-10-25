"""Scraper for the Cambodian league site: schedule, standings and playoffs (the site publishes no game details)."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from html import unescape
from urllib.parse import quote, unquote, urlsplit

from app.core import config
from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder, request_page
from app.core.security import EsportsSourceProvider
from app.schemas.esports import PlayoffSeed, PlayoffsResponse, ScheduleDay, ScheduleMatch, ScheduleWeek, Standing, Team
from app.services.esports.common import (
    CACHE_SECONDS,
    KH_ELIMINATED,
    PLAYOFFS_BEST_OF,
    REGULAR_SEASON_BEST_OF,
    TO_BE_DECIDED,
    fetch_page,
    mark_finals,
    parse_record,
    select_weeks,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

_PHNOM_PENH = timezone(timedelta(hours=7))
_TAG = re.compile(r"<!--.*?-->|<[^>]+>", re.S)

# The site streams its pages (React server rendering): each day heading is followed by placeholders, and the
# match cards arrive later in the page as hidden blocks that fill those placeholders by id. A page is about
# 150 KB; it is read with these patterns, never a parsed tree.
_DAY = re.compile(r'<p class="[^"]*">(\w+day, \d{1,2} \w+ \d{4})</p></div><div[^>]*>((?:<template id="P:\w+"></template>)+)')
_PLACEHOLDER = re.compile(r'<template id="P:(\w+)"></template>')
_SEGMENT = re.compile(r'<div hidden id="S:(\w+)">(.*?)</div><script', re.S)
_SIDE = re.compile(r'<img alt="([^"]*)"[^>]*?src="([^"]*)"/><span[^>]*>([^<]*)</span>')
_MIDDLE = re.compile(r'</span></div><div[^>]*>((?:<span[^>]*>[^<]*</span>)+)</div><div')
_SPAN = re.compile(r"<span[^>]*>([^<]*)</span>")
_TIME = re.compile(r"^\d{1,2}:\d{2}$")
_VIDEO = re.compile(r'<a href="(https://(?:www\.)?youtu[^"]*)"')
_WEEK_LINK = re.compile(r'href="/schedule\?stage=regular&amp;week=(\d+)"')

_STANDINGS_HEADING = "STANDINGS</h2>"
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
_LOGO = re.compile(r'<img alt="([^"]*)"[^>]*?src="([^"]*)"')


def _text(markup: str) -> str:
    return unescape(" ".join(_TAG.sub(" ", markup).split()))


def _page_changed(what: str) -> AppError:
    return AppError(
        status_code=502,
        code="UPSTREAM_PAGE_CHANGED",
        message=f"The league site returned a page in an unexpected format ({what} not found).",
    )


# Team logos live on the league's own image host, whose name would give the source away, so they are served
# through this API instead (``get_image``): the answer carries our address and the file name only.
_IMAGE_FILE = re.compile(r"/([^/?#]+\.(?:webp|png|jpe?g))$", re.I)
IMAGE_PATH = "esports/kh/images/"


def _image_host() -> str:
    return f"cdn.{urlsplit(EsportsSourceProvider.get_kh_base_url()).hostname}"


def _logo(source: str) -> str | None:
    source = unescape(source)
    parts = urlsplit(source)
    found = _IMAGE_FILE.search(parts.path)
    if parts.hostname != _image_host():
        return source
    return f"{config.API_URL}{IMAGE_PATH}{found[1]}" if found else None


@ttl_cache(CACHE_SECONDS)
def get_image(name: str) -> tuple[bytes, str]:
    """A team logo from the league's image host: (bytes, content type)."""
    base_url = EsportsSourceProvider.get_kh_base_url()
    response = request_page(
        method="GET",
        url=f"https://{_image_host()}/{quote(unquote(name), safe='')}",
        headers=UpstreamHeaderBuilder.get_esports_header(base_url),
    )
    return response.content, response.headers.get("content-type", "image/webp")


def _team(full_name: str, logo: str, name: str) -> Team:
    name = _text(name)
    return Team(name=name, full_name=unescape(full_name) or None, logo=None if name == TO_BE_DECIDED else _logo(logo))


def _start_at(label: str, local_time: str) -> str | None:
    try:
        started = datetime.strptime(f"{label} {local_time}", "%A, %d %B %Y %H:%M")
    except ValueError:
        return None
    return started.replace(tzinfo=_PHNOM_PENH).astimezone(UTC).isoformat()


def _match(card: str, label: str, best_of: int) -> ScheduleMatch:
    sides = _SIDE.findall(card)[:2]
    if len(sides) != 2:
        raise _page_changed("a match's teams")
    middle = _MIDDLE.search(card)
    # Played: score, time, score. Upcoming: the time, or LIVE while it is on.
    parts = [_text(part) for part in _SPAN.findall(middle[1])] if middle else []
    local_time = next((part for part in parts if _TIME.match(part)), "")
    scores = [part for part in parts if part.isdigit()]
    played = len(parts) == 3 and len(scores) == 2
    video = _VIDEO.search(card)
    return ScheduleMatch(
        match_id=None,
        start_at=_start_at(label, local_time) if local_time else None,
        local_time=local_time,
        team1=_team(*sides[0]),
        team2=_team(*sides[1]),
        score1=int(scores[0]) if played else None,
        score2=int(scores[1]) if played else None,
        replay_url=unescape(video[1]).strip() if video else None,
        best_of=best_of,
    )


def _days(html: str, best_of: int) -> list[ScheduleDay]:
    segments = dict(_SEGMENT.findall(html))
    days = []
    for number, (label, placeholders) in enumerate(_DAY.findall(html), start=1):
        cards = [segments[key] for key in _PLACEHOLDER.findall(placeholders) if key in segments]
        days.append(ScheduleDay(day=number, label=label, matches=[_match(card, label, best_of) for card in cards]))
    return days


def _schedule_page(query: str) -> str:
    return fetch_page(EsportsSourceProvider.get_kh_base_url(), f"/schedule?{query}").text


@ttl_cache(CACHE_SECONDS)
def _week(week: int) -> tuple[list[ScheduleDay], list[int]]:
    """One week's days, and the season's week numbers as the page lists them."""
    html = _schedule_page(f"stage=regular&week={week}")
    weeks = sorted({int(found) for found in _WEEK_LINK.findall(html)})
    return _days(html, REGULAR_SEASON_BEST_OF), weeks


def get_schedule(week: int | None = None) -> list[ScheduleWeek]:
    """The whole regular season (one page per week, each cached), or the one week asked for."""
    weeks = _week(1)[1]
    if week is not None and week not in weeks:
        # Raises WEEK_NOT_FOUND with the weeks the season has.
        return select_weeks([ScheduleWeek(week=number, days=[]) for number in weeks], week).weeks
    chosen = [week] if week is not None else weeks
    # A week the season does not have is never fetched; the router answers it with WEEK_NOT_FOUND.
    return [ScheduleWeek(week=number, days=_week(number)[0]) for number in chosen if number in weeks]


@ttl_cache(CACHE_SECONDS)
def get_standings() -> list[Standing]:
    html = fetch_page(EsportsSourceProvider.get_kh_base_url(), "/teams").text
    start = html.find(_STANDINGS_HEADING)
    if start < 0:
        raise _page_changed("the standings table")
    body = html[html.find("<tbody", start) : html.find("</tbody>", start)]
    table = []
    for row in _ROW.findall(body):
        cells = _CELL.findall(row)
        logo = _LOGO.search(cells[0])
        spans = _SPAN.findall(cells[0])
        if not logo or len(spans) < 2:
            raise _page_changed("a standings row")
        match_point, match_wl, net, game_wl = (_text(cell) for cell in cells[1:5])
        table.append(
            Standing(
                rank=to_int(spans[0]),
                team=Team(name=_text(spans[-1]), full_name=unescape(logo[1]), logo=_logo(logo[2])),
                match_point=to_int(match_point),
                match_wl=parse_record(match_wl),
                net_game_win=int(net.replace("+", "")),
                game_wl=parse_record(game_wl),
            )
        )
    return table


@ttl_cache(CACHE_SECONDS)
def get_playoffs() -> PlayoffsResponse:
    days = [day for day in _days(_schedule_page("stage=playoffs"), PLAYOFFS_BEST_OF) if day.matches]
    mark_finals(days)
    table = get_standings()
    return PlayoffsResponse(
        bracket_image=None,
        seeds=[PlayoffSeed(seed=row.rank, team=row.team, match_wl=row.match_wl) for row in table[: len(table) - KH_ELIMINATED]],
        days=days,
    )
