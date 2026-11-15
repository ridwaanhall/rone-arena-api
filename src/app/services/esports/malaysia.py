"""Scraper for the Malaysian league site: schedule, standings, playoffs, match details and teams."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from html import unescape
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

from app.core.exceptions import AppError
from app.core.security import EsportsSourceProvider
from app.schemas.esports import (
    HeroStatistics,
    HeroStatisticsResponse,
    PlayerStatistics,
    PlayerStatisticsResponse,
    SavageManiac,
    SavageManiacResponse,
    TeamStatistics,
    TeamStatisticsResponse,
    Asset,
    Game,
    GameTeam,
    Hero,
    MatchDetailResponse,
    PlayoffSeed,
    PlayoffsResponse,
    Player,
    PlayerSeasonStats,
    ScheduleDay,
    ScheduleMatch,
    ScheduleWeek,
    Standing,
    RosterMember,
    Team,
    TeamDetailResponse,
    TeamSummary,
)
from app.services.esports.common import (
    CACHE_SECONDS,
    PLAYOFFS_BEST_OF,
    REGULAR_SEASON_BEST_OF,
    TO_BE_DECIDED,
    balanced_div,
    fetch_page,
    find_standing,
    find_team,
    is_staff,
    kda_ratio,
    mark_finals,
    need,
    normalize_role,
    parse_record,
    plain_text,
    player_figures,
    stat_float,
    stat_int,
    table_headers,
    table_rows,
    social_links,
    team_matches,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

_KUALA_LUMPUR = timezone(timedelta(hours=8))
_TAG = re.compile(r"<!--.*?-->|<[^>]+>", re.S)

# The home and schedule pages are about 0.9 MB each, too big for a BeautifulSoup tree on a Cloudflare Worker
# (error 1102), so every part is read from the text with these patterns.
_WEEK_START = re.compile(r'<div class="tab-pane[^"]*"\s+id="tab-schedule-regular-season-category-week-(\d+)"')
_PLAYOFFS_START = re.compile(r'<div class="tab-pane[^"]*"\s+id="tab-phase-playoffs"')
_DAY = re.compile(r'<div class="text-day[^"]*">\s*DAY\s*(\d+)\s*</div>(.*?)(?=<div class="text-day|\Z)', re.S)
_CARD_START = re.compile(r'<div class="match-card\b')
_LOGO = re.compile(r'<div class="team-logo">\s*<img src="([^"]*)"')
_NAME = re.compile(r'<div class="team-name">\s*(.*?)\s*</div>', re.S)
_SCORE = re.compile(r'<div class="team-score[^"]*">\s*(\d*)\s*</div>')
_DATE = re.compile(r'<div class="match-date">\s*(.*?)\s*</div>')
_TIME = re.compile(r'<div class="match-time">\s*(.*?)\s*</div>')
_PLAYOFF_TIME = re.compile(r'Match Starts</div>\s*<div class="date-text-value">\s*(.*?)\s*</div>', re.S)
_PLAYOFF_DATE = re.compile(r'<div class="text-date[^"]*">\s*(.*?)\s*</div>')
_ROUND = re.compile(r'<div class="match-group-bracket[^"]*">\s*(.*?)\s*</div>', re.S)
_ROUND_BEST_OF = re.compile(r"\(\s*B[O0]\s*(\d)\s*\)", re.I)
_VIDEO = re.compile(r'<a href="(http[^"]*)"[^>]*>\s*(EN|BM)\s*</a>')
_DETAIL_ID = re.compile(r'data-detail-id="(\d+)"')
_SEASON_YEAR = re.compile(r"Date:\s*\d{1,2}\s+\w+\s*-\s*\d{1,2}\s+\w+\s+(\d{4})")

_STANDINGS_TABLE = 'id="tableStandingDesktop"'
_STANDING_ROW = re.compile(r'<tr class="(playoffs|eliminated)">(.*?)</tr>', re.S)
_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S)
_IMG = re.compile(r'<img src="([^"]*)"(?:\s+alt="([^"]*)")?')
_TEAM_LINK = re.compile(r'href="[^"]*/team/([\w-]+)"')


def _text(markup: str) -> str:
    return unescape(" ".join(_TAG.sub(" ", markup).split()))


def _team(name: str, logo: str | None) -> Team:
    # Undecided playoff sides carry a placeholder logo, which is left out.
    return Team(name=name, logo=None if name == TO_BE_DECIDED else logo)


def _cards(block: str) -> list[str]:
    starts = [found.start() for found in _CARD_START.finditer(block)]
    return [balanced_div(block, start) for start in starts]


def _start_at(day: str, local_time: str, year: int) -> str | None:
    """``day`` is "14 Aug", ``local_time`` "17:00" (regular season) or "3:00PM" (playoffs), Malaysian time."""
    for pattern in ("%d %b %Y %H:%M", "%d %b %Y %I:%M%p"):
        try:
            started = datetime.strptime(f"{day} {year} {local_time.replace(' ', '')}", pattern)
        except ValueError:
            continue
        return started.replace(tzinfo=_KUALA_LUMPUR).astimezone(UTC).isoformat()
    return None


def _match(card: str, day: str, local_time: str, year: int, best_of: int) -> ScheduleMatch:
    names = [_text(name) for name in _NAME.findall(card)][:2]
    if len(names) != 2:
        raise AppError(
            status_code=502,
            code="UPSTREAM_PAGE_CHANGED",
            message="The league site returned a page in an unexpected format (a match has no teams).",
        )
    logos = [unescape(logo) for logo in _LOGO.findall(card)][:2] + [None, None]
    scores = [score for score in _SCORE.findall(card)][:2]
    videos = dict((language, unescape(link)) for link, language in _VIDEO.findall(card))
    detail = _DETAIL_ID.search(card)
    played = len(scores) == 2 and all(scores)
    return ScheduleMatch(
        match_id=detail[1] if detail and played else None,
        start_at=_start_at(day, local_time, year),
        local_time=local_time,
        team1=_team(names[0], logos[0]),
        team2=_team(names[1], logos[1]),
        score1=int(scores[0]) if played else None,
        score2=int(scores[1]) if played else None,
        replay_url=videos.get("EN") or videos.get("BM"),
        best_of=best_of,
    )


def _week(pane: str, year: int) -> list[ScheduleDay]:
    days = []
    for number, block in _DAY.findall(pane):
        weekday = _text(block[: block.find("</div>")])
        matches = []
        for card in _cards(block):
            date = _DATE.search(card)
            time = _TIME.search(card)
            day = _text(date[1]) if date else ""
            matches.append(_match(card, day, _text(time[1]) if time else "", year, REGULAR_SEASON_BEST_OF))
        first = _DATE.search(block)
        label = f"{weekday}, {_text(first[1])} {year}" if first else weekday
        days.append(ScheduleDay(day=int(number), label=label, matches=matches))
    return days


def _playoff_days(pane: str, year: int) -> list[ScheduleDay]:
    days = []
    for number, block in _DAY.findall(pane):
        date = _PLAYOFF_DATE.search(block)
        label = _text(date[1]) if date else ""
        # "Wed, 28 Oct 2026": the day and month for the start time.
        day = " ".join(label.split(",", 1)[-1].split()[:2])
        round_label = _ROUND.search(block)
        name = _text(round_label[1]) if round_label else None
        stated = _ROUND_BEST_OF.search(name or "")
        best_of = int(stated[1]) if stated else PLAYOFFS_BEST_OF
        matches = []
        for card in _cards(block):
            time = _PLAYOFF_TIME.search(card)
            local_time = _text(time[1]) if time else ""
            item = _match(card, day, local_time, year, best_of)
            item.round = _ROUND_BEST_OF.sub("", name).strip() if name else None
            matches.append(item)
        days.append(ScheduleDay(day=int(number), label=label, matches=matches))
    if not any(_ROUND_BEST_OF.search(_text(found)) for found in _ROUND.findall(pane)):
        mark_finals(days)
    return days


def _standing(row: str, rank_class: str) -> Standing:
    cells = _CELL.findall(row)
    image = need(_IMG.search(cells[1]), "a team logo")
    match_wl, game_wl, match_point, net = (_text(cell) for cell in cells[2:6])
    return Standing(
        rank=to_int(_text(cells[0])),
        team=Team(name=unescape(image[2] or _text(cells[1])), full_name=_text(cells[1]), logo=unescape(image[1])),
        match_point=to_int(match_point),
        match_wl=parse_record(match_wl),
        net_game_win=int(net.replace("+", "")),
        game_wl=parse_record(game_wl),
    )


class Season(NamedTuple):
    weeks: list[ScheduleWeek]
    standings: list[Standing]
    playoffs: PlayoffsResponse


class _HomePage(NamedTuple):
    standings: list[Standing]
    # How many teams the table marks as playoff teams.
    qualified: int
    # Each team's id (its page on the site), in table order.
    teams: list[TeamSummary]


@ttl_cache(CACHE_SECONDS)
def _home() -> _HomePage:
    """The standings table, its playoff line and the teams' ids, from the home page."""
    html = fetch_page(EsportsSourceProvider.get_my_base_url(), "/").text
    start = html.find(_STANDINGS_TABLE)
    if start < 0:
        return _HomePage([], 0, [])
    table = html[start : html.find("</table>", start)]
    rows = _STANDING_ROW.findall(table)
    standings = [_standing(row, kind) for kind, row in rows]
    teams = [
        TeamSummary(team_id=link[1], name=row.team.name, full_name=row.team.full_name, logo=row.team.logo)
        for (_, markup), row in zip(rows, standings)
        if (link := _TEAM_LINK.search(markup))
    ]
    return _HomePage(standings, sum(1 for kind, _ in rows if kind == "playoffs"), teams)


