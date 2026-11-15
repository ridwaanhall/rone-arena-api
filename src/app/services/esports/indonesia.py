"""Scraper for the Indonesian league site: schedule, standings, match details and teams."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import quote, unquote, urlsplit

from app.core import config
from app.core.exceptions import AppError
from app.core.http import UpstreamHeaderBuilder, request_page
from app.core.security import EsportsSourceProvider
from app.schemas.esports import (
    Asset,
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
    Game,
    GameTeam,
    Hero,
    MatchDetailResponse,
    PlayoffSeed,
    PlayoffsResponse,
    Player,
    RosterMember,
    ScheduleDay,
    ScheduleMatch,
    ScheduleWeek,
    Standing,
    Team,
    TeamDetailResponse,
    TeamSummary,
)
from app.services.esports.common import (
    CACHE_SECONDS,
    PLAYOFFS_BEST_OF,
    REGULAR_SEASON_BEST_OF,
    TO_BE_DECIDED,
    attr,
    balanced_div,
    div_block,
    fetch_page,
    find_standing,
    find_team,
    is_staff,
    kda_ratio,
    mark_finals,
    need,
    need_attr,
    need_tag,
    normalize_role,
    parse_html,
    parse_record,
    plain_text,
    player_figures,
    stat_float,
    stat_int,
    table_headers,
    table_rows,
    social_links,
    team_matches,
    text_of,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

if TYPE_CHECKING:
    from bs4.element import Tag

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
_PLAYOFFS_MARKER = 'id="playoffs"'
_PLAYOFFS_STANDINGS_MARKER = 'id="standing-playoffs"'
# Markers in a week pane, in page order: a day heading, or the start of a match card.
_DAY_OR_CARD = re.compile(r'<div class="match (date|position-relative)[^"]*">')
_DAY_LABEL = re.compile(r"\s*(.*?)\s*</div>", re.S)
_TEAM = re.compile(r'class="team team([12])[^"]*"[^>]*>\s*<div class="logo">\s*<img[^>]*?src="([^"]*)"[^>]*>.*?<div class="name">\s*(.*?)\s*</div>', re.S)
_SCORE = re.compile(r'<div class="score[^"]*">\s*(.*?)\s*</div>', re.S)
_PLAY_TIME = re.compile(r'<div class="pt-1"[^>]*>\s*(.*?)\s*</div>', re.S)
_ROUND = re.compile(r'<div class="mb-1" style="[^"]*border-radius[^"]*">\s*(.*?)\s*</div>', re.S)
_IMAGE_SRC = re.compile(r'<img[^>]*?src="([^"]*)"')
_REPLAY_LINK = re.compile(r'<a [^>]*class="[^"]*\breplay\b[^"]*"[^>]*>')
_HREF = re.compile(r'href="([^"]*)"')
_MATCH_ID = re.compile(r"openMatchDetail\((\d+)\)")
_CALENDAR_START = re.compile(r"dates=(\d{8}T\d{6})/")


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
        panes.append((week, html[start : starts[index + 1][0]] if index + 1 < len(starts) else balanced_div(html, start)))
    return panes


def _text(value: str) -> str:
    return unescape(" ".join(re.sub(r"<!--.*?-->|<[^>]+>", " ", value, flags=re.S).split()))


def _team(match: re.Match[str]) -> Team:
    # Undecided playoff sides carry the league's own logo, which is left out.
    name = _text(match[3])
    return Team(name=name, logo=None if name == TO_BE_DECIDED else unescape(match[2]))


def _scheduled_match(card: str, best_of: int) -> ScheduleMatch:
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
    round_label = _ROUND.search(card)
    return ScheduleMatch(
        match_id=match_id[1] if match_id else None,
        start_at=datetime.strptime(started[1], "%Y%m%dT%H%M%S").replace(tzinfo=UTC).isoformat() if started else None,
        local_time=_text(time_box[1]) if time_box else "",
        team1=_team(teams["1"]),
        team2=_team(teams["2"]),
        score1=int(scores[0]) if scores[0] else None,
        score2=int(scores[1]) if scores[1] else None,
        replay_url=unescape(replay_href[1]) if replay_href else None,
        round=_text(round_label[1]) if round_label else None,
        best_of=best_of,
    )


def _schedule_days(pane: str, best_of: int = REGULAR_SEASON_BEST_OF) -> list[ScheduleDay]:
    markers = list(_DAY_OR_CARD.finditer(pane))
    days: list[ScheduleDay] = []
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(pane)
        if marker[1] == "date":
            label = _DAY_LABEL.match(pane, marker.end())
            days.append(ScheduleDay(label=_text(label[1]) if label else "", matches=[]))
        elif days:
            days[-1].matches.append(_scheduled_match(pane[marker.start() : end], best_of))
    return days


def _standings(html: str) -> list[Standing]:
    start = html.find(_STANDINGS_MARKER)
    if start < 0:
        return []
    block = balanced_div(html, html.rfind("<div", 0, start))
    return [_standing(row) for row in parse_html(block).select("tbody tr")]


def _seed(row: Tag) -> PlayoffSeed:
    rank, team, match_wl = row.find_all("td", recursive=False)
    image = team.find("img")
    return PlayoffSeed(
        seed=int(need(re.search(r"\d+", text_of(rank)), "a seed")[0]),
        team=Team(name=attr(image, "alt") or text_of(team), logo=attr(image, "src")),
        match_wl=parse_record(text_of(match_wl)),
    )


def _playoffs(html: str) -> PlayoffsResponse:
    pane = div_block(html, _PLAYOFFS_MARKER)
    days = _schedule_days(pane, PLAYOFFS_BEST_OF)
    mark_finals(days)
    standings = div_block(html, _PLAYOFFS_STANDINGS_MARKER)
    bracket = _IMAGE_SRC.search(standings)
    return PlayoffsResponse(
        bracket_image=unescape(bracket[1]) if bracket else None,
        seeds=[_seed(row) for row in parse_html(standings).select("tbody tr")] if standings else [],
        days=days,
    )


class Season(NamedTuple):
    weeks: list[ScheduleWeek]
    standings: list[Standing]
    playoffs: PlayoffsResponse


@ttl_cache(CACHE_SECONDS)
def get_season(lang: str) -> Season:
    """Schedule weeks, standings and playoffs, all read from one fetch of the schedule page in ``lang``."""
    html = fetch_page(EsportsSourceProvider.get_id_base_url(), f"/{lang}/schedule").text
    weeks = [ScheduleWeek(week=week, days=_schedule_days(pane)) for week, pane in _week_panes(html)]
    return Season(weeks, _standings(html), _playoffs(html))


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


# ---- teams: the list page is about 60 KB and a team page about 110 KB, read with patterns like the schedule

_TEAM_CARD = re.compile(r'<a href="[^"]*/team/([\w-]+)">\s*<div class="team-card-frame">.*?<img src="([^"]*)" alt="([^"]*)"', re.S)
_TEAM_HEADING = re.compile(r"<h4\b[^>]*>\s*<img src=['\"]([^'\"]*)['\"] alt=\"([^\"]*)\" class=\"team-logo\"\s*/?>\s*(.*?)\s*</h4>", re.S)
_ROSTER_MARKER = 'data-ga-impression="Section Roster Team Detail"'
_ROSTER_SEASON = re.compile(r"ROSTER\s+SEASON\s+(\d+)", re.I)
_ROSTER_CARD = re.compile(
    r'<img src="([^"]*)" alt="[^"]*">\s*</div>\s*</div>\s*<div class="player-name">\s*(.*?)\s*</div>\s*<div class="player-role[^"]*">\s*(.*?)\s*</div>',
    re.S,
)
# Player photos live on the league's own file host (a subdomain of its site, signed for six hours), whose name would
# give the source away, so they are served through this API (``get_player_photo``).
PHOTO_PATH = "esports/id/images/"


@ttl_cache(CACHE_SECONDS)
def get_teams() -> list[TeamSummary]:
    html = fetch_page(EsportsSourceProvider.get_id_base_url(), "/en/teams").text
    teams = {team_id: TeamSummary(team_id=team_id, name=_text(name), logo=unescape(logo)) for team_id, logo, name in _TEAM_CARD.findall(html)}
    return list(teams.values())


def _is_league_file(source: str) -> bool:
    host = urlsplit(source).hostname or ""
    site = urlsplit(EsportsSourceProvider.get_id_base_url()).hostname or ""
    return host == site or host.endswith(f".{site}")


def _file_name(source: str) -> str:
    return unquote(urlsplit(source).path.rsplit("/", 1)[-1])


class _TeamPage(NamedTuple):
    detail: TeamDetailResponse
    # Signed address of each player photo on the league's file host, by file name.
    photos: dict[str, str]


@ttl_cache(CACHE_SECONDS)
def _team_page(team_id: str) -> _TeamPage:
    team = find_team(get_teams(), team_id)
    html = fetch_page(EsportsSourceProvider.get_id_base_url(), f"/en/team/{team_id}").text
    roster = div_block(html, _ROSTER_MARKER)
    if not roster:
        raise AppError(status_code=404, code="TEAM_NOT_FOUND", message=f"No team {team_id!r} in this league.")
    heading = _TEAM_HEADING.search(html)
    socials = div_block(html, 'class="d-flex flex-row justify-content-center align-items-center icon-socmed"')
    season = _ROSTER_SEASON.search(roster)
    photos: dict[str, str] = {}
    members = []
    for source, name, role in _ROSTER_CARD.findall(roster):
        source = unescape(source)
        photo: str | None = source
        if _is_league_file(source):
            photos[_file_name(source)] = source
            photo = f"{config.API_URL}{PHOTO_PATH}{team_id}/{quote(_file_name(source))}"
        members.append(RosterMember(name=_text(name), role=normalize_role(_text(role)), photo=photo))
    season_data = get_season("en")
    # The page heads with the full name; the schedule and standings use the short one from the team list.
    name = team.name
    standing = find_standing(season_data.standings, name)
    detail = TeamDetailResponse(
        team_id=team_id,
        name=name,
        full_name=_text(heading[3]) if heading else None,
        logo=unescape(heading[1]) if heading else team.logo,
        season=int(season[1]) if season else None,
        socials=social_links(socials),
        players=[member for member in members if not is_staff(member.role)],
        staff=[member for member in members if is_staff(member.role)],
        standing=standing,
        matches=team_matches(name, season_data.weeks, season_data.playoffs.days),
    )
    return _TeamPage(detail, photos)


def _team_photos(team_id: str) -> dict[str, str]:
    try:
        return _team_page(team_id).photos
    except AppError:
        return {}


def get_team(team_id: str) -> TeamDetailResponse:
    return _team_page(team_id).detail


@ttl_cache(CACHE_SECONDS)
def get_player_photo(team_id: str, name: str) -> tuple[bytes, str]:
    """A roster photo from the league's file host: (bytes, content type)."""
    name = unquote(name)
    source = _team_photos(team_id).get(name) or _statistics().photos.get((team_id, name))
    if source is None:
        raise AppError(status_code=404, code="IMAGE_NOT_FOUND", message="No such player photo.")
    response = request_page(method="GET", url=source, headers=UpstreamHeaderBuilder.get_esports_header(EsportsSourceProvider.get_id_base_url()))
    return response.content, response.headers.get("content-type", "image/png")


