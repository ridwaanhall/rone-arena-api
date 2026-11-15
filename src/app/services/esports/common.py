"""Helpers shared by the league scrapers."""
from __future__ import annotations

import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlsplit

from typing import TYPE_CHECKING

from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder, request_page
from app.schemas.esports import (
    Record,
    ScheduleDay,
    ScheduleResponse,
    ScheduleWeek,
    SocialLink,
    Standing,
    TeamMatch,
    TeamSummary,
)

if TYPE_CHECKING:
    import httpx

# The pages are read with regexes only, never a DOM parser: bs4 at startup pushed the Worker's snapshot over its
# memory limit (error 10021), and imported on first use it ran a fresh Worker copy out of resources (error 1102,
# 1.7.5). Keep heavy, request-only libraries out of module scope.


# Upstream responses are parsed (and cached) for five minutes: long enough to absorb
# bursts, short enough for live scores, and well under the six-hour life of the signed
# item-image URLs the Indonesian site hands out.
CACHE_SECONDS = 300

# Series length: first to 2 in the regular season, first to 3 in the playoffs, first to 4 in the lower bracket
# final and the grand final.
REGULAR_SEASON_BEST_OF = 3
PLAYOFFS_BEST_OF = 5
FINALS_BEST_OF = 7

# Teams at the bottom of the regular season that miss the playoffs.
ID_ELIMINATED = 3
PH_ELIMINATED = 2
# Malaysia: 6 of 8 teams go through (the site marks them). Cambodia: 6 of 10, the format of past seasons; the
# site does not mark the line.
MY_ELIMINATED = 2
KH_ELIMINATED = 4

# Name the league sites give an undecided playoff side.
TO_BE_DECIDED = "TBD"


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
    DOM tree of one costs more CPU than a Cloudflare Worker request may use (error 1102), so the scrapers slice
    the parts they need out of the text and read those with regexes.
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


def mark_finals(days: list[ScheduleDay]) -> None:
    """The lower bracket final and the grand final are best of 7 (both leagues' brackets say so).

    The Indonesian site names each round, so those two are found by name; the Philippine site names none, and
    there they are the last two playoff matches.
    """
    matches = [match for day in days for match in day.matches]
    named = [match for match in matches if _is_final(match.round)]
    for match in named if named else matches[-2:]:
        match.best_of = FINALS_BEST_OF


def _is_final(label: str | None) -> bool:
    name = (label or "").casefold()
    return "grand final" in name or ("lower bracket final" in name and "semi" not in name)


# ---- teams

_HREF = re.compile(r'<a\b[^>]*?\bhref="(https?://[^"]+)"')
_PLATFORM_ALIASES = {"twitter": "x", "fb": "facebook", "youtu": "youtube"}
_STAFF_ROLES = ("coach", "analyst", "manager")


def social_links(markup: str) -> list[SocialLink]:
    """Every link in ``markup``, named after its site (``facebook``, ``instagram``, ``x``...), first of each URL kept."""
    links = []
    for url in dict.fromkeys(unescape(found) for found in _HREF.findall(markup)):
        host = (urlsplit(url).hostname or "").removeprefix("www.").removeprefix("m.")
        name = host.split(".", 1)[0]
        links.append(SocialLink(platform=_PLATFORM_ALIASES.get(name, name), url=url))
    return links


# Each league spells the roles its own way ("Jungle", "Jungler", "MId Lane", "Goldlane", "Asst. Coach"); answers use one set.
_ROLES = (
    (re.compile(r"^(?:asst\.?|assistant)\s*coach$"), "Assistant Coach"),
    (re.compile(r"^(?:head\s*)?coach$"), "Coach"),
    (re.compile(r"^analyst$"), "Analyst"),
    (re.compile(r"^(?:team\s*)?manager$"), "Manager"),
    (re.compile(r"^gold(?:\s*lane(?:r)?)?$"), "Gold Lane"),
    (re.compile(r"^exp(?:\s*lane(?:r)?)?$"), "EXP Lane"),
    (re.compile(r"^mid(?:\s*lane(?:r)?)?$"), "Mid Lane"),
    (re.compile(r"^jungle(?:r)?$"), "Jungle"),
    (re.compile(r"^roam(?:er|ing)?$"), "Roam"),
)


