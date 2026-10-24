from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import SECRET_KEY
from app.core.exceptions import AppError
from app.core.security import CryptoManager, EsportsSourceProvider
from app.main import app
from app.schemas.esports import ScheduleMatch, Team
from app.services.esports import common, indonesia, philippines
from app.services.esports.common import select_weeks, to_int
from app.utils.ttl_cache import ttl_cache

client = TestClient(app)
FIXTURES = Path(__file__).parent / "fixtures" / "esports"
ROOT = Path(__file__).parent.parent

ID_BASE = "https://id.test"
PH_BASE = "https://ph.test"
PH_SLUG = "rora-onic-20260821"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def upstream(monkeypatch):
    """Serve the saved pages instead of the real sites and record every call."""
    calls: list[SimpleNamespace] = []
    pages = {
        f"{ID_BASE}/en/schedule": "id_schedule_en.html",
        f"{ID_BASE}/id/schedule": "id_schedule.html",
        f"{ID_BASE}/match-detail/1036": "id_match.html",
        f"{PH_BASE}/": "ph_home.html",
        f"{PH_BASE}/schedule": "ph_schedule.html",
        f"{PH_BASE}/data/match/{PH_SLUG}": "ph_match.html",
    }

    def fake_request_page(*, method, url, headers, payload=None):
        calls.append(SimpleNamespace(method=method, url=url, headers=headers, payload=payload))
        if method == "POST":
            return SimpleNamespace(json=lambda: json.loads(fixture("ph_items.json")))
        if url not in pages:
            raise AppError(status_code=404, code="UPSTREAM_REQUEST_FAILED", message="Failed to fetch data")
        return SimpleNamespace(
            text=fixture(pages[url]),
            cookies=SimpleNamespace(items=lambda: [("XSRF-TOKEN", "abc"), ("session", "def")]),
        )

    monkeypatch.setattr(common, "request_page", fake_request_page)
    monkeypatch.setattr(philippines, "request_page", fake_request_page)
    monkeypatch.setattr(EsportsSourceProvider, "get_id_base_url", classmethod(lambda cls: ID_BASE))
    monkeypatch.setattr(EsportsSourceProvider, "get_ph_base_url", classmethod(lambda cls: PH_BASE))
    for cached in (indonesia.get_season, indonesia.get_match, philippines.get_standings, philippines._schedule_page, philippines.get_match):
        cached.cache_clear()
    return calls


# ---- parsing helpers


def test_counts_accept_both_thousands_separators() -> None:
    assert to_int("38.859") == 38859
    assert to_int("34,946") == 34946
    assert to_int("-2") == -2


def test_ttl_cache_reuses_results_until_cleared() -> None:
    calls = []

    @ttl_cache(60)
    def double(value: int) -> int:
        calls.append(value)
        return value * 2

    assert (double(2), double(2), double(3)) == (4, 4, 6)
    assert calls == [2, 3]
    double.cache_clear()
    double(2)
    assert calls == [2, 3, 2]


def test_select_weeks_reports_available_weeks_for_unknown_week() -> None:
    weeks = indonesia.get_season("en")[0]

    assert [w.week for w in select_weeks(weeks, None).weeks] == [1, 8]
    assert [w.week for w in select_weeks(weeks, 8).weeks] == [8]
    with pytest.raises(AppError) as caught:
        select_weeks(weeks, 3)
    assert caught.value.status_code == 404
    assert caught.value.code == "WEEK_NOT_FOUND"
    assert "1, 8" in caught.value.message


# ---- Indonesia


def test_id_schedule_reads_weeks_days_and_matches() -> None:
    body = client.get("/api/esports/id/schedule").json()

    assert [w["week"] for w in body["weeks"]] == [1, 8]
    played = body["weeks"][0]["days"][0]["matches"][0]
    assert played["match_id"] == "1036"
    assert played["start_at"] == "2026-08-14T08:00:00+00:00"
    assert played["local_time"] == "15:00"
    assert (played["team1"]["name"], played["team2"]["name"]) == ("EVOS", "RRQ")
    assert (played["score1"], played["score2"]) == (2, 0)
    assert played["replay_url"].startswith("https://www.youtube.com/")

    upcoming = body["weeks"][1]["days"][0]["matches"][0]
    assert upcoming["match_id"] is None
    assert upcoming["score1"] is None and upcoming["score2"] is None