# ---- season statistics: one page of about 1.9 MB (hero and player pools are most of it), read with patterns only.
# Its sections are tab panes; each runs to the start of the next.

_STAT_SECTIONS = ("teams", "players", "heroes", "hero-pools", "player-pools", "mvp-standings")
_STAT_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_ROW_LOGO = re.compile(r'<img src="([^"]*)"')
_ROW_TEAM_NAMES = re.compile(r'<span class="d-lg-none">\s*(.*?)\s*</span>\s*<span class="d-none d-lg-block">\s*(.*?)\s*</span>', re.S)
_PLAYER_FOLDER = re.compile(r"/player/([^/]+)/")
_BOARD_HEADING = re.compile(r'<div class="top-(player|hero)-stats-outer[^"]*">\s*<h5[^>]*>\s*(.*?)\s*</h5>', re.S)
_PLAYER_ENTRY = re.compile(
    r'<div class="player-photo">\s*<img src="([^"]*)"[^>]*>\s*</div>\s*<div class="team-logo">\s*<img src="([^"]*)"[^>]*>\s*</div>'
    r'\s*<div class="value">\s*(.*?)\s*</div>.*?<div class="player-name">\s*(.*?)\s*</div>',
    re.S,
)
_HERO_ENTRY = re.compile(
    r'<div class="hero-photo">\s*<img src="([^"]*)"[^>]*>\s*</div>\s*<div class="value[^"]*">\s*(.*?)\s*</div>.*?<div class="hero-name">\s*(.*?)\s*</div>',
    re.S,
)
_HERO_CELL = re.compile(r'<img src="([^"]*)"\s+alt="([^"]*)"')
_POOL_HERO = re.compile(
    r'<img src="([^"]*)" class="hero-pool-image">\s*<div class="hero-pool-pick[^"]*">\s*(\d+)\s*</div>\s*<div class="hero-pool-count">\s*([^<]*?)\s*</div>'
)
_POOL_PLAYER = re.compile(
    r'<img src="([^"]*)" class="player-pool-image">\s*</div>\s*<div class="player-pool-info">\s*(.*?)\s*</div>'
    r'\s*<div class="player-pool-pick[^"]*">\s*(\d+)\s*</div>\s*<div class="player-pool-count">\s*([^<]*?)\s*</div>',
    re.S,
)
_MVP_CARD = re.compile(
    r'<div class="team-logo"><img src="([^"]*)"\s*/?></div>\s*<div class="player-image"><img src="([^"]*)"\s*/?></div>'
    r'\s*<div class="rank">#(\d+)</div>\s*<div class="point">(\d+)\s*<span>.*?<div class="mvp-ign[^"]*">(.*?)</div>',
    re.S,
)
_TEAM_FIGURES = ("kills", "deaths", "assists", "gold", "damage", "lord", "tortoise", "tower")