@ttl_cache(CACHE_SECONDS)
def get_season() -> Season:
    """Weeks and playoff days from one fetch of the schedule page, standings and seeds from the home page."""
    html = fetch_page(EsportsSourceProvider.get_my_base_url(), "/schedule").text
    year_found = _SEASON_YEAR.search(html)
    year = int(year_found[1]) if year_found else datetime.now(UTC).year
    playoffs_start = _PLAYOFFS_START.search(html)
    starts = [(found.start(), int(found[1])) for found in _WEEK_START.finditer(html, 0, playoffs_start.start() if playoffs_start else len(html))]
    weeks = [ScheduleWeek(week=week, days=_week(balanced_div(html, start), year)) for start, week in starts]
    days = _playoff_days(balanced_div(html, playoffs_start.start()), year) if playoffs_start else []
    table, qualified, _ = _home()
    seeds = [PlayoffSeed(seed=row.rank, team=row.team, match_wl=row.match_wl) for row in table[:qualified]]
    return Season(weeks, table, PlayoffsResponse(bracket_image=None, seeds=seeds, days=days))


# ---- match details: one answer per match, about 230 KB, read with patterns like the pages above

_GAME_START = re.compile(r'<div class="card-match-detail\b[^"]*"\s+data-game-no="(\d+)"')
_HEADER_SIDE = re.compile(r'<div class="title-team-([12])[^"]*card-match-team\s+(victory|defeat)\s*"', re.S)
_SIDE_NAME = re.compile(r'<div class="team-name">\s*(.*?)\s*</div>', re.S)
_SIDE_LOGO = re.compile(r'<div class="team-logo-sm[^"]*"><img src="([^"]*)"')
_SIDE_KILLS = re.compile(r'<div class="fw-semibold team-score-sm">\s*(\d+)\s*</div>')
_GAME_TIME = re.compile(r'<div class="text-game-time">\s*([\d:]+)\s*</div>')
_PLAYER_START = re.compile(r'player-info-stats team([12])"')
_MID_START = re.compile(r'<div class="col-0 col-lg-mid\b')
_PLAYER_NAME = re.compile(r'<div class="player-name">\s*(.*?)\s*</div>', re.S)
_HERO = re.compile(r'<img class="hero-logo[^"]*" src="([^"]*)" alt="([^"]+)"')
# Team 2's KDA carries a spacing class as well (`kda-content me-2`) in one of the page's two versions.
_KDA = re.compile(r'<div class="kda-content[^"]*">\s*(\d+)/(\d+)/(\d+)\s*</div>')
_EQUIPMENT = re.compile(r'<img src="([^"]*)" alt="(\d+)" class="equipment-logo"')
_PAIR = re.compile(r'<div class="kda-content">\s*([\d,.]+)\s*</div>\s*<div class="kda-text">.*?</div>\s*<div class="kda-content">\s*([\d,.]+)\s*</div>', re.S)
# The four figures between two players, in page order. The site labels them tower damage, damage taken, hero
# damage and total gold, but the labels are shifted: the values are hero damage, gold, tower damage and damage
# taken (a tank's "total gold" of 177,579 in a 30-minute game is its damage taken; the winners' "hero damage"
# is the only figure that tracks the towers they took).
_MID_FIGURES = ("damage_dealt", "gold", "tower_damage", "damage_taken")


