"""Scraper for the Cambodian league site: schedule, standings, playoffs, teams and players (no game details)."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from html import unescape
from typing import NamedTuple
from urllib.parse import quote, unquote, urlsplit

from app.core import config
from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder, request_page
from app.core.security import EsportsSourceProvider
from app.schemas.esports import (
    Achievement,
    Hero,
    HeroPool,
    HeroPoolsResponse,
    HeroStatistics,
    HeroStatisticsResponse,
    Leaderboard,
    LeaderboardEntry,
    MvpStanding,
    MvpStandingsResponse,
    PlayerPool,
    PlayerPoolsResponse,
    PlayerStatistics,
    PlayerStatisticsResponse,
    PoolHero,
    PoolPlayer,
    TeamStatistics,
    TeamStatisticsResponse,
    PlayerDetailResponse,
    PlayerStats,
    PlayoffSeed,
    PlayoffsResponse,
    RosterMember,
    ScheduleDay,
    ScheduleMatch,
    ScheduleWeek,
    Standing,
    Team,
    TeamDetailResponse,
    TeamHistoryEntry,
    TeamStats,
    TeamSummary,
)
from app.services.esports.common import (
    CACHE_SECONDS,
    KH_ELIMINATED,
    PLAYOFFS_BEST_OF,
    REGULAR_SEASON_BEST_OF,
    TO_BE_DECIDED,
    balanced_div,
    fetch_page,
    find_standing,
    find_team,
    is_staff,
    mark_finals,
    normalize_role,
    parse_record,
    plain_text,
    player_figures,
    stat_float,
    stat_int,
    table_headers,
    table_rows,
    select_weeks,
    team_matches,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

_PHNOM_PENH = timezone(timedelta(hours=7))
_TAG = re.compile(r"<!--.*?-->|<[^>]+>", re.S)

# The site renders its pages with React. A week still being streamed has placeholders under each day heading,
# and the match cards arrive later in the page as hidden blocks that fill those placeholders by id; a week served
# whole (since Nov 2026, once its matches are played) has the cards right under the heading. Both are read. A page
# is about 150 KB; it is read with these patterns, never a parsed tree.
_DAY = re.compile(r'<p class="[^"]*">(\w+day, \d{1,2} \w+ \d{4})</p></div>(?=<div)')
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


# Team logos and player photos live on the league's own image host, whose name would give the source away, so they
# are served through this API instead (``get_image``): the answer carries our address and the file's path only.
# The host resizes on the fly under ``/cdn-cgi/image/<options>/``; that prefix is dropped. Logos sit in ``teams/``
# (they were at the root until Nov 2026), photos in ``players/`` and hero portraits in ``heroes/square/``; other folders
# (role icons, sponsors) are not passed on.
_IMAGE_FILE = re.compile(r"^/(?:cdn-cgi/image/[^/]+/)?((?:(?:teams|players|heroes/square)/)?[^/?#]+\.(?:webp|png|jpe?g))$", re.I)
IMAGE_PATH = "esports/kh/images/"


def _image_host() -> str:
    return f"cdn.{urlsplit(EsportsSourceProvider.get_kh_base_url()).hostname}"


def _logo(source: str) -> str | None:
    source = unescape(source)
    parts = urlsplit(source)
    found = _IMAGE_FILE.search(parts.path)
    if parts.hostname != _image_host():
        return source
    return f"{config.API_URL}{IMAGE_PATH}{quote(unquote(found[1]), safe='/')}" if found else None


@ttl_cache(CACHE_SECONDS)
def get_image(name: str) -> tuple[bytes, str]:
    """A team logo or player photo from the league's image host: (bytes, content type)."""
    base_url = EsportsSourceProvider.get_kh_base_url()
    response = request_page(
        method="GET",
        url=f"https://{_image_host()}/{quote(unquote(name), safe='/')}",
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


def _children(block: str) -> list[str]:
    """The ``<div>`` children of a ``<div>`` block, in order."""
    inner = block[block.index(">") + 1 : block.rindex("</div>")]
    children = []
    start = inner.find("<div")
    while start >= 0:
        child = balanced_div(inner, start)
        children.append(child)
        start = inner.find("<div", start + len(child))
    return children


def _days(html: str, best_of: int) -> list[ScheduleDay]:
    segments = dict(_SEGMENT.findall(html))
    days = []
    for number, found in enumerate(_DAY.finditer(html), start=1):
        label = found[1]
        block = balanced_div(html, found.end())
        keys = _PLACEHOLDER.findall(block)
        cards = [segments[key] for key in keys if key in segments] if keys else _children(block)
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


class _TeamsPage(NamedTuple):
    standings: list[Standing]
    teams: list[TeamSummary]


_TEAM_CARD = re.compile(r'<a class="group block[^"]*" href="/teams/([\w-]+)">.*?<img alt="([^"]*)"[^>]*?src="([^"]*)"', re.S)


@ttl_cache(CACHE_SECONDS)
def _teams_page() -> _TeamsPage:
    """The standings table and the team cards, both from one fetch of the teams page."""
    html = fetch_page(EsportsSourceProvider.get_kh_base_url(), "/teams").text
    standings = _standings(html)
    # The cards name each team in full; the schedule and standings use the short name, matched by the full one.
    short = {(row.team.full_name or "").casefold(): row.team.name for row in standings}
    teams: dict[str, TeamSummary] = {}
    for team_id, full_name, logo in _TEAM_CARD.findall(html):
        full_name = unescape(full_name)
        teams.setdefault(
            team_id,
            TeamSummary(team_id=team_id, name=short.get(full_name.casefold(), full_name), full_name=full_name, logo=_logo(logo)),
        )
    return _TeamsPage(standings, list(teams.values()))


def get_standings() -> list[Standing]:
    return _teams_page().standings


def get_teams() -> list[TeamSummary]:
    return _teams_page().teams


def _standings(html: str) -> list[Standing]:
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


# ---- team and player pages (about 130 KB and 100 KB of streamed markup, read with patterns)

_MEMBER = re.compile(
    r'<a class="grad-gold-purple[^"]*" href="/players/([\w-]+)">.*?<p class="[^"]*">([^<]*)</p><p class="[^"]*">([^<]*)</p>'
    r'.*?<img alt="[^"]*"[^>]*?src="([^"]*players/[^"]*)"',
    re.S,
)
_HEADER_LOGO = re.compile(r'<img alt="([^"]*)"[^>]*?src="([^"]*)"/><h1[^>]*>(.*?)</h1>', re.S)
_STATS_BLOCK = re.compile(r"<h3[^>]*>([^<]*)</h3><dl>(.*?)</dl>", re.S)
_STAT = re.compile(r"<dt[^>]*>(.*?)</dt><dd[^>]*>(.*?)</dd>", re.S)
_FACT = re.compile(r'<div class="flex min-w-0 flex-col gap-1"><span[^>]*>(.*?)</span><span[^>]*>(.*?)</span></div>', re.S)
_RICH_TEXT = re.compile(r'<div class="payload-richtext">(.*?)</div>', re.S)
_ACHIEVEMENT_HEADING = re.compile(r"<h\d[^>]*>\s*Achievements?\s*:?\s*</h\d>", re.I)
_LIST_ITEM = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S)
_ACHIEVEMENT = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})?\s*"
    r"(?P<place>\d+\s*(?:st|nd|rd|th)(?:\s*-\s*\d+\s*(?:st|nd|rd|th))?)\s*"
    r"(?P<tier>[A-Z]-Tier)?\s*(?P<title>.*?)\s*(?:\$(?P<prize>[\d,.]+))?\s*$",
    re.I,
)
_ORDINAL = re.compile(r"(\d+)\s*(?:st|nd|rd|th)", re.I)
_HISTORY = re.compile(r'<li class="[^"]*">(?:<a [^>]*href="/teams/([\w-]+)"[^>]*>|<span[^>]*>)([^<]*)</(?:a|span)><span[^>]*>(.*?)</span></li>', re.S)