class _Statistics(NamedTuple):
    teams: list[TeamStatistics]
    players: PlayerStatisticsResponse
    heroes: HeroStatisticsResponse
    hero_pools: list[HeroPool]
    player_pools: list[PlayerPool]
    mvp: list[MvpStanding]
    # Signed photo addresses on the league's file host, by (team id, file name), for ``get_player_photo``.
    photos: dict[tuple[str, str], str]


def _image_file(source: str) -> str:
    return unquote(urlsplit(unquote(unescape(source)).split("url=", 1)[-1]).path.rsplit("/", 1)[-1]).casefold()


def stat_hero(source: str, name: str | None = None) -> Hero:
    source = unescape(source).strip()
    # Pool images carry no alt text; the file is named after the hero ("Yi%20Sun-shin.jpg").
    inner = unquote(source.split("url=", 1)[-1])
    return Hero(name=name or inner.rsplit("/", 1)[-1].rsplit(".", 1)[0], image=source)


class _StatsContext:
    """Turns logos and photo addresses of the statistics page into teams and safe photo links."""

    def __init__(self, teams: list[TeamStatistics]) -> None:
        self.by_logo = {_image_file(row.team.logo or ""): row.team for row in teams if row.team.logo}
        self.by_name = {row.team.name.casefold(): row.team for row in teams}
        self.photos: dict[tuple[str, str], str] = {}

    def team(self, logo: str | None = None, photo: str | None = None) -> Team | None:
        folder = _PLAYER_FOLDER.search(photo or "")
        if folder and folder[1].casefold() in self.by_name:
            return self.by_name[folder[1].casefold()]
        return self.by_logo.get(_image_file(logo)) if logo else None

    def photo(self, source: str) -> str | None:
        source = unescape(source).strip()
        if not _is_league_file(source):
            return source or None
        folder = _PLAYER_FOLDER.search(source)
        if not folder:
            return None
        team_id, name = folder[1].casefold(), _file_name(source)
        self.photos[(team_id, name)] = source
        return f"{config.API_URL}{PHOTO_PATH}{team_id}/{quote(name)}"