def _player(block: str, figures: dict[str, int]) -> Player | None:
    """A player, or None when the site has not filled in the hero (it leaves some games without them)."""
    name = _text(need(_PLAYER_NAME.search(block), "a player name")[1])
    hero = _HERO.search(block)
    if not hero:
        return None
    kills, deaths, assists = (int(part) for part in need(_KDA.search(block), "a KDA").groups())
    return Player(
        name=name,
        hero=Hero(name=unescape(hero[2]), image=unescape(hero[1])),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=kda_ratio(kills, deaths, assists),
        items=[Asset(id=item_id, image=unescape(source)) for source, item_id in _EQUIPMENT.findall(block)],
        # The site prints the same emblem and talents for both players of a lane (team 1's or team 2's, it does
        # not say), so they are left out rather than shown for the wrong player.
        emblem=None,
        talents=[],
        gold=figures.get("gold"),
        damage_dealt=figures.get("damage_dealt"),
        damage_taken=figures.get("damage_taken"),
        tower_damage=figures.get("tower_damage"),
    )


def _players(block: str) -> tuple[list[Player | None], list[Player | None]]:
    """Each lane row is team 1's player, the figures of both, then team 2's player."""
    marks = sorted(
        [(found.start(), found[1]) for found in _PLAYER_START.finditer(block)]
        + [(found.start(), "mid") for found in _MID_START.finditer(block)]
    )
    sides: tuple[list[Player | None], list[Player | None]] = ([], [])
    pending: list[str] = []
    figures: tuple[dict[str, int], dict[str, int]] = ({}, {})
    for index, (start, kind) in enumerate(marks):
        part = block[start : marks[index + 1][0] if index + 1 < len(marks) else len(block)]
        if kind == "1":
            pending = [part]
        elif kind == "mid":
            pairs = _PAIR.findall(part)
            figures = (
                {key: to_int(pair[0]) for key, pair in zip(_MID_FIGURES, pairs)},
                {key: to_int(pair[1]) for key, pair in zip(_MID_FIGURES, pairs)},
            )
        elif pending:
            sides[0].append(_player(pending[0], figures[0]))
            sides[1].append(_player(part, figures[1]))
            pending = []
    return sides