_TEAM_STAT_FIELDS = {
    "match played": "matches_played",
    "game played": "games_played",
    "kills": "kills",
    "gold": "gold",
    "damage": "damage",
    "lord": "lord",
    "tortoise": "tortoise",
    "tower": "tower",
}
_PLAYER_STAT_FIELDS = {
    "hero played": "heroes_played",
    "mvp points": "mvp_points",
    "match played": "matches_played",
    "game played": "games_played",
    "kills": "kills",
    "assists": "assists",
    "gold earned": "gold",
    "gold / min": "gold_per_min",
    "damage dealt": "damage_dealt",
    "damage taken": "damage_taken",
    "damage to turrets": "tower_damage",
}


def _section(html: str, marker: str) -> str:
    """The ``<section>`` whose opening tag carries ``marker``, or "" (sections do not nest on these pages)."""
    start = html.find(marker)
    return html[start : html.find("</section>", start)] if start >= 0 else ""


def _label(text: str) -> str:
    return "Career" if text.strip().casefold() == "career stats" else text.strip()


def _figures(block: str) -> dict[str, str]:
    return {_text(label).casefold(): _text(value) for label, value in _STAT.findall(block)}


def _team_stats(html: str) -> list[TeamStats]:
    stats = []
    for label, block in _STATS_BLOCK.findall(_section(html, 'id="statistics"')):
        figures = _figures(block)
        values = {field: to_int(figures[key]) for key, field in _TEAM_STAT_FIELDS.items() if figures.get(key, "").replace(",", "").isdigit()}
        rate = re.match(r"([\d.]+)\s*%", figures.get("win rate", ""))
        stats.append(
            TeamStats(
                label=_label(_text(label)),
                match_wl=parse_record(figures["match w-l"]) if re.fullmatch(r"\d+-\d+", figures.get("match w-l", "")) else None,
                game_wl=parse_record(figures["game w-l"]) if re.fullmatch(r"\d+-\d+", figures.get("game w-l", "")) else None,
                win_rate=float(rate[1]) if rate else None,
                **values,
            )
        )
    return stats