def _stat_sections(html: str) -> dict[str, str]:
    marks = sorted((html.find(f'class="tab-content clearfix" id="{name}"'), name) for name in _STAT_SECTIONS)
    marks = [(start, name) for start, name in marks if start >= 0]
    return {name: html[start : marks[index + 1][0] if index + 1 < len(marks) else len(html)] for index, (start, name) in enumerate(marks)}


def _first_table(section: str) -> str:
    table = _STAT_TABLE.search(section)
    return table[0] if table else ""


def _team_statistics(section: str) -> list[TeamStatistics]:
    rows = []
    for cells in table_rows(_first_table(section)):
        names = _ROW_TEAM_NAMES.search(cells[0])
        logo = _ROW_LOGO.search(cells[0])
        team = Team(
            name=_text(names[1]) if names else plain_text(cells[0]),
            full_name=_text(names[2]) if names else None,
            logo=unescape(logo[1]) if logo else None,
        )
        figures = dict(zip(_TEAM_FIGURES, (stat_int(plain_text(cell)) for cell in cells[1:])))
        rows.append(TeamStatistics(team=team, **figures))
    return rows


def _boards(section: str, context: _StatsContext) -> list[Leaderboard]:
    headings = list(_BOARD_HEADING.finditer(section))
    boards = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else section.find("<table", heading.end())
        block = section[heading.end() : end if end >= 0 else len(section)]
        if heading[1] == "player":
            entries = [
                LeaderboardEntry(
                    rank=rank, name=_text(name), team=context.team(logo, photo), photo=context.photo(photo), value=stat_float(_text(value)) or 0
                )
                for rank, (photo, logo, value, name) in enumerate(_PLAYER_ENTRY.findall(block), start=1)
            ]
        else:
            entries = [
                LeaderboardEntry(rank=rank, name=_text(name), hero=stat_hero(image, _text(name)), value=stat_float(_text(value)) or 0)
                for rank, (image, value, name) in enumerate(_HERO_ENTRY.findall(block), start=1)
            ]
        boards.append(Leaderboard(title=_text(heading[2]), entries=entries))
    return boards