# The match fragment cuts a long team name with a run of dots ("iG ........"); the schedule names the team "iG".
_CUT_NAME = re.compile(r"\s*\.{2,}\s*$")


def _team_name(markup: str) -> str:
    return _CUT_NAME.sub("", _text(markup))


def _game(number: int, block: str) -> Game | None:
    header = block[: block.find("team-versus-title mobile")]
    sides = []
    for found in _HEADER_SIDE.finditer(header):
        side = balanced_div(header, found.start())
        logo = _SIDE_LOGO.search(side)
        sides.append(
            (
                Team(name=_team_name(need(_SIDE_NAME.search(side), "a team name")[1]), logo=unescape(logo[1]) if logo else None),
                found[2] == "victory",
                int(need(_SIDE_KILLS.search(side), "a team's kills")[1]),
            )
        )
    players = _players(block)
    # A game the site published without its heroes says nothing about the draft, so it is left out.
    if len(sides) != 2 or not players[0] or any(player is None for side in players for player in side):
        return None
    clock = _GAME_TIME.search(header)
    return Game(
        number=number,
        duration=clock[1] if clock else None,
        teams=[
            GameTeam(team=team, winner=won, kills=kills, stats={}, players=[player for player in side_players if player])
            for (team, won, kills), side_players in zip(sides, players)
        ],
    )