def _ordinal(match: re.Match[str]) -> str:
    number = int(match[1])
    suffix = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _achievement(item: str) -> Achievement | None:
    # The list is typed by hand: words can run together ("2ndA-TierMPL") and placements be misspelt ("4 st").
    text = unescape(" ".join(_TAG.sub("", item).split()))
    if not text:
        return None
    found = _ACHIEVEMENT.match(text)
    if not found or not found["title"]:
        return Achievement(title=text)
    return Achievement(
        title=found["title"],
        placement=_ORDINAL.sub(_ordinal, re.sub(r"\s*-\s*", " - ", found["place"])),
        date=found["date"],
        tier=found["tier"],
        prize=f"${found['prize']}" if found["prize"] else None,
    )


def _facts(section: str) -> dict[str, str]:
    """The labelled facts of a profile ("Region", "Owner"...), keyed in snake case."""
    return {
        re.sub(r"\W+", "_", _text(label).casefold()).strip("_"): _text(value)
        for label, value in _FACT.findall(section)
        if _text(value)
    }


def _member(player_id: str, name: str, role: str, photo: str) -> RosterMember:
    return RosterMember(player_id=player_id, name=unescape(name).strip(), role=normalize_role(unescape(role)), photo=_logo(photo))


@ttl_cache(CACHE_SECONDS)
def get_team(team_id: str) -> TeamDetailResponse:
    team = find_team(get_teams(), team_id)
    html = fetch_page(EsportsSourceProvider.get_kh_base_url(), f"/teams/{team_id}").text
    members = [_member(*found) for found in _MEMBER.findall(_section(html, 'id="members"') or html)]
    profile = _section(html, 'id="profile"')
    facts = _facts(profile)
    facts.pop("team_name", None)
    rich = _RICH_TEXT.search(profile)
    description, achievements = "", []
    if rich:
        heading = _ACHIEVEMENT_HEADING.search(rich[1])
        description = _text(rich[1][: heading.start()] if heading else rich[1])
        if heading:
            achievements = [found for item in _LIST_ITEM.findall(rich[1][heading.end() :]) if (found := _achievement(item))]
    header = _HEADER_LOGO.search(html)
    stats = _team_stats(html)
    # The season's block is labelled "MPL KH S11".
    season = next((found for block in stats if (found := re.search(r"\bS(\d+)\b", block.label))), None)
    schedule = get_schedule()
    playoffs = get_playoffs()
    return TeamDetailResponse(
        team_id=team_id,
        name=team.name,
        full_name=_text(header[3]) if header else team.full_name,
        logo=_logo(header[2]) if header else team.logo,
        season=int(season[1]) if season else None,
        description=description or None,
        achievements=achievements,
        profile=facts,
        stats=stats,
        players=[member for member in members if not is_staff(member.role)],
        staff=[member for member in members if is_staff(member.role)],
        standing=find_standing(get_standings(), team.name),
        matches=team_matches(team.name, schedule, playoffs.days),
    )