def _player_statistics(section: str, context: _StatsContext) -> PlayerStatisticsResponse:
    # The first table holds every player; the tables after it repeat them team by team.
    table = _first_table(section)
    headers = table_headers(table)
    players = []
    for cells in table_rows(table):
        logo = _ROW_LOGO.search(cells[0])
        players.append(
            PlayerStatistics(
                name=plain_text(cells[0]),
                team=context.team(logo[1] if logo else None),
                role=normalize_role(plain_text(cells[1])) or None if "lanes" in headers else None,
                **player_figures(headers, cells),
            )
        )
    return PlayerStatisticsResponse(leaderboards=_boards(section, context), players=players)


def _hero_statistics(section: str, context: _StatsContext) -> HeroStatisticsResponse:
    heroes = []
    for cells in table_rows(_first_table(section)):
        image = _HERO_CELL.search(cells[0])
        picks, bans, wins = (stat_int(plain_text(cell)) or 0 for cell in cells[1:4])
        heroes.append(
            HeroStatistics(
                hero=stat_hero(image[1], unescape(image[2]).strip()) if image else Hero(name=plain_text(cells[0])),
                picks=picks,
                bans=bans,
                wins=wins,
                win_rate=stat_float(plain_text(cells[4])) if len(cells) > 4 else None,
            )
        )
    return HeroStatisticsResponse(leaderboards=_boards(section, context), heroes=heroes)