def _consistent(game: Game) -> bool:
    """The players' kills add up to the team's score."""
    return all(sum(player.kills for player in team.players) == team.kills for team in game.teams)


def _games(html: str) -> list[Game]:
    starts = list(_GAME_START.finditer(html))
    games = []
    for index, found in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(html)
        game = _game(int(found[1]), html[found.start() : end])
        if game:
            games.append(game)
    return games


# The site serves two versions of a match fragment at random (about 2 in 5 fetches get the bad one, Oct 2026), and
# that one repeats team 1's KDA for team 2. A page whose kills do not add up is fetched again (six tries leave
# under a 0.5 % chance of no good copy); a game still wrong after the last try is left out.
_MATCH_TRIES = 6


@ttl_cache(CACHE_SECONDS)
def get_match(match_id: int) -> MatchDetailResponse:
    for _ in range(_MATCH_TRIES):
        try:
            html = fetch_page(EsportsSourceProvider.get_my_base_url(), f"/ajax/rating/match-detail?matchId={match_id}&isShowDetail=false").text
        except AppError as error:
            # The site answers an unknown match with a 500; say so plainly instead of passing on a server error.
            if error.status_code in (404, 500):
                raise AppError(status_code=404, code="MATCH_NOT_FOUND", message=f"No match details found for match {match_id}.") from error
            raise
        games = _games(html)
        if all(_consistent(game) for game in games):
            break
    games = [game for game in games if _consistent(game)]
    if not games:
        raise AppError(status_code=404, code="MATCH_NOT_FOUND", message=f"No match details found for match {match_id}.")
    return MatchDetailResponse(match_id=str(match_id), games=games)


# ---- teams: the list comes from the home page's standings (every team links its page); a team page is about 330 KB