def _dump(season) -> list:
    return [[item.model_dump() for item in season.weeks], [item.model_dump() for item in season.standings], season.playoffs.model_dump()]


def test_id_season_ignores_the_pop_ups_and_junk_after_the_last_week(monkeypatch) -> None:
    # The real page is 2.4 MB, mostly pop-ups, and reading it with a DOM parser used up the Worker's whole CPU
    # budget (Cloudflare error 1102). The weeks are read straight from the text, so unrelated markup must not matter.
    plain = _dump(indonesia.get_season("en"))
    junk = '<div id="modal-1"><div class="match position-relative"><div class="score">9</div></div></div>' * 50
    html = fixture("id_schedule_en.html")
    last = html.rindex('id="standing-regular-season"')
    padded = html[: html.rindex("<div", 0, last)] + junk + html[html.rindex("<div", 0, last) :] + junk
    monkeypatch.setattr(common, "request_page", lambda **kwargs: type("R", (), {"text": padded})())
    indonesia.get_season.cache_clear()

    assert _dump(indonesia.get_season("en")) == plain


def test_id_week_panes_stop_at_the_next_week_and_close_the_last_one() -> None:
    html = '<div id="t-week-1"><p>one</p></div><div id="t-week-2"><div><p>two</p></div></div><p>junk</p>'

    assert indonesia._week_panes(html) == [
        (1, '<div id="t-week-1"><p>one</p></div>'),
        (2, '<div id="t-week-2"><div><p>two</p></div></div>'),
    ]


def test_id_season_reports_a_changed_page_instead_of_failing_obscurely() -> None:
    with pytest.raises(AppError) as unclosed:
        indonesia._week_panes('<div id="t-week-1"><div class="match date">')
    assert unclosed.value.code == "UPSTREAM_PAGE_CHANGED"

    card_without_scores = '<div class="match date x">Friday</div><div class="match position-relative"><p>no teams</p></div>'
    with pytest.raises(AppError) as broken:
        indonesia._schedule_days(card_without_scores)
    assert broken.value.status_code == 502


def test_id_schedule_language_defaults_to_english_and_can_be_indonesian(upstream) -> None:
    def label(**params) -> str:
        return client.get("/api/esports/id/schedule", params=params).json()["weeks"][0]["days"][0]["label"]

    assert label() == "Friday, 14 August 2026"
    assert label(lang="en") == "Friday, 14 August 2026"
    assert label(lang="id") == "Jumat, 14 Agustus 2026"
    assert [call.url for call in upstream] == [f"{ID_BASE}/en/schedule", f"{ID_BASE}/id/schedule"]
    assert client.get("/api/esports/id/schedule", params={"lang": "fr"}).status_code == 422


def test_id_playoffs_read_rounds_seeds_bracket_and_undecided_sides() -> None:
    body = client.get("/api/esports/id/playoffs").json()

    assert body["bracket_image"].startswith("https://wsrv.nl/?url=")
    assert [(seed["seed"], seed["team"]["name"], seed["match_wl"]) for seed in body["seeds"]] == [
        (1, "TLID", {"win": 12, "lose": 4}),
        (2, "NAVI", {"win": 12, "lose": 4}),
        (3, "AE", {"win": 10, "lose": 6}),
    ]
    assert body["seeds"][0]["team"]["logo"].startswith("https://wsrv.nl/")
    first, final = body["days"]
    # The day heading carries a <br /> and a comment after the date.
    assert first["label"] == "Wednesday, 4 November 2026"
    played, upcoming = first["matches"]
    assert played["round"] == "Round 1 Match 1"
    assert (played["match_id"], played["start_at"]) == ("1108", "2026-11-04T06:00:00+00:00")
    assert (played["score1"], played["score2"], played["best_of"]) == (3, 2, 5)
    assert (played["status"], played["winner"]) == ("finished", "team1")
    assert (upcoming["status"], upcoming["winner"], upcoming["best_of"]) == ("scheduled", None, 5)

    grand_final = final["matches"][0]
    assert (grand_final["round"], grand_final["best_of"]) == ("Grand Finals", 7)
    # Undecided sides carry the league's own logo, which must not leak.
    assert grand_final["team1"] == {"name": "TBD", "full_name": None, "logo": None}


def test_id_playoffs_follow_the_language_and_share_the_schedule_fetch(upstream) -> None:
    assert client.get("/api/esports/id/playoffs", params={"lang": "id"}).json()["days"][0]["label"] == "Rabu, 4 November 2026"
    client.get("/api/esports/id/schedule", params={"lang": "id"})
    assert len(upstream) == 1


