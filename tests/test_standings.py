from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import AppError
from app.main import app
from app.services.esports.standings import Match, apply_results, compute_standings, round_robin, team_names, validate_score
from test_esports import upstream  # noqa: F401  (serves the saved league pages)

client = TestClient(app)


def _match(week: int, a: str, b: str, s1: int | None, s2: int | None) -> Match:
    return Match(week=week, team1=a, team2=b, score1=s1, score2=s2, state="played" if s1 is not None else "scheduled")


# ---- the formula reproduces both official tables

SNAPSHOTS = json.loads((Path(__file__).parent / "fixtures" / "esports" / "season_snapshots.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("league", ["id", "ph"])
def test_formula_reproduces_the_official_table_of_a_real_season(league: str) -> None:
    snapshot = SNAPSHOTS[league]
    matches = [_match(week, a, b, s1, s2) for week, a, b, s1, s2 in snapshot["matches"]]
    teams = sorted({m.team1 for m in matches} | {m.team2 for m in matches})

    rows = compute_standings(teams, matches, 3)

    computed = [(r.rank, r.team, r.won, r.net, r.won, r.lost, [r.games_won, r.games_lost]) for r in rows]
    assert computed == [tuple(row) for row in snapshot["official"]]


def test_the_real_seasons_contain_the_cases_that_pin_the_tie_break_order() -> None:
    rows = {row.team: row for row in compute_standings(["NAVI", "TLID", "AE", "EVOS", "BTR", "ONIC", "DEWA", "RRQ", "GEEK"], [_match(*m) for m in SNAPSHOTS["id"]["matches"]], 3)}

    # ONIC and DEWA: level on points; DEWA won their match, yet ONIC's game difference ranks first.
    assert rows["ONIC"].won == rows["DEWA"].won and rows["ONIC"].rank < rows["DEWA"].rank
    assert rows["ONIC"].tiebreak == "net_game_win"
    # RRQ and GEEK: identical records, so head-to-head decides.
    assert (rows["RRQ"].won, rows["RRQ"].net) == (rows["GEEK"].won, rows["GEEK"].net)
    assert (rows["RRQ"].rank, rows["GEEK"].rank) == (8, 9)
    assert rows["RRQ"].tiebreak == "head_to_head"


def test_simulate_endpoint_ranks_the_live_schedule() -> None:
    for league, eliminated in (("id", 3), ("ph", 2)):
        data = client.post(f"/api/esports/{league}/standings/simulate", json={}).json()
        teams = data["teams"]

        assert teams == len(data["standings"]) > eliminated
        assert (data["eliminated"], data["playoff_spots"]) == (eliminated, teams - eliminated)
        assert data["edited_matches"] == 0
        assert [row["rank"] for row in data["standings"]] == list(range(1, teams + 1))
        assert sum(row["in_playoffs_zone"] for row in data["standings"]) == teams - eliminated


def test_eliminated_can_be_chosen_per_request() -> None:
    data = client.post("/api/esports/ph/standings/simulate", json={"eliminated": 1}).json()

    assert data["playoff_spots"] == data["teams"] - 1
    assert sum(row["in_playoffs_zone"] for row in data["standings"]) == data["teams"] - 1


def test_real_seasons_have_as_many_weeks_as_teams() -> None:
    for league in ("id", "ph"):
        matches = SNAPSHOTS[league]["matches"]
        teams = {name for _, a, b, *_ in matches for name in (a, b)}
        assert {week for week, *_ in matches} == set(range(1, len(teams) + 1))
        assert len(matches) == len(teams) * (len(teams) - 1)


def test_editing_a_result_changes_the_table_and_marks_the_match() -> None:
    before = client.post("/api/esports/ph/standings/simulate", json={}).json()
    schedule = client.get("/api/esports/ph/schedule").json()["weeks"]
    played = next(m for week in schedule for day in week["days"] for m in day["matches"] if m["score1"] is not None)
    week = next(w["week"] for w in schedule for d in w["days"] if played in d["matches"])
    flipped = {"week": week, "team1": played["team2"]["name"], "team2": played["team1"]["name"], "score1": played["score1"], "score2": played["score2"]}

    after = client.post("/api/esports/ph/standings/simulate", json={"results": [flipped]}).json()

    # Team order is swapped in the request, so this gives the match to the other side.
    assert after["edited_matches"] == 1
    assert after["standings"] != before["standings"]
    edited = [m for w in after["weeks"] for m in w["matches"] if m["state"] == "edited"]
    assert len(edited) == 1
    assert (edited[0]["score1"], edited[0]["score2"]) == (played["score2"], played["score1"])


def test_clearing_a_played_match_makes_it_remaining() -> None:
    before = client.post("/api/esports/ph/standings/simulate", json={}).json()
    schedule = client.get("/api/esports/ph/schedule").json()["weeks"]
    week = schedule[0]
    match = week["days"][0]["matches"][0]
    cleared = {"week": week["week"], "team1": match["team1"]["name"], "team2": match["team2"]["name"]}

    after = client.post("/api/esports/ph/standings/simulate", json={"results": [cleared]}).json()

    assert after["matches_played"] == before["matches_played"] - 1
    assert after["matches_remaining"] == before["matches_remaining"] + 1


# ---- tie-breaks


def test_net_game_wins_come_before_head_to_head() -> None:
    # B beat A head to head, but A has the better game difference (ONIC / DEWA in the real table).
    matches = [
        _match(1, "A", "B", 1, 2),
        _match(2, "A", "C", 2, 0),
        _match(3, "A", "D", 2, 0),
        _match(4, "B", "C", 0, 2),
        _match(5, "B", "D", 2, 1),
        _match(6, "C", "D", 2, 0),
    ]
    by_name = {row.team: row for row in compute_standings(["A", "B", "C", "D"], matches, 1)}

    assert by_name["A"].won == by_name["B"].won == 2
    assert by_name["A"].rank < by_name["B"].rank
    assert by_name["A"].tiebreak == "net_game_win"


def test_head_to_head_separates_teams_equal_on_points_and_games() -> None:
    # A and B finish level on points and games; A won their match (RRQ / GEEK in the real table).
    matches = [_match(1, "A", "B", 2, 0), _match(2, "A", "C", 0, 2), _match(3, "B", "D", 2, 0)]
    by_name = {row.team: row for row in compute_standings(["A", "B", "C", "D"], matches, 1)}

    assert (by_name["A"].won, by_name["A"].net) == (by_name["B"].won, by_name["B"].net) == (1, 0)
    assert by_name["A"].rank < by_name["B"].rank
    assert by_name["A"].tiebreak == by_name["B"].tiebreak == "head_to_head"


def test_three_way_tie_uses_the_mini_table() -> None:
    # A beats B, B beats C, C beats A, all 2-0; D loses to everyone. The mini table is level.
    cycle = [_match(1, "A", "B", 2, 0), _match(2, "B", "C", 2, 0), _match(3, "C", "A", 2, 0)]
    losses = [_match(4, "A", "D", 2, 0), _match(5, "B", "D", 2, 0), _match(6, "C", "D", 2, 0)]
    order = compute_standings(["A", "B", "C", "D"], cycle + losses, 1)

    assert order[-1].team == "D"
    assert {row.tiebreak for row in order[:3]} == {"unresolved"}


def test_untied_teams_have_no_tiebreak() -> None:
    order = compute_standings(["A", "B", "C"], [_match(1, "A", "B", 2, 0), _match(2, "A", "C", 2, 0), _match(3, "B", "C", 2, 0)], 1)

    assert [row.team for row in order] == ["A", "B", "C"]
    assert [row.tiebreak for row in order] == [None, None, None]


# ---- schedule generator


@pytest.mark.parametrize("count", [2, 3, 4, 5, 8, 9, 20])
def test_round_robin_is_a_double_round_robin_with_weeks_equal_to_teams(count: int) -> None:
    teams = team_names(count)
    matches = round_robin(teams)

    meetings = Counter(frozenset((m.team1, m.team2)) for m in matches)
    assert len(meetings) == count * (count - 1) // 2
    assert set(meetings.values()) == {2}
    assert all(m.team1 != m.team2 for m in matches)
    assert Counter(m.week for m in matches) == Counter({week: count - 1 for week in range(1, count + 1)})
    # Each team plays every other team once at home and once away.
    assert Counter((m.team1, m.team2) for m in matches).most_common(1)[0][1] == 1


def test_team_count_limits() -> None:
    for count in (1, 21):
        with pytest.raises(AppError) as error:
            round_robin(team_names(count))
        assert error.value.code == "INVALID_TEAM_COUNT"


# ---- validation


@pytest.mark.parametrize("scores", [(2, 0), (2, 1), (1, 2), (0, 2), (None, None)])
def test_valid_scores(scores: tuple[int | None, int | None]) -> None:
    validate_score(*scores)


@pytest.mark.parametrize("scores", [(1, 1), (0, 0), (2, 2), (3, 0), (2, None), (None, 1)])
def test_invalid_scores(scores: tuple[int | None, int | None]) -> None:
    with pytest.raises(AppError) as error:
        validate_score(*scores)
    assert error.value.status_code == 422


def test_a_one_one_result_explains_the_deciding_game() -> None:
    with pytest.raises(AppError) as error:
        validate_score(1, 1)
    assert "deciding game" in error.value.message


def test_results_must_point_at_real_matches() -> None:
    matches = round_robin(team_names(4))
    for results, code in (
        ([(1, "Team A", "Nobody", 2, 0)], "UNKNOWN_TEAM"),
        ([(9, "Team A", "Team B", 2, 0)], "MATCH_NOT_FOUND"),
    ):
        with pytest.raises(AppError) as error:
            apply_results(matches, results)
        assert error.value.code == code


def test_each_scheduled_match_takes_one_result() -> None:
    matches = round_robin(team_names(3))
    first = matches[0]
    same = (first.week, first.team1, first.team2, 2, 0)
    apply_results(matches, [same])
    with pytest.raises(AppError) as error:
        apply_results(matches, [same, same])
    assert error.value.code == "MATCH_NOT_FOUND"


def test_the_eliminated_count_is_checked() -> None:
    teams = team_names(4)
    for bad in (-1, 4, 9):
        with pytest.raises(AppError) as error:
            compute_standings(teams, round_robin(teams), bad)
        assert error.value.code == "INVALID_ELIMINATED"


# ---- clinch and elimination status


def _season(results: list[tuple[str, str, int, int]], teams: list[str]) -> list[Match]:
    """A full round robin for ``teams`` where only the listed matches have a result."""
    done = {(a, b): (s1, s2) for a, b, s1, s2 in results}
    matches = []
    for index, (a, b) in enumerate((m.team1, m.team2) for m in round_robin(teams)):
        s1, s2 = done.get((a, b), (None, None))
        matches.append(_match(index // (len(teams) - 1) + 1, a, b, s1, s2))
    return matches


def test_status_is_exact_once_the_season_is_over() -> None:
    teams = ["A", "B", "C", "D"]
    wins = {"A": 6, "B": 4, "C": 2, "D": 0}
    matches = []
    for index, m in enumerate(round_robin(teams)):
        a_wins = wins[m.team1] >= wins[m.team2]
        matches.append(_match(m.week, m.team1, m.team2, 2 if a_wins else 0, 0 if a_wins else 2))
    order = compute_standings(teams, matches, 1)

    assert [(row.team, row.status) for row in order] == [("A", "clinched"), ("B", "clinched"), ("C", "clinched"), ("D", "eliminated")]


def test_status_from_points_bounds_before_the_season_ends() -> None:
    teams = ["A", "B", "C", "D"]
    # A wins everything so far (6 matches), D loses everything; 6 matches are still to play.
    results = [("A", "B", 2, 0), ("A", "C", 2, 0), ("A", "D", 2, 0), ("B", "A", 0, 2), ("C", "A", 0, 2), ("D", "A", 0, 2),
               ("B", "D", 2, 0), ("C", "D", 2, 0), ("D", "B", 0, 2), ("D", "C", 0, 2)]
    matches = _season(results, teams)
    # Two playoff spots: B and C still fight for the second, A is out of reach, D cannot get there.
    by_name = {row.team: row for row in compute_standings(teams, matches, 2)}

    assert by_name["A"].status == "clinched"
    assert by_name["B"].status == "alive"
    assert by_name["D"].status == "eliminated"
    # With three spots, B can only be overtaken by A and C, so it is through already.
    assert {row.team: row.status for row in compute_standings(teams, matches, 1)}["B"] == "clinched"


def test_nobody_is_eliminated_when_the_cut_is_zero() -> None:
    teams = team_names(4)
    rows = compute_standings(teams, round_robin(teams), 0)

    assert {row.status for row in rows} == {"clinched"}


def test_status_at_the_start_of_a_season_is_undecided() -> None:
    teams = team_names(8)
    rows = compute_standings(teams, round_robin(teams), 3)

    assert {row.status for row in rows} == {"alive"}


# ---- the custom calculator


def test_calculate_defaults_to_eight_teams_named_a_to_h() -> None:
    data = client.post("/api/esports/standings/calculate", json={}).json()

    assert data["teams"] == 8
    assert data["eliminated"] == 3
    assert data["playoff_spots"] == 5
    assert [row["team"]["name"] for row in data["standings"]][:3] == sorted(row["team"]["name"] for row in data["standings"])[:3]
    assert data["matches_remaining"] == 56


def test_calculate_with_named_teams_and_results() -> None:
    body = {"teams": ["Alpha", "Bravo", "Charlie"], "eliminated": 1}
    schedule = client.post("/api/esports/standings/calculate", json=body).json()
    first = schedule["weeks"][0]["matches"][0]
    result = {"week": 1, "team1": first["team1"]["name"], "team2": first["team2"]["name"], "score1": 2, "score2": 1}

    data = client.post("/api/esports/standings/calculate", json={**body, "results": [result]}).json()
    top = data["standings"][0]

    assert top["team"]["name"] == first["team1"]["name"]
    assert (top["match_point"], top["net_game_win"]) == (1, 1)
    assert data["edited_matches"] == 1


def test_calculate_default_cut_fits_small_leagues() -> None:
    assert client.post("/api/esports/standings/calculate", json={"team_count": 3}).json()["eliminated"] == 2
    assert client.post("/api/esports/standings/calculate", json={"team_count": 2}).json()["eliminated"] == 1


@pytest.mark.parametrize(
    "body",
    [
        {"team_count": 1},
        {"team_count": 21},
        {"teams": ["Same", "same"]},
        {"teams": ["Only"]},
        {"eliminated": 8},
        {"results": [{"week": 1, "team1": "Team A", "team2": "Team B", "score1": 1, "score2": 1}]},
        {"results": [{"week": 1, "team1": "Team A", "team2": "Team B", "score1": 3, "score2": 0}]},
    ],
)
def test_calculate_rejects_invalid_input(body: dict) -> None:
    response = client.post("/api/esports/standings/calculate", json=body)

    assert response.status_code == 422
    assert response.json()["status"] == "error"


def test_simulate_rejects_an_unknown_league_and_bad_eliminated() -> None:
    assert client.post("/api/esports/xx/standings/simulate", json={}).status_code == 422
    assert client.post("/api/esports/id/standings/simulate", json={"eliminated": 9}).status_code == 422


def test_standings_tools_are_documented_in_the_playground() -> None:
    from app.web.openapi_catalog import get_group_operations

    operations = {op["api_path"]: op for op in get_group_operations(app, "esports")}

    assert operations["/api/esports/{league}/standings/simulate"]["request_body"]
    assert operations["/api/esports/standings/calculate"]["request_body"]


# ---- the web page


def test_standings_page_renders_with_its_script_and_nav_link() -> None:
    response = client.get("/tools/standings")

    assert response.status_code == 200
    assert "<h1>Standings simulator</h1>" in response.text
    assert "/static/js/standings.js?v=" in response.text
    assert 'data-api-base="' in response.text
    assert 'href="/tools/standings"' in response.text
    assert "—" not in response.text.split("<main")[1]


def test_standings_page_is_in_the_sitemap_and_llms_txt() -> None:
    assert "/tools/standings</loc>" in client.get("/sitemap.xml").text
    assert "(https://arena.rone.dev/tools/standings.md)" in client.get("/llms.txt").text
    assert "## Rules" in client.get("/llms-full.txt").text


def test_standings_markdown_documents_the_rules_and_both_endpoints() -> None:
    text = client.get("/tools/standings.md").text

    assert text.startswith("# Standings simulator")
    assert "net game wins" in text and "head-to-head" in text
    assert "/web/esports/{league}/standings/simulate.md" in text
    assert "/web/esports/standings/calculate.md" in text
    assert client.get("/web/esports/standings/calculate.md").status_code == 200
    assert "\"eliminated\": 3" in client.get("/web/esports/standings/calculate.md").text