_TEAM_LOGO = re.compile(r'<img src="([^"]*)" class="team-logo\b')
_TEAM_PHOTO = re.compile(r'<img src="([^"]*)" alt="[^"]*" class="team-pic"')
_TEAM_NAME = re.compile(r'<div class="text-center text-fit-parent">\s*(.*?)\s*</div>', re.S)
_MUSIC = re.compile(r'<audio id="audio-source" src="([^"]*)"')
_SLOGAN = re.compile(r'<div class="text-fit-parent text-gradient"[^>]*>\s*(.*?)\s*</div>', re.S)
_DESCRIPTION = re.compile(r'<div class="team-desc[^"]*"[^>]*>(.*?)</div>', re.S)
_PARAGRAPH = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)
_GALLERY_IMAGE = re.compile(r'<img src="([^"]*)"')
_MATCH_SEASON = re.compile(r"Match Season\s*(\d+)")
_CARD_COLUMN = re.compile(r'<div class="col-6 col-lg-25\b')
_ROLE = re.compile(r'class="talent-role[^"]*">.*?<span>\s*(.*?)\s*</span>', re.S)
_ARCHETYPE = re.compile(r'<div class="archetype-wrapper[^"]*">\s*(.*?)\s*</div>', re.S)
_TALENT_NAME = re.compile(r'class="talent-name[^"]*">\s*<span[^>]*>\s*(.*?)\s*</span>', re.S)
_STAT_ROW = re.compile(r"<span>\s*([\w ]+?):\s*</span>\s*<span class=\"tooltip-value\">\s*([\d,.]*)\s*</span>")
_TIER = re.compile(r'<div class="tier-badge">\s*<img src="[^"]*" class="orns" alt="([^"]*)"')
_BIRTH = re.compile(r'<div class="bod-wrapper[^"]*">\s*<span[^>]*>\s*([^<]*?)\s*</span>.*?<span[^>]*>\s*(\d+)\s*Years? Old\s*</span>', re.S)
_NATIONALITY = re.compile(r'<div class="nationality-wrapper[^"]*">\s*(?:<img src="([^"]*)"[^>]*>)?\s*<span[^>]*>\s*(.*?)\s*</span>', re.S)
_FLAG = re.compile(r"Flag_of_(?:the_)?([A-Za-z_]+)\.\w+")
_PORTRAIT = re.compile(r'<img src="([^"]*)" class="talent-img"')
_PREVIOUS_TEAM = re.compile(
    r'Previous team</span>\s*</div>\s*(?:<img src="([^"]*)"[^>]*>)?\s*<div class="easter-egg-logo-name">\s*(.*?)\s*</div>', re.S
)
_SECOND_ROLE = re.compile(r'2nd role</span>.*?<div class="easter-egg-logo-name">\s*(.*?)\s*</div>', re.S)
_MEMBER_SOCIALS = re.compile(r'<div\s+class="team-social-media\b[^"]*">(.*?)</div>', re.S)


def get_teams() -> list[TeamSummary]:
    return sorted(_home().teams, key=lambda team: (team.full_name or team.name).casefold())


def _league_image(source: str) -> bool:
    """Icons and ornaments on the league's own site, which must not reach an answer."""
    host = urlsplit(source).hostname or ""
    site = urlsplit(EsportsSourceProvider.get_my_base_url()).hostname or ""
    return not host or host == site or host.endswith(f".{site}")


def _image(source: str | None) -> str | None:
    source = unescape(source) if source else None
    return None if not source or _league_image(source) else source


def _season_stats(card: str) -> PlayerSeasonStats | None:
    figures = {label.strip().casefold(): to_int(value) for label, value in _STAT_ROW.findall(card) if value}
    if "kills" not in figures:
        return None
    kills, deaths, assists = figures["kills"], figures.get("deaths", 0), figures.get("assists", 0)
    return PlayerSeasonStats(
        matches=figures.get("total matches", 0),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=kda_ratio(kills, deaths, assists),
        savage=figures.get("savage"),
        maniac=figures.get("maniac"),
    )


def _member(column: str) -> RosterMember | None:
    name = _TALENT_NAME.search(column)
    if not name:
        return None
    card_end = column.find('<span class="orn-talent-box-frame">')
    card, after = (column[:card_end], column[card_end:]) if card_end >= 0 else (column, "")
    role = _ROLE.search(card)
    archetype = _ARCHETYPE.search(card)
    tier = _TIER.search(card)
    birth = _BIRTH.search(card)
    nationality = _NATIONALITY.search(card)
    flag = _FLAG.search(unquote(nationality[1] or "")) if nationality else None
    portrait = _PORTRAIT.search(card)
    previous = _PREVIOUS_TEAM.search(card)
    second = _SECOND_ROLE.search(card)
    socials = _MEMBER_SOCIALS.search(after)
    return RosterMember(
        name=_text(name[1]),
        role=normalize_role(_text(role[1])) if role else "",
        photo=_image(portrait[1]) if portrait else None,
        archetype=_text(archetype[1]) or None if archetype else None,
        secondary_role=normalize_role(_text(second[1])) or None if second else None,
        tier=unescape(tier[1]) or None if tier else None,
        birth_date=birth[1] or None if birth else None,
        age=int(birth[2]) if birth else None,
        nationality=flag[1].replace("_", " ") if flag else None,
        hometown=_text(nationality[2]) or None if nationality else None,
        previous_team=Team(name=_text(previous[2]), logo=_image(previous[1])) if previous and _text(previous[2]) else None,
        socials=social_links(socials[1]) if socials else [],
        stats=_season_stats(card),
    )