def test_id_regular_season_matches_are_best_of_three_without_round() -> None:
    played = client.get("/api/esports/id/schedule").json()["weeks"][0]["days"][0]["matches"][0]

    assert (played["round"], played["best_of"], played["status"], played["winner"]) == (None, 3, "finished", "team1")


def test_id_page_without_playoffs_returns_an_empty_bracket(monkeypatch) -> None:
    html = fixture("id_schedule_en.html")
    html = html[html.index('<div class="outer-tabs-schedule">') : html.index('<div class="tab-content clearfix" id="standing-playoffs">')]
    monkeypatch.setattr(common, "request_page", lambda **kwargs: SimpleNamespace(text=html))

    assert client.get("/api/esports/id/playoffs").json() == {"bracket_image": None, "seeds": [], "days": []}


def test_id_standings_follow_the_language() -> None:
    for lang in ("en", "id"):
        first = client.get("/api/esports/id/standings", params={"lang": lang}).json()["standings"][0]
        assert (first["team"]["name"], first["match_point"]) == ("NAVI", 11)


def test_id_schedule_week_filter() -> None:
    assert [w["week"] for w in client.get("/api/esports/id/schedule", params={"week": 8}).json()["weeks"]] == [8]
    missing = client.get("/api/esports/id/schedule", params={"week": 9})
    assert missing.status_code == 404
    assert client.get("/api/esports/id/schedule", params={"week": 0}).status_code == 422


def test_id_standings() -> None:
    first = client.get("/api/esports/id/standings").json()["standings"][0]

    assert first["rank"] == 1
    assert first["team"]["name"] == "NAVI"
    assert first["match_point"] == 11
    assert first["match_wl"] == {"win": 11, "lose": 3}
    assert first["net_game_win"] == 14
    assert first["game_wl"] == {"win": 23, "lose": 9}


def test_id_match_details_read_players_stats_and_mirrored_side() -> None:
    game = client.get("/api/esports/id/matches/1036").json()["games"][0]

    assert game["duration"] == "16:51"
    home, away = game["teams"]
    assert (home["team"]["name"], home["winner"], home["kills"]) == ("EVOS", True, 11)
    assert (away["team"]["name"], away["winner"], away["kills"]) == ("RRQ", False, 7)

    player = home["players"][0]
    assert (player["name"], player["hero"]["name"]) == ("Rendyyy", "Dyrroth")
    assert (player["kills"], player["deaths"], player["assists"], player["kda"]) == (3, 2, 3, 3.0)
    assert [item["id"] for item in player["items"]] == ["3204", "3212", "2302", "3210", "3206"]
    assert "X-Amz-Signature" in player["items"][0]["image"]
    assert player["emblem"]["id"] == "20003"
    assert [t["id"] for t in player["talents"]] == ["811", "721", "731"]
    assert (player["damage_dealt"], player["damage_taken"], player["tower_damage"], player["gold"]) == (38859, 126389, 1699, 9316)

    mirrored = away["players"][0]
    assert (mirrored["name"], mirrored["hero"]["name"]) == ("Joshua", "Esmeralda")
    assert mirrored["emblem"]["id"] == "20008"
    assert [t["id"] for t in mirrored["talents"]] == ["131", "811", "321"]
    assert (mirrored["damage_dealt"], mirrored["gold"]) == (43881, 7293)


def test_id_match_without_details_is_404() -> None:
    assert client.get("/api/esports/id/matches/1").status_code == 404
    assert client.get("/api/esports/id/matches/abc").status_code == 422


def test_id_empty_match_fragment_is_match_not_found(monkeypatch) -> None:
    monkeypatch.setattr(indonesia, "fetch_page", lambda base, path: SimpleNamespace(text="<div></div>"))

    response = client.get("/api/esports/id/matches/2")
    assert response.status_code == 404
    assert response.json()["code"] == "MATCH_NOT_FOUND"


# ---- Philippines


def test_ph_standings_read_logo_from_background_style() -> None:
    standings = client.get("/api/esports/ph/standings").json()["standings"]

    assert len(standings) == 2
    assert standings[0]["team"]["name"] == "FLCN"
    assert standings[0]["team"]["logo"].endswith("falcon-400.webp")
    assert standings[0]["match_wl"] == {"win": 12, "lose": 1}
    assert standings[0]["net_game_win"] == 17
    assert standings[0]["game_wl"] == {"win": 25, "lose": 8}


