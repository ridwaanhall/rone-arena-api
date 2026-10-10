"""Chance of each team reaching the playoffs, by simulating the matches still to play.

A match that is still to be played gets a winner and a score from a small model, the table is
ranked with the same rules as `standings.py` (points, net game wins, head-to-head), and the share
of simulated seasons in which a team finishes inside the playoff spots is its probability.

The model (documented because it is an estimate, not a fact):
- ``form`` (default): the chance a team wins a match comes from its record so far, with one
  imaginary win and loss added so an unbeaten or winless team is not certain, and combines the two
  teams with the log5 formula. With no matches played every team is even.
- ``even``: every match is a coin flip.
- The winner takes the match 2-0 in 62% of cases, 2-1 otherwise. That is the share in the real
  Indonesian and Philippine seasons (91 of 115 matches).

Results are seeded from the table itself, so the same request always returns the same numbers. With the
default sample the figure is accurate to about one percentage point (95%), so the later decimals are shown
because they are what the simulation produced, not as a promise of that precision.
Teams that are already through or out (the ``status`` column) get exactly 100 and 0.
"""
from __future__ import annotations

import random
import zlib
from typing import Literal

from app.services.esports.standings import Match, Row

SWEEP_SHARE = 0.62
# Match draws one request may spend. Simulations are scaled down for leagues with many matches left.
DRAW_BUDGET = 120_000
MAX_DRAWS = 400_000
DEFAULT_SIMULATIONS = (300, 20_000)  # (floor, ceiling) of the automatic choice
MAX_SIMULATIONS = 20_000
MIN_SIMULATIONS = 100

Model = Literal["form", "even"]


def _win_chance(first: tuple[int, int], second: tuple[int, int]) -> float:
    """Chance that the first team wins, from (won, played) of each (log5 with a +1/+2 prior)."""
    a = (first[0] + 1) / (first[1] + 2)
    b = (second[0] + 1) / (second[1] + 2)
    return a * (1 - b) / (a * (1 - b) + b * (1 - a))


def simulation_count(requested: int | None, remaining: int) -> int:
    """How many seasons to simulate: what was asked for, held to the draw limits."""
    if remaining == 0:
        return 0
    if requested is None:
        floor, ceiling = DEFAULT_SIMULATIONS
        return max(floor, min(ceiling, DRAW_BUDGET // remaining))
    return max(MIN_SIMULATIONS, min(requested, MAX_SIMULATIONS, MAX_DRAWS // remaining))


def playoff_probabilities(
    teams: list[str],
    matches: list[Match],
    rows: list[Row],
    spots: int,
    model: Model = "form",
    simulations: int | None = None,
) -> tuple[dict[str, float], int]:
    """Percent chance (not rounded) of finishing in the top ``spots``, and how many seasons were simulated."""
    status = {row.team: row.status for row in rows}
    exact = {team: 100.0 if state == "clinched" else 0.0 for team, state in status.items() if state != "alive"}
    teams = sorted(teams)  # one fixed order, so the draws do not depend on how the caller listed the teams
    index = {name: position for position, name in enumerate(teams)}
    size = len(teams)

    base_points = [0] * size
    base_net = [0] * size
    played = [0] * size
    # (i, j) -> [wins of i over j, net game wins of i against j] from matches already played.
    head_to_head: dict[tuple[int, int], list[int]] = {}
    remaining: list[tuple[int, int]] = []
    for match in matches:
        first, second = index[match.team1], index[match.team2]
        result = match.result
        if result is None:
            remaining.append((first, second))
            continue
        margin = abs(result[0] - result[1])
        winner, loser = (first, second) if result[0] > result[1] else (second, first)
        base_points[winner] += 1
        base_net[winner] += margin
        base_net[loser] -= margin
        played[first] += 1
        played[second] += 1
        head_to_head.setdefault((winner, loser), [0, 0])
        head_to_head.setdefault((loser, winner), [0, 0])
        head_to_head[(winner, loser)][0] += 1
        head_to_head[(winner, loser)][1] += margin
        head_to_head[(loser, winner)][1] -= margin

    count = simulation_count(simulations, len(remaining))
    if count == 0 or all(team in exact for team in teams):
        return {team: exact[team] for team in teams}, 0

    if model == "even":
        chance = [0.5] * len(remaining)
    else:
        chance = [_win_chance((base_points[a], played[a]), (base_points[b], played[b])) for a, b in remaining]

    # Seeded from the table, not from the order the teams are listed in, so one state gives one answer.
    state = (list(zip(teams, base_points, base_net)), sorted((teams[a], teams[b]) for a, b in remaining), spots, model, count)
    seed = zlib.crc32(repr(state).encode())
    rng = random.Random(seed)
    inside = [0] * size

    for _ in range(count):
        points = base_points[:]
        net = base_net[:]
        draws: list[tuple[int, int, int]] = []  # (winner, loser, margin)
        for (a, b), p in zip(remaining, chance):
            winner, loser = (a, b) if rng.random() < p else (b, a)
            margin = 2 if rng.random() < SWEEP_SHARE else 1
            points[winner] += 1
            net[winner] += margin
            net[loser] -= margin
            draws.append((winner, loser, margin))

        order = sorted(range(size), key=lambda i: (-points[i], -net[i]))
        start = 0
        while start < size:
            end = start + 1
            while end < size and (points[order[end]], net[order[end]]) == (points[order[start]], net[order[start]]):
                end += 1
            group = order[start:end]
            if end <= spots:
                for i in group:
                    inside[i] += 1
            elif start < spots and len(group) > 1:
                # The playoff line runs through this group: head-to-head, then a coin flip (tiebreaker match).
                members = set(group)
                table = {i: [0, 0] for i in group}
                for i in group:
                    for j in group:
                        if i != j and (i, j) in head_to_head:
                            table[i][0] += head_to_head[(i, j)][0]
                            table[i][1] += head_to_head[(i, j)][1]
                for winner, loser, margin in draws:
                    if winner in members and loser in members:
                        table[winner][0] += 1
                        table[winner][1] += margin
                        table[loser][1] -= margin
                ranked = sorted(group, key=lambda i: (-table[i][0], -table[i][1], rng.random()))
                for i in ranked[: spots - start]:
                    inside[i] += 1
            start = end

    result = {team: 100 * inside[index[team]] / count for team in teams}
    result.update(exact)
    return result, count