@ttl_cache(CACHE_SECONDS)
def get_team(team_id: str) -> TeamDetailResponse:
    team = find_team(get_teams(), team_id)
    html = fetch_page(EsportsSourceProvider.get_my_base_url(), f"/team/{team_id}").text
    info = html.find('class="team-info')
    if info < 0:
        raise AppError(status_code=404, code="TEAM_NOT_FOUND", message=f"No team {team_id!r} in this league.")
    header = balanced_div(html, html.rfind("<div", 0, info))
    slogan_start = header.find("description-slogan-wrapper")
    slogan = _SLOGAN.search(header, slogan_start) if slogan_start >= 0 else None
    description = _DESCRIPTION.search(header)
    paragraphs = [_text(paragraph) for paragraph in _PARAGRAPH.findall(description[1])] if description else []
    gallery_start = html.find('class="team-photos"')
    gallery = balanced_div(html, html.rfind("<div", 0, gallery_start)) if gallery_start >= 0 else ""
    # Each member is a column holding a talent card; the scan starts at the column of the first card.
    first_card = html.find('<div class="talent-card"')
    roster_start = html.rfind('<div class="col-6 col-lg-25', 0, first_card) if first_card >= 0 else len(html)
    members = [member for found in _CARD_COLUMN.finditer(html, roster_start) if (member := _member(balanced_div(html, found.start())))]
    music = _MUSIC.search(header)
    photo = _TEAM_PHOTO.search(header)
    logo = _TEAM_LOGO.search(header)
    name = _TEAM_NAME.search(header)
    season = _MATCH_SEASON.search(html)
    socials = _MEMBER_SOCIALS.search(header)
    data = get_season()
    return TeamDetailResponse(
        team_id=team_id,
        name=team.name,
        full_name=team.full_name or (_text(name[1]) if name else None),
        logo=_image(logo[1]) if logo else team.logo,
        season=int(season[1]) if season else None,
        tagline=_text(slogan[1]) or None if slogan else None,
        description="\n\n".join(paragraph for paragraph in paragraphs if paragraph) or None,
        socials=social_links(socials[1]) if socials else [],
        team_photo=_image(photo[1]) if photo else None,
        gallery=[image for source in dict.fromkeys(_GALLERY_IMAGE.findall(gallery)) if (image := _image(source))],
        entrance_music=unescape(music[1]) if music else None,
        players=[member for member in members if not is_staff(member.role)],
        staff=[member for member in members if is_staff(member.role)],
        standing=find_standing(data.standings, team.name),
        matches=team_matches(team.name, data.weeks, data.playoffs.days),
    )


# ---- season statistics: the bottom of the teams page (about 0.8 MB, most of it the hero table printed twice, for
# phones and for desktops) has the team, player, hero and savage/maniac tables; read with patterns only.

_STAT_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_STAT_PANE = re.compile(r'<div class="tab-pane[^"]*" id="tab-stats-([\w-]+)"')
_ROLE_CLASS = re.compile(r"col-player-role-(?!all\b)(\w+)")
_ROW = re.compile(r"<tr\b([^>]*)>(.*?)</tr>", re.S)
_SHORT_AND_FULL = re.compile(r'<span class="d-lg-none[^"]*">\s*(.*?)\s*</span>\s*<span class="d-none d-lg-block[^"]*">\s*(.*?)\s*</span>', re.S)
_HERO_IMAGE = re.compile(r'<img src="([^"]*)"\s+alt="([^"]*)"')
_TEAM_FIGURES = ("kills", "deaths", "assists", "gold", "damage", "lord", "tortoise", "tower")


class _Statistics(NamedTuple):
    teams: list[TeamStatistics]
    players: list[PlayerStatistics]
    heroes: list[HeroStatistics]
    savage_maniac: list[SavageManiac]