def normalize_role(label: str) -> str:
    """The role in the shared spelling: Gold Lane, EXP Lane, Mid Lane, Jungle, Roam, Coach, Assistant Coach, Analyst."""
    text = " ".join(label.split())
    key = text.casefold()
    return next((role for pattern, role in _ROLES if pattern.match(key)), text)


def is_staff(role: str) -> bool:
    return any(word in role.casefold() for word in _STAFF_ROLES)


def find_team(teams: list[TeamSummary], team_id: str) -> TeamSummary:
    """The team ``team_id`` names, or 404 TEAM_NOT_FOUND listing the league's teams."""
    for team in teams:
        if team.team_id == team_id:
            return team
    raise AppError(
        status_code=404,
        code="TEAM_NOT_FOUND",
        message=f"No team {team_id!r} in this league. Available teams: {', '.join(team.team_id for team in teams) or 'none'}.",
    )


def find_standing(table: list[Standing], name: str) -> Standing | None:
    wanted = name.casefold()
    return next((row for row in table if row.team.name.casefold() == wanted), None)


def team_matches(name: str, weeks: list[ScheduleWeek], playoff_days: list[ScheduleDay]) -> list[TeamMatch]:
    """Every regular-season and playoff match of the team named ``name`` (as the schedule writes it)."""
    wanted = name.casefold()
    found: list[TeamMatch] = []
    stages = [("regular_season", week.week, week.days) for week in weeks] + [("playoffs", None, playoff_days)]
    for stage, week, days in stages:
        for day in days:
            for match in day.matches:
                sides = (match.team1.name.casefold(), match.team2.name.casefold())
                if wanted not in sides:
                    continue
                first = sides[0] == wanted
                result = None
                if match.winner is not None:
                    result = "win" if (match.winner == "team1") == first else "loss"
                found.append(
                    TeamMatch(
                        **match.model_dump(exclude={"status", "winner"}),
                        stage=stage,
                        week=week,
                        day_label=day.label,
                        opponent=match.team2 if first else match.team1,
                        result=result,
                    )
                )
    return found


# ---- statistics tables

_TABLE_TAG = re.compile(r"<!--.*?-->|<[^>]+>", re.S)
_HEADER_CELL = re.compile(r"<th\b[^>]*>(.*?)</th>", re.S)
_BODY_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
_BODY_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
_DECIMAL_COMMA = re.compile(r"^-?\d+,\d{1,2}$")

# Column labels of the player tables, as the leagues write them, and the field each fills.
PLAYER_COLUMNS = {
    "total games": "games",
    "games": "games",
    "total kills": "kills",
    "avg kills": "avg_kills",
    "total deaths": "deaths",
    "avg deaths": "avg_deaths",
    "total assists": "assists",
    "avg assists": "avg_assists",
    "avg kda": "kda",
    "kda ratio": "kda",
    "kill participation": "kill_participation",
}
PLAYER_INT_FIELDS = {"games", "kills", "deaths", "assists"}


def plain_text(markup: str) -> str:
    return unescape(" ".join(_TABLE_TAG.sub(" ", markup).split())).replace("\xa0", " ").strip()


_COMMENT = re.compile(r"<!--.*?-->", re.S)


def strip_comments(markup: str) -> str:
    """Markup without its HTML comments (the leagues comment out whole table columns)."""
    return _COMMENT.sub("", markup)


def tag_attr(markup: str, tag: str, name: str) -> str | None:
    """An attribute of the first ``<tag>`` in ``markup``, unescaped, or None. Attributes may sit in any order and
    across lines."""
    opening = re.search(rf"<{tag}\b[^>]*>", markup)
    if not opening:
        return None
    value = re.search(rf'\s{name}\s*=\s*"([^"]*)"', opening[0])
    return unescape(value[1]) if value else None


