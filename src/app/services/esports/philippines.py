"""Scraper for the Philippine league site: schedule, standings and match details."""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone

from bs4.element import Tag

from app.core.http import UpstreamHeaderBuilder, request_page
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
    SequenceItem,
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

_MANILA = timezone(timedelta(hours=8))
_WEEK_ID = re.compile(r"^week-\d+$")
_GAME_ID = re.compile(r"^game\d+$")
_BACKGROUND_URL = re.compile(r"url\('([^']+)'\)")
_SCORE = re.compile(r"(\d+)\s*:\s*(\d+)")
_CSRF_TOKEN = re.compile(r'_token: "([^"]+)"')
_BATTLE_IDS = re.compile(r"loadItemSequence\('(\d+)',\s*'(\d+)'\)")
_LEFT_PERCENT = re.compile(r"left:\s*([\d.]+)%")
_TIER = re.compile(r"tier-(\d+)")


def _asset(image: Tag) -> Asset:
    # Image files are named after the item, emblem or talent id.
    source = need_attr(image, "src")
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


def _schedule_match(item: Tag, label: str) -> ScheduleMatch:
    local_time = text_of(item.find("div"))
    names = [text_of(name) for name in item.select(".team-name")]
    logos = [need_attr(image, "src") for image in item.select("img")]
    score = _SCORE.search(text_of(item.select_one(".mt-n2")))
    href = attr(item.select_one("a[href*='/data/match/']"), "href")
    return ScheduleMatch(
        match_id=href.rsplit("/", 1)[1] if href else None,
        start_at=_start_at(label, local_time),
        local_time=local_time,
        team1=Team(name=names[0], logo=logos[0]),
        team2=Team(name=names[1], logo=logos[1]),
        score1=int(score.group(1)) if score else None,
        score2=int(score.group(2)) if score else None,
    )


def _schedule_day(header: Tag) -> ScheduleDay:
    label = text_of(header.select_one(".match-category-day"))
    day = re.search(r"\d+", text_of(header.select_one(".match-category-day-no")))
    block = need_tag(header.find_parent(class_="col-lg-4"), "a schedule day")
    return ScheduleDay(
        day=int(day[0]) if day else None,
        label=label,
        matches=[_schedule_match(item, label) for item in block.select(".schedule-item")],
    )


@ttl_cache(CACHE_SECONDS)
def get_schedule() -> list[ScheduleWeek]:
    soup = parse_html(fetch_page(EsportsSourceProvider.get_ph_base_url(), "/schedule").text)
    panes = [(need_attr(pane, "id"), pane) for pane in soup.select("#regular-season .tab-pane")]
    return [
        ScheduleWeek(
            week=int(pane_id.rsplit("-", 1)[1]),
            days=[_schedule_day(header) for header in pane.select(".match-category-flex")],
        )
        for pane_id, pane in panes
        if _WEEK_ID.match(pane_id)
    ]


def _summary(pane: Tag) -> list[dict[str, int]]:
    """Per-team totals from the summary tab, keyed by the row label (``total_gold``, ``red_buff``...)."""
    totals: tuple[dict[str, int], dict[str, int]] = ({}, {})
    for divider in pane.select("#summary .stats-divider"):
        label = re.sub(r"\W+", "_", text_of(divider).lower().replace("/", " per ")).strip("_")
        for team_totals, value in zip(totals, need(divider.parent, "a summary row").select(".stats-num")):
            team_totals[label] = to_int(text_of(value))
    return list(totals)


def _player(row: Tag, columns: dict[str, int]) -> Player:
    cells = row.find_all("td", recursive=False)

    def cell(column: str) -> Tag:
        return cells[columns[column]]

    hero = cell("Hero")
    kills, deaths, assists = (to_int(text_of(cell(column))) for column in ("Kill", "Death", "Assist"))
    return Player(
        name=text_of(cell("Player")),
        hero=Hero(name=text_of(hero), image=need_attr(hero.find("img"), "src")),
        kills=kills,
        deaths=deaths,
        assists=assists,
        kda=kda_ratio(kills, deaths, assists),
        items=[_asset(image) for image in cell("Items").find_all("img")],
        emblem=next((_asset(image) for image in cell("Emblems").find_all("img")), None),
        talents=[_asset(image) for image in cell("Talents").find_all("img")],
        gold=to_int(text_of(cell("Gold"))),
        damage_dealt=to_int(text_of(cell("Hero Damage"))),
        damage_taken=to_int(text_of(cell("Damage Taken"))),
        tower_damage=to_int(text_of(cell("Tower Damage"))),
    )


def _scoreboard(pane: Tag, short_names: list[str]) -> list[tuple[Team, list[Player]]]:
    """Each team (short name from the summary tab, full name and logo from here) and its players."""
    sides = []
    for short_name, table in zip(short_names, pane.select("#scoreboard table")):
        columns = {text_of(header): index for index, header in enumerate(table.select("thead th"))}
        card = need_tag(table.find_parent(class_="container"), "a team card")
        team = Team(name=short_name, full_name=text_of(card.select_one("h3")), logo=need_attr(card.select_one("img"), "src"))
        sides.append((team, [_player(row, columns) for row in table.select("tbody tr")]))
    return sides


def _item_sequences(html: str) -> tuple[list[int], list[list[SequenceItem]]]:
    """Timeline axis minutes and, per player (team 1 first), the items in purchase order."""
    soup = parse_html(html)
    axis = [int(minute) for minute in text_of(soup.select_one(".equips-divider")).split()]
    sequences = [
        [
            SequenceItem(
                **_asset(need_tag(dot.find("img"), "an item image")).model_dump(),
                tier=int(tier[1]) if (tier := _TIER.search(attr(dot.select_one(".equip-item-img"), "class") or "")) else None,
                timeline_percent=float(need(_LEFT_PERCENT.search(need_attr(dot, "style")), "an item position").group(1)),
            )
            for dot in row.select(".item-dots")
        ]
        for row in soup.select(".team-player-equips")
    ]
    return axis, sequences


@ttl_cache(CACHE_SECONDS)
def get_match(slug: str) -> MatchDetailResponse:
    base_url = EsportsSourceProvider.get_ph_base_url()
    page = fetch_page(base_url, f"/data/match/{slug}")
    soup = parse_html(page.text)
    token = need(_CSRF_TOKEN.search(page.text), "the CSRF token").group(1)
    battle_ids = dict(_BATTLE_IDS.findall(page.text))
    # The item sequences are a CSRF-protected POST tied to this page's session.
    headers = {
        **UpstreamHeaderBuilder.get_esports_header(base_url),
        "Cookie": "; ".join(f"{name}={value}" for name, value in page.cookies.items()),
        "X-Requested-With": "XMLHttpRequest",
    }

    games = []
    for pane in soup.find_all(id=_GAME_ID):
        number = int(need_attr(pane, "id").removeprefix("game"))
        short_names = [text_of(name) for name in pane.select("#summary .team-name h3")]
        totals = _summary(pane)
        sides = _scoreboard(pane, short_names)
        axis, sequences = _item_sequences(
            request_page(
                method="POST",
                url=f"{base_url}/data/match-data/itemization",
                headers=headers,
                payload={"_token": token, "battleId": battle_ids[str(number)], "matchName": slug},
            ).json()["data"]
        )
        players = [player for _, side_players in sides for player in side_players]
        for player, sequence in zip(players, sequences):
            player.item_sequence = sequence
        games.append(
            Game(
                number=number,
                duration=None,
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
            )
        )
    return MatchDetailResponse(match_id=slug, games=games)