def _stat_panes(html: str) -> dict[str, str]:
    starts = [(found.start(), found[1]) for found in _STAT_PANE.finditer(html)]
    return {name: html[start : starts[index + 1][0] if index + 1 < len(starts) else len(html)] for index, (start, name) in enumerate(starts)}


def _first_table(pane: str) -> str:
    table = _STAT_TABLE.search(pane)
    return table[0] if table else ""


def _row_team(cell: str, teams: dict[str, TeamSummary]) -> Team | None:
    link = _TEAM_LINK.search(cell)
    team = teams.get(link[1]) if link else None
    if team:
        return Team(name=team.name, full_name=team.full_name, logo=team.logo)
    names = _SHORT_AND_FULL.search(cell)
    logo = _IMG.search(cell)
    if not names:
        return None
    return Team(name=_text(names[1]), full_name=_text(names[2]) or None, logo=unescape(logo[1]) if logo else None)


@ttl_cache(CACHE_SECONDS)
def _statistics() -> _Statistics:
    html = fetch_page(EsportsSourceProvider.get_my_base_url(), "/teams").text
    panes = _stat_panes(html)
    teams = {team.team_id: team for team in _home().teams}

    team_rows = []
    for cells in table_rows(_first_table(panes.get("teams", ""))):
        team = _row_team(cells[0], teams)
        if team:
            team_rows.append(TeamStatistics(team=team, **dict(zip(_TEAM_FIGURES, (stat_int(plain_text(cell)) for cell in cells[1:])))))

    table = _first_table(panes.get("players", ""))
    headers = table_headers(table)
    body = table[table.find("<tbody") :] if "<tbody" in table else table
    players = []
    for attributes, row in _ROW.findall(body):
        cells = table_rows(f"<tr>{row}</tr>")
        if not cells:
            continue
        cells = cells[0]
        # The row's classes name the player's lane ("col-player-role-midlane"); the table has no lane column.
        role = _ROLE_CLASS.search(attributes)
        players.append(
            PlayerStatistics(
                name=plain_text(cells[0]),
                team=_row_team(cells[0], teams),
                role=normalize_role(role[1]) if role else None,
                **player_figures(headers, cells),
            )
        )

    table = _first_table(panes.get("heroes", ""))
    column = {header: index for index, header in enumerate(table_headers(table))}
    heroes = []
    for cells in table_rows(table):
        image = _HERO_IMAGE.search(cells[0])

        def figure(name: str) -> str:
            return plain_text(cells[column[name]]) if name in column else ""

        heroes.append(
            HeroStatistics(
                hero=Hero(name=unescape(image[2]).strip(), image=unescape(image[1])) if image else Hero(name=plain_text(cells[0])),
                picks=stat_int(figure("pick")) or 0,
                bans=stat_int(figure("ban")) or 0,
                wins=stat_int(figure("win")) or 0,
                win_rate=stat_float(figure("win rate")),
            )
        )

    savage_maniac = [
        SavageManiac(name=plain_text(cells[0]), team=_row_team(cells[0], teams), savage=stat_int(plain_text(cells[1])) or 0, maniac=stat_int(plain_text(cells[2])) or 0)
        for cells in table_rows(_first_table(panes.get("savage-maniac", "")))
        if len(cells) >= 3
    ]
    return _Statistics(team_rows, players, heroes, savage_maniac)


def get_team_statistics() -> TeamStatisticsResponse:
    return TeamStatisticsResponse(teams=_statistics().teams)


def get_player_statistics() -> PlayerStatisticsResponse:
    # The league publishes no leaderboards.
    return PlayerStatisticsResponse(leaderboards=[], players=_statistics().players)


def get_hero_statistics() -> HeroStatisticsResponse:
    return HeroStatisticsResponse(leaderboards=[], heroes=_statistics().heroes)


def get_savage_maniac() -> SavageManiacResponse:
    return SavageManiacResponse(players=_statistics().savage_maniac)