def element_text(markup: str, class_fragment: str, start: int = 0) -> str:
    """The text of the first ``<div>`` from ``start`` whose class attribute contains ``class_fragment`` (nested divs
    included), or an empty string."""
    found = re.search(rf'<div\b[^>]*\bclass="[^"]*{class_fragment}[^"]*"', markup[start:])
    return plain_text(balanced_div(markup, start + found.start())) if found else ""


def _class_pattern(token: str) -> re.Pattern[str]:
    return re.compile(rf'<div\b[^>]*?\sclass="(?:[^"]*\s)?{re.escape(token)}(?:\s[^"]*)?"')


def class_blocks(markup: str, token: str) -> list[str]:
    """Every ``<div>`` whose class list holds ``token`` (as a whole word), in page order, each up to its closing tag."""
    return [balanced_div(markup, found.start()) for found in _class_pattern(token).finditer(markup)]


def class_spans(markup: str, token: str) -> list[tuple[int, int]]:
    """(start, end) in ``markup`` of every ``<div>`` whose class list holds ``token``."""
    spans = []
    for found in _class_pattern(token).finditer(markup):
        spans.append((found.start(), found.start() + len(balanced_div(markup, found.start()))))
    return spans


def class_block(markup: str, token: str) -> str:
    """The first ``<div>`` whose class list holds ``token``, or an empty string."""
    found = _class_pattern(token).search(markup)
    return balanced_div(markup, found.start()) if found else ""


def child_divs(block: str) -> list[str]:
    """The ``<div>`` children directly inside ``block`` (itself one ``<div>``), in order."""
    children = []
    depth = 0
    for tag in _DIV_TAG.finditer(block):
        if tag.group(1):
            depth -= 1
        else:
            depth += 1
            if depth == 2:
                children.append(balanced_div(block, tag.start()))
    return children


def table_headers(table: str) -> list[str]:
    # Sortable tables add arrows to each label ("Kills ▲ ▼").
    return [plain_text(cell).replace("▲", "").replace("▼", "").strip().casefold() for cell in _HEADER_CELL.findall(table)]


def table_rows(table: str) -> list[list[str]]:
    """The cells (markup) of each body row."""
    body = table[table.find("<tbody") :] if "<tbody" in table else table
    return [cells for row in _BODY_ROW.findall(body) if (cells := _BODY_CELL.findall(row))]


def stat_int(text: str) -> int | None:
    """A count such as ``3,502,761``, ``843`` or ``-``(none)."""
    digits = re.sub(r"[.,\s]", "", text.strip())
    return int(digits) if re.fullmatch(r"-?\d+", digits) else None


def stat_float(text: str) -> float | None:
    """An average, ratio or percentage: ``2,31`` (decimal comma), ``1.54``, ``78%`` or ``80.71%``; ``-`` is none."""
    value = text.strip().rstrip("%").strip()
    value = value.replace(",", ".") if _DECIMAL_COMMA.match(value) else value.replace(",", "")
    try:
        return float(value)
    except ValueError:
        return None


def player_figures(headers: list[str], cells: list[str]) -> dict[str, int | float | None]:
    """The player-table figures of one row, by field name, from the columns the league labels."""
    figures: dict[str, int | float | None] = {}
    for header, cell in zip(headers, cells):
        field = PLAYER_COLUMNS.get(header)
        if field:
            text = plain_text(cell)
            figures[field] = stat_int(text) if field in PLAYER_INT_FIELDS else stat_float(text)
    return figures


def image_file_key(source: str) -> str:
    """The file name an image URL points at, lower-cased, through any image-proxy wrapping.

    Answers carry images through wsrv.nl in production (``https://wsrv.nl/?url=<encoded URL>``), the league sites
    sometimes wrap them themselves (``https://wsrv.nl?url=https://...``), and tests run unwrapped; matching a team by
    its logo has to see the same file in all three. The resizing prefix some hosts add does not change the name.
    """
    url = unescape(source).strip()
    for _ in range(3):
        wrapped = parse_qs(urlsplit(url).query).get("url")
        if not wrapped or (urlsplit(url).hostname or "").removeprefix("www.") != "wsrv.nl":
            break
        url = wrapped[0]
    return unquote(urlsplit(url).path).rsplit("/", 1)[-1].casefold()