def test_ph_schedule_reads_days_times_and_slugs() -> None:
    weeks = client.get("/api/esports/ph/schedule").json()["weeks"]

    assert [w["week"] for w in weeks] == [1, 8]
    day = weeks[0]["days"][0]
    assert (day["day"], day["label"]) == (1, "Friday, 21 August 2026")
    played = day["matches"][0]
    assert played["match_id"] == PH_SLUG
    assert played["local_time"] == "5:00 PM"
    # 5:00 PM in Manila (UTC+8).
    assert played["start_at"] == "2026-08-21T09:00:00+00:00"
    assert (played["team1"]["name"], played["team2"]["name"]) == ("RORA", "ONIC")
    assert (played["score1"], played["score2"]) == (0, 2)

    upcoming = weeks[1]["days"][0]["matches"][0]
    assert upcoming["match_id"] is None
    assert upcoming["score1"] is None


def test_ph_match_details_join_summary_scoreboard_and_item_sequence(upstream) -> None:
    body = client.get(f"/api/esports/ph/matches/{PH_SLUG}").json()
    game = body["games"][0]

    assert body["match_id"] == PH_SLUG
    assert game["number"] == 1
    assert game["timeline_minutes"] == [0, 2, 4, 6, 8, 10, 12, 14]
    home, away = game["teams"]
    assert (home["team"]["name"], home["team"]["full_name"]) == ("RORA", "Aurora Gaming")
    assert (home["kills"], away["kills"]) == (0, 6)
    assert away["stats"]["total_gold"] == 48645
    assert away["stats"]["tower_destroy"] == 9
    assert "total_kills" not in away["stats"]

    player = home["players"][0]
    assert (player["name"], player["hero"]["name"]) == ("Koyl", "Hirara")
    assert (player["kills"], player["deaths"], player["assists"], player["kda"]) == (0, 2, 0, 0.0)
    assert (player["gold"], player["damage_dealt"], player["damage_taken"], player["tower_damage"]) == (8165, 18069, 54350, 0)
    assert [item["id"] for item in player["items"]] == ["3431", "3009", "2014", "2013", "2001"]
    assert player["emblem"]["id"] == "20005"
    assert [t["id"] for t in player["talents"]] == ["111", "122", "531"]
    first_purchase = player["item_sequence"][0]
    assert first_purchase["id"] == "1411" and first_purchase["tier"] == 1
    assert 0 < first_purchase["timeline_percent"] < 1

    post = upstream[-1]
    assert post.method == "POST" and post.url == f"{PH_BASE}/data/match-data/itemization"
    assert post.payload == {"_token": "TESTTOKEN", "battleId": "3602903927299249588", "matchName": PH_SLUG}
    assert post.headers["Cookie"] == "XSRF-TOKEN=abc; session=def"


def test_ph_playoffs_read_days_bracket_and_seeds(monkeypatch) -> None:
    monkeypatch.setattr(philippines, "PH_ELIMINATED", 1)
    body = client.get("/api/esports/ph/playoffs").json()

    assert body["bracket_image"].startswith("https://wsrv.nl/?url=")
    # Seeds are the top of the regular-season standings; the fixture has two teams.
    assert [(seed["seed"], seed["team"]["name"]) for seed in body["seeds"]] == [(1, "FLCN")]
    # The cards repeated further down the page are not playoff days.
    assert [(day["day"], day["label"]) for day in body["days"]] == [(1, "Wednesday, 21 October 2026"), (5, "Sunday, 25 October 2026")]
    played = body["days"][0]["matches"][0]
    assert played["match_id"] == "onic-tnc-20261021"
    assert played["start_at"] == "2026-10-21T07:00:00+00:00"
    assert (played["score1"], played["score2"], played["best_of"], played["status"], played["winner"]) == (3, 2, 5, "finished", "team1")
    assert played["round"] is None

    grand_final = body["days"][1]["matches"][0]
    assert (grand_final["best_of"], grand_final["status"]) == (7, "scheduled")
    assert grand_final["team2"] == {"name": "TBD", "full_name": None, "logo": None}


def test_ph_playoffs_do_not_change_the_regular_season(upstream) -> None:
    weeks = client.get("/api/esports/ph/schedule").json()["weeks"]
    client.get("/api/esports/ph/playoffs")

    assert [w["week"] for w in weeks] == [1, 8]
    assert weeks[0]["days"][0]["matches"][0]["best_of"] == 3
    assert [call.url for call in upstream] == [f"{PH_BASE}/schedule", f"{PH_BASE}/"]