_PLAYER_HEADER = re.compile(r'<h1[^>]*>(.*?)</h1><p[^>]*>(.*?)</p>', re.S)
_PLAYER_PHOTO = re.compile(r'<img alt="[^"]*"[^>]*?src="([^"]*players/[^"]*)"')
_PLAYER_TEAM = re.compile(r'<a aria-label="[^"]*" class="[^"]*" href="/teams/([\w-]+)">')


@ttl_cache(CACHE_SECONDS)
def get_player(player_id: str) -> PlayerDetailResponse:
    try:
        html = fetch_page(EsportsSourceProvider.get_kh_base_url(), f"/players/{player_id}").text
    except AppError as error:
        if error.status_code in (404, 500):
            raise _player_not_found(player_id) from error
        raise
    header = _PLAYER_HEADER.search(html)
    if not header:
        raise _player_not_found(player_id)
    photo = _PLAYER_PHOTO.search(html)
    current = _PLAYER_TEAM.search(html)
    team = next((item for item in get_teams() if current and item.team_id == current[1]), None)
    biography = _section(html, 'id="biography"')
    stats = []
    for label, block in _STATS_BLOCK.findall(_section(html, 'id="statistics"')):
        figures = _figures(block)
        values = {field: to_int(figures[key]) for key, field in _PLAYER_STAT_FIELDS.items() if figures.get(key, "").replace(",", "").isdigit()}
        stats.append(PlayerStats(label=_label(_text(label)), **values))
    history_start = html.find(">Team History</h2>")
    history = html[history_start : html.find("</section>", history_start)] if history_start >= 0 else ""
    return PlayerDetailResponse(
        player_id=player_id,
        name=_text(header[1]),
        role=normalize_role(_text(header[2])),
        photo=_logo(photo[1]) if photo else None,
        team=team,
        profile=_facts(biography),
        team_history=[
            TeamHistoryEntry(team_id=linked or None, name=unescape(name).strip(), period=_text(period) or None)
            for linked, name, period in _HISTORY.findall(history)
        ],
        stats=stats,
    )


def _player_not_found(player_id: str) -> AppError:
    return AppError(status_code=404, code="PLAYER_NOT_FOUND", message=f"No player {player_id!r} in this league.")


# ---- season statistics: one page per tab (``/statistics?tab=...``), the same six sections as the Indonesian league.
# The pool tabs are about 0.9 MB each, so every tab is read with patterns only.

