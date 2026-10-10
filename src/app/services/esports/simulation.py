"""Standings simulations: the engine in `standings.py` applied to a live or generated season."""
from __future__ import annotations

from app.core.enums import LeagueEnum, LeagueLanguageEnum
from app.core.exceptions import AppError
from app.schemas.esports import (
    CalculateRequest,
    MatchResult,
    Record,
    ScheduleWeek,
    SimulatedMatch,
    SimulatedStanding,
    SimulatedWeek,
    SimulateRequest,
    Standing,
    StandingsSimulationResponse,
    Team,
)
from app.services.esports import indonesia, philippines, probability, standings

# Teams that miss the playoffs by default.
DEFAULT_ELIMINATED = {LeagueEnum.INDONESIA: 3, LeagueEnum.PHILIPPINES: 2}
CUSTOM_ELIMINATED = 3


def _results(items: list[MatchResult]) -> list[tuple[int, str, str, int | None, int | None]]:
    return [(item.week, item.team1, item.team2, item.score1, item.score2) for item in items]


def _build(
    teams: dict[str, Team],
    matches: list[standings.Match],
    eliminated: int,
    model: str,
    simulations: int | None,
) -> StandingsSimulationResponse:
    rows = standings.compute_standings(list(teams), matches, eliminated)
    spots = len(teams) - eliminated
    chances, simulated = probability.playoff_probabilities(list(teams), matches, rows, spots, model, simulations)
    weeks: dict[int, list[SimulatedMatch]] = {}
    for match in matches:
        weeks.setdefault(match.week, []).append(
            SimulatedMatch(
                team1=teams[match.team1],
                team2=teams[match.team2],
                score1=match.score1,
                score2=match.score2,
                state=match.state,
            )
        )
    played = sum(1 for match in matches if match.done)
    return StandingsSimulationResponse(
        teams=len(teams),
        weeks_count=len(weeks),
        playoff_spots=spots,
        eliminated=eliminated,
        matches_played=played,
        matches_remaining=len(matches) - played,
        edited_matches=sum(1 for match in matches if match.state == "edited"),
        probability_model=model,
        probability_simulations=simulated,
        weeks=[SimulatedWeek(week=week, matches=items) for week, items in sorted(weeks.items())],
        standings=[
            SimulatedStanding(
                rank=row.rank,
                team=teams[row.team],
                match_point=row.won,
                match_wl=Record(win=row.won, lose=row.lost),
                net_game_win=row.net,
                game_wl=Record(win=row.games_won, lose=row.games_lost),
                played=row.played,
                remaining=row.remaining,
                max_match_point=row.max_points,
                tiebreak=row.tiebreak,
                status=row.status,
                in_playoffs_zone=row.rank <= spots,
                playoff_probability=chances[row.team],
            )
            for row in rows
        ],
    )


def _from_schedule(weeks: list[ScheduleWeek], known: list[Standing]) -> tuple[dict[str, Team], list[standings.Match]]:
    """Teams (with logos and full names) and matches of the league's real schedule."""
    teams: dict[str, Team] = {item.team.name: item.team for item in known}
    matches: list[standings.Match] = []
    for week in weeks:
        for day in week.days:
            for item in day.matches:
                for team in (item.team1, item.team2):
                    teams.setdefault(team.name, team)
                done = item.score1 is not None and item.score2 is not None
                matches.append(
                    standings.Match(
                        week=week.week,
                        team1=item.team1.name,
                        team2=item.team2.name,
                        score1=item.score1,
                        score2=item.score2,
                        state="played" if done else "scheduled",
                    )
                )
    return teams, matches


def simulate_league(league: LeagueEnum, request: SimulateRequest) -> StandingsSimulationResponse:
    if league is LeagueEnum.INDONESIA:
        weeks, known = indonesia.get_season(LeagueLanguageEnum.ENGLISH.value)
    else:
        weeks, known = philippines.get_schedule(), philippines.get_standings()
    teams, matches = _from_schedule(weeks, known)
    if not matches:
        raise AppError(status_code=502, code="UPSTREAM_REQUEST_FAILED", message="The league schedule is not available right now.")
    standings.apply_results(matches, _results(request.results))
    eliminated = DEFAULT_ELIMINATED[league] if request.eliminated is None else request.eliminated
    return _build(teams, matches, eliminated, request.model, request.simulations)


def calculate(request: CalculateRequest) -> StandingsSimulationResponse:
    names = request.teams if request.teams is not None else standings.team_names(request.team_count)
    standings.check_team_count(len(names))
    cleaned = [name.strip() for name in names]
    if len({name.casefold() for name in cleaned}) != len(cleaned) or not all(cleaned):
        raise AppError(status_code=422, code="INVALID_TEAMS", message="Team names must be non-empty and all different.")
    matches = standings.round_robin(cleaned)
    standings.apply_results(matches, _results(request.results))
    eliminated = min(CUSTOM_ELIMINATED, len(cleaned) - 1) if request.eliminated is None else request.eliminated
    return _build({name: Team(name=name) for name in cleaned}, matches, eliminated, request.model, request.simulations)
