"""Standings maths for the regular season of a first-to-two league, shared by every league.

Matches are first to 2 games ("best of 2" in the community's words), so a finished match is
2-0, 2-1, 1-2 or 0-2; a 1-1 still needs a deciding game. A team earns 1 match point per match
won. Recomputing the Indonesian (9 teams) and Philippine (8 teams) tables from their schedules
reproduces both official tables exactly, with this order:

1. match points, highest first
2. net game wins (games won minus games lost), highest first
3. head-to-head among the teams still tied (match wins, then net game wins, in the matches
   they played against each other)
4. still level: ``unresolved``; the league plays a tiebreaker match

Net game wins come before head-to-head (ONIC sits above DEWA although DEWA beat them), and
head-to-head comes before anything else (RRQ above GEEK on identical records).
Only (1) and (2) are proven by two full tables; (3) for three or more tied teams is a mini
table and the Philippine tie-breaks are assumed to equal the Indonesian ones.

The functions here are pure so they stay cheap on a Cloudflare Worker.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.core.exceptions import AppError

GAME_TARGET = 2
MIN_TEAMS = 2
MAX_TEAMS = 20
VALID_SCORES = {(GAME_TARGET, 0), (GAME_TARGET, 1), (1, GAME_TARGET), (0, GAME_TARGET)}


@dataclass
class Match:
    week: int
    team1: str
    team2: str
    score1: int | None = None
    score2: int | None = None
    # played: result came with the schedule · edited: set by the caller · scheduled: no result
    state: str = "scheduled"

    @property
    def done(self) -> bool:
        return self.score1 is not None and self.score2 is not None


@dataclass
class Row:
    team: str
    won: int = 0
    lost: int = 0
    games_won: int = 0
    games_lost: int = 0
    remaining: int = 0
    rank: int = 0
    tiebreak: str | None = None
    status: str = "alive"

    @property
    def played(self) -> int:
        return self.won + self.lost

    @property
    def net(self) -> int:
        return self.games_won - self.games_lost

    @property
    def max_points(self) -> int:
        return self.won + self.remaining


def _invalid(message: str, code: str = "INVALID_MATCH_RESULT") -> AppError:
    return AppError(status_code=422, code=code, message=message)


def validate_score(score1: int | None, score2: int | None) -> None:
    """Accept a first-to-2 result, or both scores empty (not played)."""
    if score1 is None and score2 is None:
        return
    if score1 is None or score2 is None:
        raise _invalid("Give both scores of a match, or neither to mark it as not played.")
    if (score1, score2) not in VALID_SCORES:
        hint = " A 1-1 match needs a deciding game, so one team must reach 2." if (score1, score2) == (1, 1) else ""
        raise _invalid(f"{score1}-{score2} is not a result of a first-to-{GAME_TARGET} match. Use 2-0, 2-1, 1-2 or 0-2.{hint}")


def team_names(count: int) -> list[str]:
    return [f"Team {chr(ord('A') + index)}" for index in range(count)]


def check_team_count(count: int) -> None:
    if not MIN_TEAMS <= count <= MAX_TEAMS:
        raise _invalid(f"A league needs {MIN_TEAMS} to {MAX_TEAMS} teams, got {count}.", "INVALID_TEAM_COUNT")


def round_robin(teams: list[str]) -> list[Match]:
    """Double round robin laid out like the real leagues: as many weeks as teams, each with
    (teams - 1) matches. The first half of the season is a full round robin by the circle
    method, the second half repeats it with the sides swapped."""
    check_team_count(len(teams))
    pool: list[str | None] = [*teams, None] if len(teams) % 2 else [*teams]
    rounds: list[list[tuple[str, str]]] = []
    for _ in range(len(pool) - 1):
        rounds.append([(a, b) for a, b in zip(pool[: len(pool) // 2], reversed(pool[len(pool) // 2 :])) if a and b])
        pool = [pool[0], pool[-1], *pool[1:-1]]
    fixtures = [pair for matches in rounds for pair in matches]
    fixtures += [(b, a) for a, b in fixtures]
    per_week = len(teams) - 1
    return [Match(week=index // per_week + 1, team1=a, team2=b) for index, (a, b) in enumerate(fixtures)]


def apply_results(matches: list[Match], results: list[tuple[int, str, str, int | None, int | None]]) -> None:
    """Set results on the schedule in place. ``results`` are (week, team1, team2, score1, score2);
    either team order is accepted. When a pair meets twice in one week, results fill them in order."""
    names = {name for match in matches for name in (match.team1, match.team2)}
    claimed: set[int] = set()
    for week, team1, team2, score1, score2 in results:
        for name in (team1, team2):
            if name not in names:
                raise _invalid(f"Unknown team {name!r}. Teams: {', '.join(sorted(names))}.", "UNKNOWN_TEAM")
        validate_score(score1, score2)
        candidates = [
            index
            for index, match in enumerate(matches)
            if match.week == week and {match.team1, match.team2} == {team1, team2} and index not in claimed
        ]
        if not candidates:
            weeks = sorted({match.week for match in matches if {match.team1, match.team2} == {team1, team2}})
            when = f" They meet in week {' and '.join(str(item) for item in weeks)}." if weeks else ""
            raise _invalid(f"Week {week} has no (further) match between {team1} and {team2}.{when}", "MATCH_NOT_FOUND")
        index = candidates[0]
        claimed.add(index)
        match = matches[index]
        if (match.team1, match.team2) != (team1, team2):
            score1, score2 = score2, score1
        match.score1, match.score2, match.state = score1, score2, "edited"


def _order(rows: list[Row], matches: list[Match]) -> None:
    """Sort rows in place and set rank and tiebreak."""
    by_points: dict[int, list[Row]] = defaultdict(list)
    for row in rows:
        by_points[row.won].append(row)

    ordered: list[Row] = []
    for points in sorted(by_points, reverse=True):
        level = by_points[points]
        by_net: dict[int, list[Row]] = defaultdict(list)
        for row in level:
            by_net[row.net].append(row)
        for net in sorted(by_net, reverse=True):
            tied = by_net[net]
            if len(tied) == 1:
                tied[0].tiebreak = "net_game_win" if len(level) > 1 else None
                ordered.append(tied[0])
                continue
            members = {row.team for row in tied}
            table: dict[str, list[int]] = {name: [0, 0] for name in members}
            for match in matches:
                if match.done and match.team1 in members and match.team2 in members:
                    winner, loser = (match.team1, match.team2) if match.score1 > match.score2 else (match.team2, match.team1)
                    table[winner][0] += 1
                    table[winner][1] += abs(match.score1 - match.score2)
                    table[loser][1] -= abs(match.score1 - match.score2)
            tied.sort(key=lambda row: (-table[row.team][0], -table[row.team][1], row.team))
            for row in tied:
                twin = any(table[other.team] == table[row.team] for other in tied if other is not row)
                row.tiebreak = "unresolved" if twin else "head_to_head"
            ordered.extend(tied)
    rows[:] = ordered
    for position, row in enumerate(rows, start=1):
        row.rank = position


def compute_standings(teams: list[str], matches: list[Match], eliminated: int) -> list[Row]:
    """Rank the teams after the matches that have a result and mark who is through.

    Status uses plain points bounds, so it is exact once the season is over and otherwise
    conservative: it can say ``alive`` for a team that is in fact decided, never the reverse.
    """
    if not 0 <= eliminated < len(teams):
        raise _invalid(
            f"{eliminated} eliminated teams is not possible with {len(teams)} teams; use 0 to {len(teams) - 1}.",
            "INVALID_ELIMINATED",
        )
    rows = {name: Row(team=name) for name in teams}
    for match in matches:
        first, second = rows[match.team1], rows[match.team2]
        if not match.done:
            first.remaining += 1
            second.remaining += 1
            continue
        first.games_won += match.score1
        first.games_lost += match.score2
        second.games_won += match.score2
        second.games_lost += match.score1
        winner, loser = (first, second) if match.score1 > match.score2 else (second, first)
        winner.won += 1
        loser.lost += 1

    ordered = list(rows.values())
    _order(ordered, matches)

    spots = len(teams) - eliminated
    season_over = all(match.done for match in matches)
    for row in ordered:
        if season_over:
            row.status = "clinched" if row.rank <= spots else "eliminated"
            continue
        others = [other for other in ordered if other is not row]
        can_catch_up = sum(1 for other in others if other.max_points >= row.won)
        already_ahead = sum(1 for other in others if other.won > row.max_points)
        row.status = "clinched" if can_catch_up < spots else "eliminated" if already_ahead >= spots else "alive"
    return ordered