_STAT_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_IMAGE = re.compile(r'<img alt="([^"]*)"[^>]*?src="([^"]*)"')
_SPAN_TEXT = re.compile(r"<span[^>]*>([^<]*)</span>")
_BOARD = re.compile(r"<h3[^>]*>(Top 5[^<]*)</h3>")
_BOARD_PLAYER = re.compile(
    r'<img alt=""[^>]*?src="([^"]*)"/><img alt="([^"]*)"[^>]*?src="([^"]*)"/><span[^>]*>([^<]*)</span></div><div[^>]*>([^<]*)</div>'
)
_BOARD_HERO = re.compile(r'<img alt="([^"]*)"[^>]*?src="([^"]*heroes/[^"]*)"/><span[^>]*>([^<]*)</span></div><div[^>]*>([^<]*)</div>')
_POOL_ENTRY = re.compile(r'<span[^>]*title="([^"]*)"><span[^>]*><img alt="[^"]*"[^>]*?src="([^"]*)"/><span[^>]*>(\d+)</span></span><span[^>]*>(.*?)</span></span>', re.S)
_MVP_CARD = re.compile(
    r'<img alt=""[^>]*?src="([^"]*)"/><img alt="[^"]*"[^>]*?src="([^"]*)"/><span[^>]*>(\d+)(?:<!-- -->|\s)*PTS</span>'
    r'<span[^>]*>#(?:<!-- -->)?(\d+)</span></div><div[^>]*>(.*?)</div>',
    re.S,
)
_STAT_TEAM_FIGURES = ("kills", "deaths", "assists", "gold", "damage", "lord", "tortoise", "tower")


def _statistics_page(tab: str) -> str:
    return fetch_page(EsportsSourceProvider.get_kh_base_url(), f"/statistics?tab={tab}").text


def _first_table(html: str) -> str:
    table = _STAT_TABLE.search(html)
    return table[0] if table else ""


def _file_key(source: str) -> str:
    return unquote(urlsplit(unescape(source)).path).rsplit("/", 1)[-1].casefold()


def _team_by_logo(source: str) -> Team | None:
    """The team whose logo file is ``source``'s (the pages size the same logo differently)."""
    key = _file_key(source)
    for team in get_teams():
        if team.logo and _file_key(team.logo) == key:
            return Team(name=team.name, full_name=team.full_name, logo=team.logo)
    return None


def _stat_hero(name: str, image: str) -> Hero:
    return Hero(name=unescape(name).strip(), image=_logo(image))


def _stat_boards(html: str) -> list[Leaderboard]:
    headings = list(_BOARD.finditer(html))
    boards = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else html.find("<table", heading.end())
        block = html[heading.end() : end if end >= 0 else len(html)]
        players = _BOARD_PLAYER.findall(block)
        if players:
            entries = [
                LeaderboardEntry(rank=rank, name=_text(name), team=_team_by_logo(logo), photo=_logo(photo), value=stat_float(_text(value)) or 0)
                for rank, (logo, _, photo, value, name) in enumerate(players, start=1)
            ]
        else:
            entries = [
                LeaderboardEntry(rank=rank, name=_text(name), hero=_stat_hero(alt, image), value=stat_float(_text(value)) or 0)
                for rank, (alt, image, value, name) in enumerate(_BOARD_HERO.findall(block), start=1)
            ]
        boards.append(Leaderboard(title=_text(heading[1]), entries=entries))
    return boards


@ttl_cache(CACHE_SECONDS)
def get_team_statistics() -> TeamStatisticsResponse:
    rows = []
    for cells in table_rows(_first_table(_statistics_page("teams"))):
        image = _IMAGE.search(cells[0])
        names = [_text(name) for name in _SPAN_TEXT.findall(cells[0])]
        team = (_team_by_logo(image[2]) if image else None) or Team(
            name=names[0] if names else plain_text(cells[0]), full_name=names[1] if len(names) > 1 else None, logo=_logo(image[2]) if image else None
        )
        rows.append(TeamStatistics(team=team, **dict(zip(_STAT_TEAM_FIGURES, (stat_int(plain_text(cell)) for cell in cells[1:])))))
    return TeamStatisticsResponse(teams=rows)