def test_ph_match_estimates_duration_and_reads_media() -> None:
    game = client.get(f"/api/esports/ph/matches/{PH_SLUG}").json()["games"][0]
    totals = [team["stats"] for team in game["teams"]]
    minutes = sum(side["total_gold"] / side["gold_per_min"] for side in totals) / 2

    assert game["duration"] is None
    assert game["duration_estimate_seconds"] == round(minutes * 60)
    assert game["duration_estimate"] == f"{round(minutes * 60) // 60}:{round(minutes * 60) % 60:02d}"
    assert game["highlights"] == ["https://www.youtube.com/embed/abc123"]
    assert game["screenshots"] == ["https://wsrv.nl/?url=https%3A%2F%2Fik.imagekit.io%2Fnloe8dhf7w%2Fmplph%2Fs18%2Fscreens%2Fgame1.jpg"]


def test_match_status_follows_the_series_length() -> None:
    def outcome(score1, score2, best_of=3):
        match = ScheduleMatch(match_id=None, start_at=None, local_time="", team1=Team(name="A"), team2=Team(name="B"),
                              score1=score1, score2=score2, best_of=best_of)
        return match.status, match.winner

    assert outcome(None, None) == ("scheduled", None)
    assert outcome(1, 2) == ("finished", "team2")
    assert outcome(1, 1) == ("in_progress", None)
    assert outcome(2, 1, best_of=5) == ("in_progress", None)
    assert outcome(3, 3, best_of=7) == ("in_progress", None)
    assert outcome(4, 3, best_of=7) == ("finished", "team1")


def test_ph_match_slug_is_validated() -> None:
    assert client.get("/api/esports/ph/matches/Not_A_Slug").status_code == 422
    assert client.get("/api/esports/ph/matches/unknown-match-20260101").status_code == 404


def test_results_are_cached(upstream) -> None:
    client.get("/api/esports/id/standings")
    client.get("/api/esports/id/schedule")

    assert len(upstream) == 1


# ---- encryption and secrecy


def test_sources_round_trip_through_the_crypto_manager() -> None:
    manager = CryptoManager("test-secret")
    token = manager.encrypt("https://upstream.test")

    assert b"upstream" not in token
    assert manager.decrypt(token) == "https://upstream.test"


@pytest.mark.skipif(not SECRET_KEY, reason="needs the real SECRET_KEY to decrypt the stored tokens")
def test_stored_tokens_decrypt_to_the_league_sites(monkeypatch) -> None:
    monkeypatch.undo()

    assert EsportsSourceProvider.get_id_base_url().startswith("https://id-")
    assert EsportsSourceProvider.get_ph_base_url().startswith("https://ph-")


def _tracked_files() -> list[Path]:
    listing = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    return [ROOT / name for name in listing if name and (ROOT / name).is_file() and (ROOT / name).suffix not in {".png", ".jpg", ".webp", ".ico", ".woff2", ".lock"}]


def test_upstream_hosts_and_secret_never_appear_in_the_repository() -> None:
    hosts = ("id-mpl.com", "ph-mpl.com")
    for path in _tracked_files():
        if path == Path(__file__).resolve():
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert not any(host in content for host in hosts), f"{path} names an upstream host"
        if SECRET_KEY:
            assert SECRET_KEY not in content, f"{path} contains the secret key"


def test_upstream_hosts_and_secret_never_reach_the_website() -> None:
    rendered = [client.get(url).text for url in ("/api/openapi.json", "/web/esports", "/")]
    rendered.append(json.dumps(client.get("/api").json()))
    for text in rendered:
        assert "id-mpl" not in text and "ph-mpl" not in text
        if SECRET_KEY:
            assert SECRET_KEY not in text


def test_upstream_errors_do_not_expose_the_upstream_url(monkeypatch) -> None:
    def failing(**kwargs):
        raise AppError(status_code=502, code="UPSTREAM_REQUEST_FAILED", message="Failed to fetch data", details=kwargs["url"])

    monkeypatch.setattr(common, "request_page", failing)

    body = client.get("/api/esports/id/standings").json()
    assert body["code"] == "UPSTREAM_REQUEST_FAILED"
    assert ID_BASE not in json.dumps(body)
