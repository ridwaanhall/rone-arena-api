"""Scraper for the Malaysian league site: schedule, standings, playoffs and match details."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from html import unescape
from typing import NamedTuple

from app.core.exceptions import AppError
from app.core.security import EsportsSourceProvider
from app.schemas.esports import (
    Asset,
    Game,
    GameTeam,
    Hero,
    MatchDetailResponse,
    PlayoffSeed,
    PlayoffsResponse,
    Player,
    ScheduleDay,
    ScheduleMatch,
    ScheduleWeek,
    Standing,
    Team,
)
from app.services.esports.common import (
    CACHE_SECONDS,
    PLAYOFFS_BEST_OF,
    REGULAR_SEASON_BEST_OF,
    TO_BE_DECIDED,
    balanced_div,
    fetch_page,
    kda_ratio,
    mark_finals,
    need,
    parse_record,
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


@ttl_cache(CACHE_SECONDS)
def _standings() -> tuple[list[Standing], int]:
    """The standings table and how many teams it marks as playoff teams, from the home page."""
    html = fetch_page(EsportsSourceProvider.get_my_base_url(), "/").text
    start = html.find(_STANDINGS_TABLE)
    if start < 0:
        return [], 0
    table = html[start : html.find("</table>", start)]
    rows = _STANDING_ROW.findall(table)
    return [_standing(row, kind) for kind, row in rows], sum(1 for kind, _ in rows if kind == "playoffs")


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
    table, qualified = _standings()
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
_HERO = re.compile(r'<img class="hero-logo[^"]*" src="([^"]*)" alt="([^"]*)"')
_KDA = re.compile(r'<div class="kda-content">\s*(\d+)/(\d+)/(\d+)\s*</div>')
_EQUIPMENT = re.compile(r'<img src="([^"]*)" alt="(\d+)" class="equipment-logo"')
_PAIR = re.compile(r'<div class="kda-content">\s*([\d,.]+)\s*</div>\s*<div class="kda-text">.*?</div>\s*<div class="kda-content">\s*([\d,.]+)\s*</div>', re.S)
# The four figures between two players, in page order. The site labels them tower damage, damage taken, hero
# damage and total gold, but the labels are shifted: the values are hero damage, gold, tower damage and damage
# taken (a tank's "total gold" of 177,579 in a 30-minute game is its damage taken; the winners' "hero damage"
# is the only figure that tracks the towers they took).
_MID_FIGURES = ("damage_dealt", "gold", "tower_damage", "damage_taken")


def _player(block: str, figures: dict[str, int]) -> Player:
    name = _text(need(_PLAYER_NAME.search(block), "a player name")[1])
    hero = need(_HERO.search(block), "a hero")
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


def _players(block: str) -> tuple[list[Player], list[Player]]:
    """Each lane row is team 1's player, the figures of both, then team 2's player."""
    marks = sorted(
        [(found.start(), found[1]) for found in _PLAYER_START.finditer(block)]
        + [(found.start(), "mid") for found in _MID_START.finditer(block)]
    )
    sides: tuple[list[Player], list[Player]] = ([], [])
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


def _game(number: int, block: str) -> Game | None:
    header = block[: block.find("team-versus-title mobile")]
    sides = []
    for found in _HEADER_SIDE.finditer(header):
        side = balanced_div(header, found.start())
        logo = _SIDE_LOGO.search(side)
        sides.append(
            (
                Team(name=_text(need(_SIDE_NAME.search(side), "a team name")[1]), logo=unescape(logo[1]) if logo else None),
                found[2] == "victory",
                int(need(_SIDE_KILLS.search(side), "a team's kills")[1]),
            )
        )
    players = _players(block)
    if len(sides) != 2 or not players[0]:
        return None
    clock = _GAME_TIME.search(header)
    return Game(
        number=number,
        duration=clock[1] if clock else None,
        teams=[
            GameTeam(team=team, winner=won, kills=kills, stats={}, players=side_players)
            for (team, won, kills), side_players in zip(sides, players)
        ],
    )


@ttl_cache(CACHE_SECONDS)
def get_match(match_id: int) -> MatchDetailResponse:
    try:
        html = fetch_page(EsportsSourceProvider.get_my_base_url(), f"/ajax/rating/match-detail?matchId={match_id}&isShowDetail=false").text
    except AppError as error:
        # The site answers an unknown match with a 500; say so plainly instead of passing on a server error.
        if error.status_code in (404, 500):
            raise AppError(status_code=404, code="MATCH_NOT_FOUND", message=f"No match details found for match {match_id}.") from error
        raise
    starts = list(_GAME_START.finditer(html))
    games = []
    for index, found in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(html)
        game = _game(int(found[1]), html[found.start() : end])
        if game:
            games.append(game)
    if not games:
        raise AppError(status_code=404, code="MATCH_NOT_FOUND", message=f"No match details found for match {match_id}.")
    return MatchDetailResponse(match_id=str(match_id), games=games)
