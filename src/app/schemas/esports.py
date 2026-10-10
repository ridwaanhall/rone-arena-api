from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

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


# ---- standings simulator


class MatchResult(BaseModel):
    """One edited match. Either team order is accepted; scores are games won in a first-to-2 match."""

    week: int = Field(ge=1, description="Week of the match.")
    team1: str = Field(min_length=1, max_length=40)
    team2: str = Field(min_length=1, max_length=40)
    score1: int | None = Field(default=None, ge=0, le=2, description="Games won by team1. Omit both scores to mark the match as not played.")
    score2: int | None = Field(default=None, ge=0, le=2, description="Games won by team2.")


ProbabilityModel = Literal["form", "even"]
_MODEL_HELP = (
    "How the chance of the matches still to play is set: `form` (default) from each team's record so far, or `even` for a coin flip."
)
_SIMULATIONS_HELP = "How many seasons to simulate for the playoff probability (100 to 20000). Omit it to let the server choose from how many matches are left."


class SimulateRequest(BaseModel):
    results: list[MatchResult] = Field(default_factory=list, max_length=400, description="Matches to set or clear. Everything else keeps the real result.")
    eliminated: int | None = Field(default=None, ge=0, le=19, description="Teams that miss the playoffs (the bottom of the table). Default: 3 for Indonesia, 2 for the Philippines.")
    model: ProbabilityModel = Field(default="form", description=_MODEL_HELP)
    simulations: int | None = Field(default=None, ge=100, le=20000, description=_SIMULATIONS_HELP)


class CalculateRequest(BaseModel):
    teams: list[Annotated[str, Field(min_length=1, max_length=40)]] | None = Field(
        default=None, max_length=20, description="Team names, 2 to 20, all different. Omit to use Team A, Team B, ... with **team_count**."
    )
    team_count: int = Field(default=8, ge=2, le=20, description="Number of teams when **teams** is omitted.")
    eliminated: int | None = Field(default=None, ge=0, le=19, description="Teams that miss the playoffs. Default: 3, or fewer when the league is small.")
    results: list[MatchResult] = Field(default_factory=list, max_length=400)
    model: ProbabilityModel = Field(default="form", description=_MODEL_HELP)
    simulations: int | None = Field(default=None, ge=100, le=20000, description=_SIMULATIONS_HELP)


class SimulatedMatch(BaseModel):
    team1: Team
    team2: Team
    score1: int | None
    score2: int | None
    # played: the real result · edited: set by this request · scheduled: no result yet
    state: Literal["played", "edited", "scheduled"]


class SimulatedWeek(BaseModel):
    week: int
    matches: list[SimulatedMatch]


class SimulatedStanding(BaseModel):
    rank: int
    team: Team
    match_point: int
    match_wl: Record
    net_game_win: int
    game_wl: Record
    played: int
    remaining: int
    max_match_point: int
    # How this team was separated from teams on the same match points.
    tiebreak: Literal["net_game_win", "head_to_head", "unresolved"] | None
    # clinched: certain to be in the playoffs · eliminated: certain to miss them · alive: undecided
    status: Literal["clinched", "alive", "eliminated"]
    in_playoffs_zone: bool
    # Percent chance (full precision) of finishing in the playoff spots; exactly 100 or 0 once decided.
    playoff_probability: float


class StandingsSimulationResponse(BaseModel):
    teams: int
    weeks_count: int
    playoff_spots: int
    eliminated: int
    matches_played: int
    matches_remaining: int
    edited_matches: int
    probability_model: ProbabilityModel
    # Seasons simulated for the probabilities; 0 when every team is already decided and the chances are exact.
    probability_simulations: int
    weeks: list[SimulatedWeek]
    standings: list[SimulatedStanding]