def _hero_pools(section: str, context: _StatsContext) -> list[HeroPool]:
    pools = []
    for cells in table_rows(_first_table(section)):
        logo = _ROW_LOGO.search(cells[0])
        pools.append(
            HeroPool(
                name=plain_text(cells[0]),
                team=context.team(logo[1] if logo else None),
                role=normalize_role(plain_text(cells[1])) or None,
                total=stat_int(plain_text(cells[2])) or 0,
                heroes=[PoolHero(hero=stat_hero(image), picks=int(picks), win_rate=stat_float(rate)) for image, picks, rate in _POOL_HERO.findall(cells[3])],
            )
        )
    return pools


def _player_pools(section: str, context: _StatsContext) -> list[PlayerPool]:
    pools = []
    for cells in table_rows(_first_table(section)):
        image = _HERO_CELL.search(cells[0]) or _ROW_LOGO.search(cells[0])
        name = plain_text(cells[0])
        players = []
        for photo, info, picks, rate in _POOL_PLAYER.findall(cells[2]):
            # "NAVI - Zeonn": the team's short name, then the player.
            team_name, _, player = _text(info).partition(" - ")
            players.append(
                PoolPlayer(
                    name=player or team_name,
                    team=context.team(photo=photo) or context.by_name.get(team_name.casefold()),
                    photo=context.photo(photo),
                    picks=int(picks),
                    win_rate=stat_float(rate),
                )
            )
        pools.append(PlayerPool(hero=stat_hero(image[1], name) if image else Hero(name=name), total=stat_int(plain_text(cells[1])) or 0, players=players))
    return pools


def _mvp(section: str, context: _StatsContext) -> list[MvpStanding]:
    standings = []
    for logo, photo, rank, points, name in _MVP_CARD.findall(section):
        team = context.team(logo, photo)
        name = _text(name)
        # The card names the player after the team's short name ("TLID KEVIN").
        if team and name.casefold().startswith(f"{team.name.casefold()} "):
            name = name[len(team.name) + 1 :]
        standings.append(MvpStanding(rank=int(rank), name=name, team=team, photo=context.photo(photo), points=int(points)))
    return standings


@ttl_cache(CACHE_SECONDS)
def _statistics() -> _Statistics:
    html = fetch_page(EsportsSourceProvider.get_id_base_url(), "/en/statistics").text
    sections = _stat_sections(html)
    teams = _team_statistics(sections.get("teams", ""))
    context = _StatsContext(teams)
    return _Statistics(
        teams=teams,
        players=_player_statistics(sections.get("players", ""), context),
        heroes=_hero_statistics(sections.get("heroes", ""), context),
        hero_pools=_hero_pools(sections.get("hero-pools", ""), context),
        player_pools=_player_pools(sections.get("player-pools", ""), context),
        mvp=_mvp(sections.get("mvp-standings", ""), context),
        photos=context.photos,
    )


def get_team_statistics() -> TeamStatisticsResponse:
    return TeamStatisticsResponse(teams=_statistics().teams)


def get_player_statistics() -> PlayerStatisticsResponse:
    return _statistics().players


def get_hero_statistics() -> HeroStatisticsResponse:
    return _statistics().heroes


def get_hero_pools() -> HeroPoolsResponse:
    return HeroPoolsResponse(players=_statistics().hero_pools)


def get_player_pools() -> PlayerPoolsResponse:
    return PlayerPoolsResponse(heroes=_statistics().player_pools)


def get_mvp_standings() -> MvpStandingsResponse:
    return MvpStandingsResponse(standings=_statistics().mvp)
