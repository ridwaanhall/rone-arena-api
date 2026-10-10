from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel

from app.core.images import wsrv_url

# Image URLs scraped from the league sites are served through the image proxy too.
Image = Annotated[str, AfterValidator(wsrv_url)]


class Team(BaseModel):
    name: str
    full_name: str | None = None
    logo: Image | None = None


class Record(BaseModel):
    win: int
    lose: int


class ScheduleMatch(BaseModel):
    # Value to pass to the league's matches endpoint; null when no details page exists yet.
    match_id: str | None
    start_at: str | None
    local_time: str
    team1: Team
    team2: Team
    # Both scores are null until the match has been played.
    score1: int | None
    score2: int | None
    replay_url: str | None = None


class ScheduleDay(BaseModel):
    day: int | None = None
    label: str
    matches: list[ScheduleMatch]


class ScheduleWeek(BaseModel):
    week: int
    days: list[ScheduleDay]


class ScheduleResponse(BaseModel):
    weeks: list[ScheduleWeek]


class Standing(BaseModel):
    rank: int
    team: Team
    match_point: int
    match_wl: Record
    net_game_win: int
    game_wl: Record


class StandingsResponse(BaseModel):
    standings: list[Standing]


class Hero(BaseModel):
    name: str
    image: Image | None = None


class Asset(BaseModel):
    id: str
    image: Image


class SequenceItem(Asset):
    tier: int | None = None
    # Position on the match timeline, 0-100 (share of the game's length).
    timeline_percent: float


class Player(BaseModel):
    name: str
    hero: Hero
    kills: int
    deaths: int
    assists: int
    kda: float
    items: list[Asset]
    emblem: Asset | None
    talents: list[Asset]
    gold: int | None
    damage_dealt: int | None
    damage_taken: int | None
    tower_damage: int | None
    # Purchase order of items; only the Philippine league publishes it.
    item_sequence: list[SequenceItem] = []


class GameTeam(BaseModel):
    team: Team
    # Null when the league does not state the winner of a game.
    winner: bool | None
    kills: int
    # Further team totals (gold, damage, objectives); empty when the league publishes none.
    stats: dict[str, int]
    players: list[Player]


class Game(BaseModel):
    number: int
    duration: str | None
    # Minute labels of the item-sequence timeline axis (Philippine league only).
    timeline_minutes: list[int] = []
    teams: list[GameTeam]


class MatchDetailResponse(BaseModel):
    match_id: str
    games: list[Game]
