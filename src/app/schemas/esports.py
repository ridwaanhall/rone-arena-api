from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, computed_field

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
    # Bracket round as the league names it ("Upper Bracket Finals"); playoffs of the Indonesian league only.
    round: str | None = None
    # Games in the series: 3 in the regular season, 5 in the playoffs, 7 in the lower bracket final and grand final.
    best_of: int = 3

    @computed_field
    @property
    def status(self) -> Literal["scheduled", "in_progress", "finished"]:
        if self.score1 is None or self.score2 is None:
            return "scheduled"
        return "finished" if max(self.score1, self.score2) > self.best_of // 2 else "in_progress"

    @computed_field
    @property
    def winner(self) -> Literal["team1", "team2"] | None:
        if self.status != "finished":
            return None
        return "team1" if (self.score1 or 0) > (self.score2 or 0) else "team2"


class ScheduleDay(BaseModel):
    day: int | None = None
    label: str
    matches: list[ScheduleMatch]


class ScheduleWeek(BaseModel):
    week: int
    days: list[ScheduleDay]


class ScheduleResponse(BaseModel):
    weeks: list[ScheduleWeek]


class PlayoffSeed(BaseModel):
    seed: int
    team: Team
    # Regular-season match record.
    match_wl: Record


class PlayoffsResponse(BaseModel):
    bracket_image: Image | None
    # Regular-season rank of each playoff team, best first.
    seeds: list[PlayoffSeed]
    days: list[ScheduleDay]


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
    # Philippine league only, which publishes no game clock: total gold divided by gold per minute,
    # averaged over both teams. Close to the real length (the figures are rounded), never exact.
    duration_estimate: str | None = None
    duration_estimate_seconds: int | None = None
    # Minute labels of the item-sequence timeline axis (Philippine league only).
    timeline_minutes: list[int] = []
    teams: list[GameTeam]
    # Video links and screenshots the Philippine league attaches to a game; often empty.
    highlights: list[str] = []
    screenshots: list[Image] = []


class MatchDetailResponse(BaseModel):
    match_id: str
    games: list[Game]


# ---- teams


class SocialLink(BaseModel):
    # facebook, instagram, youtube, x, tiktok... (from the link's host).
    platform: str
    url: str


class TeamSummary(BaseModel):
    # Value for the league's team endpoint.
    team_id: str
    # Short name, as the schedule and standings write it.
    name: str
    full_name: str | None = None
    logo: Image | None = None


class TeamsResponse(BaseModel):
    teams: list[TeamSummary]


class PlayerSeasonStats(BaseModel):
    """A player's regular-season totals, as the league prints them on the team page (Malaysian league only)."""

    matches: int
    kills: int
    deaths: int
    assists: int
    kda: float
    savage: int | None = None
    maniac: int | None = None


class RosterMember(BaseModel):
    # Value for the league's player endpoint (Cambodian league only); null elsewhere.
    player_id: str | None = None
    name: str
    # Role as the league names it: "Roam", "Gold Lane", "Coach", "Analyst"...
    role: str
    photo: Image | None = None
    # Further details only the Malaysian league publishes; null or empty elsewhere.
    archetype: str | None = None
    secondary_role: str | None = None
    tier: str | None = None
    birth_date: str | None = None
    age: int | None = None
    nationality: str | None = None
    hometown: str | None = None
    previous_team: Team | None = None
    socials: list[SocialLink] = []
    stats: PlayerSeasonStats | None = None


class Achievement(BaseModel):
    title: str
    # "1st", "5th - 8th"...; null when the league gives none.
    placement: str | None = None
    # Cambodian league only: the date (YYYY-MM-DD), the event's tier ("S-Tier") and the prize, as the league writes them.
    date: str | None = None
    tier: str | None = None
    prize: str | None = None


class TeamStats(BaseModel):
    """Team totals the league prints on the team page (Cambodian league only); a figure it leaves out is null."""

    # "MPL KH S11" for the season, "Career" for all seasons together.
    label: str
    matches_played: int | None = None
    games_played: int | None = None
    match_wl: Record | None = None
    game_wl: Record | None = None
    # Percent of matches won.
    win_rate: float | None = None
    kills: int | None = None
    gold: int | None = None
    damage: int | None = None
    lord: int | None = None
    tortoise: int | None = None
    tower: int | None = None


class TeamMatch(ScheduleMatch):
    stage: Literal["regular_season", "playoffs"]
    # Regular-season week; null in the playoffs.
    week: int | None
    day_label: str
    opponent: Team
    # From this team's side; null until the match is finished.
    result: Literal["win", "loss"] | None


