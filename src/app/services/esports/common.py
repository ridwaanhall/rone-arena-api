"""Helpers shared by the league scrapers."""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup, SoupStrainer
from bs4.element import Tag

from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder, request_page
from app.schemas.esports import Record, ScheduleResponse, ScheduleWeek

# Upstream responses are parsed (and cached) for five minutes: long enough to absorb
# bursts, short enough for live scores, and well under the six-hour life of the signed
# item-image URLs the Indonesian site hands out.
CACHE_SECONDS = 300


def text_of(element: Tag | None) -> str:
    return element.get_text(" ", strip=True) if element else ""


def to_int(value: str) -> int:
    """Parse a count that may carry thousands separators (``38.859`` or ``34,946``)."""
    return int(re.sub(r"[.,\s]", "", value))


def parse_record(value: str) -> Record:
    win, lose = (to_int(part) for part in value.split("-", 1))
    return Record(win=win, lose=lose)


def kda_ratio(kills: int, deaths: int, assists: int) -> float:
    return round((kills + assists) / max(deaths, 1), 2)


def fetch_page(base_url: str, path: str) -> httpx.Response:
    return request_page(
        method="GET",
        url=f"{base_url}{path}",
        headers=UpstreamHeaderBuilder.get_esports_header(base_url),
    )


def parse_html(html: str, parse_only: SoupStrainer | None = None) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser", parse_only=parse_only)


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
