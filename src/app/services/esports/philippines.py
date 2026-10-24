"""Scraper for the Philippine league site: schedule, standings and match details."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from html import unescape

from bs4.element import Tag

from app.core.http import UpstreamHeaderBuilder, request_page
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
    SequenceItem,
    Standing,
    Team,
)
from app.services.esports.common import (
    CACHE_SECONDS,
    PH_ELIMINATED,
    PLAYOFFS_BEST_OF,
    REGULAR_SEASON_BEST_OF,
    TO_BE_DECIDED,
    attr,
    balanced_div,
    div_block,
    fetch_page,
    kda_ratio,
    mark_finals,
    need,
    need_attr,
    need_tag,
    parse_html,
    parse_record,
    text_of,
    to_int,
)
from app.utils.ttl_cache import ttl_cache

_MANILA = timezone(timedelta(hours=8))
_WEEK_ID = re.compile(r"^week-\d+$")
_BACKGROUND_URL = re.compile(r"url\('([^']+)'\)")
_SCORE = re.compile(r"(\d+)\s*:\s*(\d+)")
_CSRF_TOKEN = re.compile(r'_token: "([^"]+)"')
_BATTLE_IDS = re.compile(r"loadItemSequence\('(\d+)',\s*'(\d+)'\)")
_LEFT_PERCENT = re.compile(r"left:\s*([\d.]+)%")
_TIER = re.compile(r"tier-(\d+)")


def _asset_from(source: str) -> Asset:
    # Image files are named after the item, emblem or talent id.
    return Asset(id=source.rsplit("/", 1)[1].split(".")[0], image=source)


def _start_at(label: str, local_time: str) -> str | None:
    try:
        started = datetime.strptime(f"{label} {local_time}", "%A, %d %B %Y %I:%M %p")
    except ValueError:
        return None
    return started.replace(tzinfo=_MANILA).astimezone(UTC).isoformat()


def _standing(row: Tag) -> Standing:
    rank, team, match_point, match_wl, net_game_win, game_wl = (text_of(cell) for cell in row.find_all("td", recursive=False))
    logo = _BACKGROUND_URL.search(attr(row.select_one(".team-logo"), "style") or "")
    return Standing(
        rank=to_int(rank),
        team=Team(name=team, logo=logo.group(1) if logo else None),
        match_point=to_int(match_point),
        match_wl=parse_record(match_wl),
        net_game_win=to_int(net_game_win),
        game_wl=parse_record(game_wl),
    )


@ttl_cache(CACHE_SECONDS)
def get_standings() -> list[Standing]:
    soup = parse_html(fetch_page(EsportsSourceProvider.get_ph_base_url(), "/").text)
    return [_standing(row) for row in soup.select("#standing-regular-season #table-group tbody tr")]


def _team(name: str, logo: str) -> Team:
    # Undecided playoff sides carry the league's own logo, which is left out.
    return Team(name=name, logo=None if name == TO_BE_DECIDED else logo)


def _schedule_match(item: Tag, label: str, best_of: int) -> ScheduleMatch:
    local_time = text_of(item.find("div"))
    names = [text_of(name) for name in item.select(".team-name")]
    logos = [need_attr(image, "src") for image in item.select("img")]
    score = _SCORE.search(text_of(item.select_one(".mt-n2")))
    href = attr(item.select_one("a[href*='/data/match/']"), "href")
    return ScheduleMatch(
        match_id=href.rsplit("/", 1)[1] if href else None,
        start_at=_start_at(label, local_time),
        local_time=local_time,
        team1=_team(names[0], logos[0]),
        team2=_team(names[1], logos[1]),
        score1=int(score.group(1)) if score else None,
        score2=int(score.group(2)) if score else None,
        best_of=best_of,
    )


def _schedule_day(header: Tag, best_of: int = REGULAR_SEASON_BEST_OF) -> ScheduleDay:
    label = text_of(header.select_one(".match-category-day"))
    day = re.search(r"\d+", text_of(header.select_one(".match-category-day-no")))
    block = need_tag(header.find_parent(class_="col-lg-4"), "a schedule day")
    return ScheduleDay(
        day=int(day[0]) if day else None,
        label=label,
        matches=[_schedule_match(item, label, best_of) for item in block.select(".schedule-item")],
    )


@ttl_cache(CACHE_SECONDS)
def _schedule_page() -> tuple[list[ScheduleWeek], list[ScheduleDay], str | None]:
    """Regular-season weeks, playoff days and the bracket image, from one fetch of the schedule page."""
    soup = parse_html(fetch_page(EsportsSourceProvider.get_ph_base_url(), "/schedule").text)
    panes = [(need_attr(pane, "id"), pane) for pane in soup.select("#regular-season .tab-pane")]
    weeks = [
        ScheduleWeek(
            week=int(pane_id.rsplit("-", 1)[1]),
            days=[_schedule_day(header) for header in pane.select(".match-category-flex")],
        )
        for pane_id, pane in panes
        if _WEEK_ID.match(pane_id)
    ]
    # The playoff cards appear twice on the page; the first "playoffs" block is the schedule tab.
    playoffs = soup.find(id="playoffs")
    days = [_schedule_day(header, PLAYOFFS_BEST_OF) for header in playoffs.select(".match-category-flex")] if playoffs else []
    mark_finals(days)
    bracket = attr(playoffs.select_one(".playoffs-bracket img"), "src") if playoffs else None
    return weeks, days, bracket


def get_schedule() -> list[ScheduleWeek]:
    return _schedule_page()[0]


def get_playoffs() -> PlayoffsResponse:
    _, days, bracket = _schedule_page()
    table = get_standings()
    return PlayoffsResponse(
        bracket_image=bracket,
        seeds=[PlayoffSeed(seed=row.rank, team=row.team, match_wl=row.match_wl) for row in table[: len(table) - PH_ELIMINATED]],
        days=days,
    )


# A match page is 0.8 MB, mostly whitespace and inline styles in the scoreboard. Building a BeautifulSoup tree
# of it went over a Cloudflare Worker's CPU budget (error 1102), so the games are sliced out of the text and
# read with these regexes.
_GAME_START = re.compile(r'<div class="tab-content clearfix" id="game(\d+)"')
_TAG = re.compile(r"<!--.*?-->|<[^>]+>", re.S)
_IMG_SRC = re.compile(r'<img\b[^>]*?\bsrc="([^"]*)"')
_LINK = re.compile(r'<(?:a|iframe|source)\b[^>]*?\b(?:href|src)="(http[^"]*)"')
_SHORT_NAME = re.compile(r'class="card col-lg-5[^"]*team-name"[^>]*>.*?<h3[^>]*>(.*?)</h3>', re.S)
_SUMMARY_ROW = re.compile(
    r'class="stats-num[^"]*">(.*?)</div>\s*<div class="stats-divider[^"]*">(.*?)</div>\s*<div class="stats-num[^"]*">(.*?)</div>', re.S
)
_TABLE = re.compile(r"<table\b.*?</table>", re.S)
_HEADING = re.compile(r"<h3[^>]*>(.*?)</h3>", re.S)
_HEADER_CELL = re.compile(r"<th\b.*?</th>", re.S)
_ROW = re.compile(r"<tr\b.*?</tr>", re.S)
_CELL = re.compile(r"<td\b.*?</td>", re.S)
_PLAYER_EQUIPS = re.compile(r'<div class="team-player-equips\b[^"]*"[^>]*>')
_DOT = re.compile(r'class="item-dots\b[^"]*"\s+style="([^"]*)"(.*?)<img\b[^>]*?\bsrc="([^"]*)"', re.S)


def _plain(markup: str) -> str:
    return unescape(" ".join(_TAG.sub(" ", markup).split()))


def _tab(pane: str, name: str) -> str:
    return div_block(pane, f'id="{name}"')


def _summary(summary: str) -> list[dict[str, int]]:
    """Per-team totals from the summary tab, keyed by the row label (``total_gold``, ``red_buff``...)."""
    totals: tuple[dict[str, int], dict[str, int]] = ({}, {})
    for first, label, second in _SUMMARY_ROW.findall(summary):
        key = re.sub(r"\W+", "_", _plain(label).lower().replace("/", " per ")).strip("_")
        totals[0][key], totals[1][key] = to_int(_plain(first)), to_int(_plain(second))
    return list(totals)


def _player(row: str, columns: dict[str, int]) -> Player:
    cells = _CELL.findall(row)

    def text(column: str) -> str:
        return _plain(cells[columns[column]])

    def assets(column: str) -> list[Asset]:
        return [_asset_from(unescape(source)) for source in _IMG_SRC.findall(cells[columns[column]])]

    kills, deaths, assists = (to_int(text(column)) for column in ("Kill", "Death", "Assist"))
    hero_image = _IMG_SRC.search(cells[columns["Hero"]])
    emblems = assets("Emblems")
    return Player(
        name=text("Player"),
        hero=Hero(name=text("Hero"), image=unescape(need(hero_image, "a hero image")[1])),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=kda_ratio(kills, deaths, assists),
        items=assets("Items"),
        emblem=emblems[0] if emblems else None,
        talents=assets("Talents"),
        gold=to_int(text("Gold")),
        damage_dealt=to_int(text("Hero Damage")),
        damage_taken=to_int(text("Damage Taken")),
        tower_damage=to_int(text("Tower Damage")),
    )


def _scoreboard(scoreboard: str, short_names: list[str]) -> list[tuple[Team, list[Player]]]:
    """Each team (short name from the summary tab, full name and logo from the heading above its table) and its players."""
    sides = []
    heading_start = 0
    for short_name, table in zip(short_names, _TABLE.finditer(scoreboard)):
        heading = scoreboard[heading_start : table.start()]
        heading_start = table.end()
        columns = {_plain(header): index for index, header in enumerate(_HEADER_CELL.findall(table[0]))}
        body = table[0][table[0].find("<tbody") :]
        team = Team(
            name=short_name,
            full_name=_plain(need(_HEADING.search(heading), "a team heading")[1]),
            logo=unescape(need(_IMG_SRC.search(heading), "a team logo")[1]),
        )
        sides.append((team, [_player(row, columns) for row in _ROW.findall(body)]))
    return sides


def _item_sequences(html: str) -> tuple[list[int], list[list[SequenceItem]]]:
    """Timeline axis minutes and, per player (team 1 first), the items in purchase order."""
    axis = [int(minute) for minute in _plain(div_block(html, 'class="equips-divider')).split()]
    rows = _PLAYER_EQUIPS.split(html)[1:]
    sequences = [
        [
            SequenceItem(
                **_asset_from(unescape(source)).model_dump(),
                tier=int(tier[1]) if (tier := _TIER.search(between)) else None,
                timeline_percent=float(need(_LEFT_PERCENT.search(style), "an item position").group(1)),
            )
            for style, between, source in _DOT.findall(row)
        ]
        for row in rows
    ]
    return axis, sequences


def _duration_estimate(totals: list[dict[str, int]]) -> int | None:
    """Game length in seconds from total gold over gold per minute, averaged over both teams."""
    minutes = [side["total_gold"] / side["gold_per_min"] for side in totals if side.get("total_gold") and side.get("gold_per_min")]
    return round(sum(minutes) / len(minutes) * 60) if minutes else None


def _media(pane: str) -> tuple[list[str], list[str]]:
    """Highlight video links and screenshot images of one game."""
    highlights = [unescape(link) for link in _LINK.findall(_tab(pane, "highlight"))]
    screenshots = [unescape(source) for source in _IMG_SRC.findall(_tab(pane, "screenshots"))]
    return list(dict.fromkeys(highlights)), list(dict.fromkeys(screenshots))


def _game_panes(html: str) -> list[tuple[int, str]]:
    return [(int(found[1]), balanced_div(html, found.start())) for found in _GAME_START.finditer(html)]


@ttl_cache(CACHE_SECONDS)
def get_match(slug: str) -> MatchDetailResponse:
    base_url = EsportsSourceProvider.get_ph_base_url()
    page = fetch_page(base_url, f"/data/match/{slug}")
    token = need(_CSRF_TOKEN.search(page.text), "the CSRF token").group(1)
    battle_ids = dict(_BATTLE_IDS.findall(page.text))
    # The item sequences are a CSRF-protected POST tied to this page's session.
    headers = {
        **UpstreamHeaderBuilder.get_esports_header(base_url),
        "Cookie": "; ".join(f"{name}={value}" for name, value in page.cookies.items()),
        "X-Requested-With": "XMLHttpRequest",
    }

    games = []
    for number, pane in _game_panes(page.text):
        summary = _tab(pane, "summary")
        short_names = [_plain(name) for name in _SHORT_NAME.findall(summary)]
        totals = _summary(summary)
        sides = _scoreboard(_tab(pane, "scoreboard"), short_names)
        axis, sequences = _item_sequences(
            request_page(
                method="POST",
                url=f"{base_url}/data/match-data/itemization",
                headers=headers,
                payload={"_token": token, "battleId": battle_ids[str(number)], "matchName": slug},
            ).json()["data"]
        )
        seconds = _duration_estimate(totals)
        highlights, screenshots = _media(pane)
        players = [player for _, side_players in sides for player in side_players]
        for player, sequence in zip(players, sequences):
            player.item_sequence = sequence
        games.append(
            Game(
                number=number,
                duration=None,
                duration_estimate=f"{seconds // 60}:{seconds % 60:02d}" if seconds is not None else None,
                duration_estimate_seconds=seconds,
                timeline_minutes=axis,
                teams=[
                    GameTeam(
                        team=team,
                        winner=None,
                        kills=side_totals.pop("total_kills"),
                        stats=side_totals,
                        players=side_players,
                    )
                    for side_totals, (team, side_players) in zip(totals, sides)
                ],
                highlights=highlights,
                screenshots=screenshots,
            )
        )
    return MatchDetailResponse(match_id=slug, games=games)
