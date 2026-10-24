"""Helpers shared by the league scrapers."""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup
from bs4.element import PageElement, Tag

from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder, request_page
from app.schemas.esports import Record, ScheduleDay, ScheduleResponse, ScheduleWeek

# Upstream responses are parsed (and cached) for five minutes: long enough to absorb
# bursts, short enough for live scores, and well under the six-hour life of the signed
# item-image URLs the Indonesian site hands out.
CACHE_SECONDS = 300

# Series length: first to 2 in the regular season, first to 3 in the playoffs, first to 4 in the grand final.
REGULAR_SEASON_BEST_OF = 3
PLAYOFFS_BEST_OF = 5
GRAND_FINAL_BEST_OF = 7

# Teams at the bottom of the regular season that miss the playoffs.
ID_ELIMINATED = 3
PH_ELIMINATED = 2

# Name the league sites give an undecided playoff side.
TO_BE_DECIDED = "TBD"


def text_of(element: PageElement | None) -> str:
    return element.get_text(" ", strip=True) if element else ""


def attr(element: PageElement | None, name: str) -> str | None:
    """An attribute as one string (``class`` lists are joined with spaces), or None when it is not there."""
    if not isinstance(element, Tag):
        return None
    value = element.get(name)
    if value is None:
        return None
    return value if isinstance(value, str) else " ".join(value)


def _page_changed(what: str) -> AppError:
    return AppError(
        status_code=502,
        code="UPSTREAM_PAGE_CHANGED",
        message=f"The league site returned a page in an unexpected format ({what} not found).",
    )


def need[T](value: T | None, what: str = "an expected value") -> T:
    """``value`` unless it is missing, which means the league site changed its page."""
    if value is None:
        raise _page_changed(what)
    return value


def need_tag(element: PageElement | None, what: str = "an expected element") -> Tag:
    if not isinstance(element, Tag):
        raise _page_changed(what)
    return element


def need_attr(element: PageElement | None, name: str) -> str:
    value = attr(element, name)
    if value is None:
        raise _page_changed(f"the {name!r} attribute")
    return value


def to_int(value: str) -> int:
    """Parse a count that may carry thousands separators (``38.859`` or ``34,946``)."""
    return int(re.sub(r"[.,\s]", "", value))


def parse_record(value: str) -> Record:
    win, lose = (to_int(part) for part in value.split("-", 1))
    return Record(win=win, lose=lose)


_DIV_TAG = re.compile(r"<(/?)div\b")


def balanced_div(html: str, start: int) -> str:
    """The ``<div>`` that opens at ``start``, up to its closing tag, found by counting nested divs.

    The league pages are large (the Indonesian schedule is 2.4 MB, a Philippine match 0.8 MB) and building a
    BeautifulSoup tree of one costs more CPU than a Cloudflare Worker request may use (error 1102), so the
    scrapers slice the parts they need out of the text and parse those with regexes or a small tree.
    """
    depth = 0
    for tag in _DIV_TAG.finditer(html, start):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html[start : html.index(">", tag.start()) + 1]
    raise _page_changed("the end of a block")


def div_block(html: str, marker: str) -> str:
    """The ``<div>`` whose opening tag carries ``marker`` (an id attribute), or "" when the page has none."""
    start = html.find(marker)
    return balanced_div(html, html.rfind("<div", 0, start)) if start >= 0 else ""


def kda_ratio(kills: int, deaths: int, assists: int) -> float:
    return round((kills + assists) / max(deaths, 1), 2)


def fetch_page(base_url: str, path: str) -> httpx.Response:
    return request_page(
        method="GET",
        url=f"{base_url}{path}",
        headers=UpstreamHeaderBuilder.get_esports_header(base_url),
    )


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def select_weeks(weeks: list[ScheduleWeek], week: int | None) -> ScheduleResponse:
    """The whole regular season, or one week of it. Season length varies, so weeks come from the page."""
    if week is None:
        return ScheduleResponse(weeks=weeks)
    chosen = [item for item in weeks if item.week == week]
    if not chosen:
        raise AppError(
            status_code=404,
            code="WEEK_NOT_FOUND",
            message=f"Week {week} is not in the regular season. Available weeks: {', '.join(str(item.week) for item in weeks) or 'none'}.",
        )
    return ScheduleResponse(weeks=chosen)


def mark_grand_final(days: list[ScheduleDay]) -> None:
    """The last match of the playoffs is the grand final, a best of 7."""
    last = next((day.matches[-1] for day in reversed(days) if day.matches), None)
    if last is not None:
        last.best_of = GRAND_FINAL_BEST_OF