class TeamDetailResponse(TeamSummary):
    # Season the roster is for, as the league states it.
    season: int | None = None
    tagline: str | None = None
    description: str | None = None
    socials: list[SocialLink] = []
    team_photo: Image | None = None
    gallery: list[Image] = []
    # Team entrance music (Malaysian league only); a signed link that expires within hours.
    entrance_music: str | None = None
    achievements: list[Achievement] = []
    # Further facts the league lists about the team ("region", "owner", "manager"); Cambodian league only.
    profile: dict[str, str] = {}
    # Season and career totals (Cambodian league only).
    stats: list[TeamStats] = []
    players: list[RosterMember]
    # Coaches, analysts and managers.
    staff: list[RosterMember]
    # Regular-season standing; null before the league publishes the table.
    standing: Standing | None = None
    # Every regular-season and playoff match of the team, in schedule order.
    matches: list[TeamMatch] = []


class PlayerStats(BaseModel):
    """A player's totals as the league prints them (Cambodian league only); a figure it leaves out is null."""

    # "MPL KH S11" for the season, "Career" for all seasons together.
    label: str
    heroes_played: int | None = None
    mvp_points: int | None = None
    matches_played: int | None = None
    games_played: int | None = None
    kills: int | None = None
    assists: int | None = None
    gold: int | None = None
    gold_per_min: int | None = None
    damage_dealt: int | None = None
    damage_taken: int | None = None
    tower_damage: int | None = None


class TeamHistoryEntry(BaseModel):
    # Value for the team endpoint; null when the league has no page for the team.
    team_id: str | None
    name: str
    # As the league writes it: "2026 – Present".
    period: str | None


class PlayerDetailResponse(BaseModel):
    player_id: str
    name: str
    role: str
    photo: Image | None = None
    # The player's current team.
    team: TeamSummary | None = None
    # Biography facts as the league lists them ("full_name", "based"...).
    profile: dict[str, str] = {}
    team_history: list[TeamHistoryEntry] = []
    stats: list[PlayerStats] = []


# ---- season statistics


class TeamStatistics(BaseModel):
    team: Team
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    gold: int | None = None
    damage: int | None = None
    lord: int | None = None
    tortoise: int | None = None
    tower: int | None = None


class TeamStatisticsResponse(BaseModel):
    teams: list[TeamStatistics]


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    team: Team | None = None
    photo: Image | None = None
    hero: Hero | None = None
    # The figure ranked: a total, an average, a KDA or a percentage, as the board says.
    value: float


class Leaderboard(BaseModel):
    # As the league names it: "Top 5 Kills", "KDA Ranking", "Top 5 Hero Pick"...
    title: str
    entries: list[LeaderboardEntry]


class PlayerStatistics(BaseModel):
    name: str
    team: Team | None = None
    role: str | None = None
    games: int | None = None
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    avg_kills: float | None = None
    avg_deaths: float | None = None
    avg_assists: float | None = None
    kda: float | None = None
    # Percent of the team's kills the player took part in.
    kill_participation: float | None = None


class PlayerStatisticsResponse(BaseModel):
    leaderboards: list[Leaderboard]
    players: list[PlayerStatistics]


class HeroStatistics(BaseModel):
    hero: Hero
    picks: int
    bans: int
    wins: int
    # Percentages; the rates of picks and bans are published by the Philippine league only.
    pick_rate: float | None = None
    ban_rate: float | None = None
    win_rate: float | None = None


class HeroStatisticsResponse(BaseModel):
    leaderboards: list[Leaderboard]
    heroes: list[HeroStatistics]


class PoolHero(BaseModel):
    hero: Hero
    picks: int
    win_rate: float | None


class HeroPool(BaseModel):
    """The heroes one player has played this season (Indonesian league only)."""

    name: str
    team: Team | None = None
    role: str | None = None
    # Different heroes played.
    total: int
    heroes: list[PoolHero]


class HeroPoolsResponse(BaseModel):
    players: list[HeroPool]


class PoolPlayer(BaseModel):
    name: str
    team: Team | None = None
    photo: Image | None = None
    picks: int
    win_rate: float | None


class PlayerPool(BaseModel):
    """The players who have played one hero this season (Indonesian league only)."""

    hero: Hero
    # Different players who played it.
    total: int
    players: list[PoolPlayer]


class PlayerPoolsResponse(BaseModel):
    heroes: list[PlayerPool]


class MvpStanding(BaseModel):
    rank: int
    name: str
    team: Team | None = None
    photo: Image | None = None
    points: int


class MvpStandingsResponse(BaseModel):
    standings: list[MvpStanding]


class SavageManiac(BaseModel):
    name: str
    team: Team | None = None
    savage: int
    maniac: int


class SavageManiacResponse(BaseModel):
    players: list[SavageManiac]


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
    eliminated: int | None = Field(default=None, ge=0, le=19, description="Teams that miss the playoffs (the bottom of the table). Default: 3 for Indonesia, 2 for the Philippines, 2 for Malaysia, 4 for Cambodia.")
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