@ttl_cache(CACHE_SECONDS)
def get_player_statistics() -> PlayerStatisticsResponse:
    html = _statistics_page("players")
    table = _first_table(html)
    headers = table_headers(table)
    players = []
    for cells in table_rows(table):
        images = _IMAGE.findall(cells[0])
        players.append(
            PlayerStatistics(
                name=plain_text(cells[0]),
                # The row's first image is the team logo, named by its short name.
                team=_team_by_logo(images[0][1]) if images else None,
                role=normalize_role(plain_text(cells[1])) or None if "lane" in headers else None,
                **player_figures(headers, cells),
            )
        )
    return PlayerStatisticsResponse(leaderboards=_stat_boards(html), players=players)


@ttl_cache(CACHE_SECONDS)
def get_hero_statistics() -> HeroStatisticsResponse:
    html = _statistics_page("heroes")
    heroes = []
    for cells in table_rows(_first_table(html)):
        image = _IMAGE.search(cells[0])
        picks, bans, wins = (stat_int(plain_text(cell)) or 0 for cell in cells[1:4])
        heroes.append(
            HeroStatistics(
                hero=_stat_hero(image[1], image[2]) if image else Hero(name=plain_text(cells[0])),
                picks=picks,
                bans=bans,
                wins=wins,
                win_rate=stat_float(plain_text(cells[4])) if len(cells) > 4 else None,
            )
        )
    return HeroStatisticsResponse(leaderboards=_stat_boards(html), heroes=heroes)


@ttl_cache(CACHE_SECONDS)
def get_hero_pools() -> HeroPoolsResponse:
    pools = []
    for cells in table_rows(_first_table(_statistics_page("hero-pools"))):
        logo = _IMAGE.search(cells[0])
        pools.append(
            HeroPool(
                name=plain_text(cells[0]),
                team=_team_by_logo(logo[2]) if logo else None,
                role=normalize_role(plain_text(cells[1])) or None,
                total=stat_int(plain_text(cells[2])) or 0,
                heroes=[
                    PoolHero(hero=_stat_hero(name, image), picks=int(picks), win_rate=stat_float(_text(rate)))
                    for name, image, picks, rate in _POOL_ENTRY.findall(cells[3])
                ],
            )
        )
    return HeroPoolsResponse(players=pools)


@ttl_cache(CACHE_SECONDS)
def get_player_pools() -> PlayerPoolsResponse:
    # A pool names the player only; the team comes from the player table.
    teams = {player.name.casefold(): player.team for player in get_player_statistics().players}
    pools = []
    for cells in table_rows(_first_table(_statistics_page("player-pools"))):
        image = _IMAGE.search(cells[0])
        name = plain_text(cells[0])
        players = [
            PoolPlayer(name=unescape(player).strip(), team=teams.get(unescape(player).strip().casefold()), photo=_logo(photo), picks=int(picks), win_rate=stat_float(_text(rate)))
            for player, photo, picks, rate in _POOL_ENTRY.findall(cells[2])
        ]
        pools.append(PlayerPool(hero=_stat_hero(image[1] or name, image[2]) if image else Hero(name=name), total=stat_int(plain_text(cells[1])) or 0, players=players))
    return PlayerPoolsResponse(heroes=pools)


@ttl_cache(CACHE_SECONDS)
def get_mvp_standings() -> MvpStandingsResponse:
    standings = []
    for logo, photo, points, rank, name in _MVP_CARD.findall(_statistics_page("mvp")):
        team = _team_by_logo(logo)
        name = _text(name)
        # The card names the player after the team's short name ("VGR Vincen6").
        if team and name.casefold().startswith(f"{team.name.casefold()} "):
            name = name[len(team.name) + 1 :]
        standings.append(MvpStanding(rank=int(rank), name=name, team=team, photo=_logo(photo), points=int(points)))
    return MvpStandingsResponse(standings=standings)
