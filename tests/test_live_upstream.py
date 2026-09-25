"""End-to-end checks against the real upstream game-data service.

These call every public endpoint and assert on the data that comes back, not
just the status code, so they catch upstream schema or source-ID drift.
They need network access and valid upstream keys, so they only run on demand:

    LIVE_UPSTREAM=1 pytest tests/test_live_upstream.py
"""
from __future__ import annotations

import os
import sys
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app  # noqa: E402

pytestmark = pytest.mark.skipif(not os.getenv("LIVE_UPSTREAM"), reason="set LIVE_UPSTREAM=1 to hit the real upstream")

client = TestClient(app)
MIYA = 1


def records(path: str, **params: Any) -> list[dict[str, Any]]:
    """GET an upstream-backed endpoint and return its record payloads."""
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["code"] == 0, body
    found = body["data"]["records"]
    assert found, f"{path} returned no records"
    return [record["data"] for record in found]


def total(path: str, **params: Any) -> int:
    return client.get(path, params=params).json()["data"]["total"]


# ---------------------------------------------------------------- heroes


def test_hero_list_is_sorted_and_named() -> None:
    newest = records("/api/heroes", size=5)
    ids = [hero["hero_id"] for hero in newest]
    assert ids == sorted(ids, reverse=True)
    assert all(hero["hero"]["data"]["name"] for hero in newest)
    assert records("/api/heroes", size=1, order="asc")[0]["hero_id"] == 1
    assert total("/api/heroes") >= 100


def test_hero_rank_sorts_by_requested_field() -> None:
    ranked = records("/api/heroes/rank", sort_field="ban_rate", sort_order="desc", size=10, days="7", rank="mythic")
    rates = [hero["main_hero_ban_rate"] for hero in ranked]
    assert rates == sorted(rates, reverse=True)
    assert all(0 <= hero["main_hero_win_rate"] <= 1 for hero in ranked)


def test_hero_positions_filter_by_role_and_lane() -> None:
    mids = records("/api/heroes/positions", role="mage", lane="mid", size=50)
    for hero in mids:
        # Single-role/lane heroes are padded with "" placeholders upstream.
        roles = {entry["data"]["sort_title"] for entry in hero["hero"]["data"]["sortid"] if entry}
        lanes = {entry["data"]["road_sort_id"] for entry in hero["hero"]["data"]["roadsort"] if entry}
        assert "mage" in roles
        assert "2" in lanes
    assert total("/api/heroes/positions", role="mage", lane="mid") < total("/api/heroes")


def test_hero_detail_by_id_and_by_name_match() -> None:
    by_id = records(f"/api/heroes/{MIYA}")[0]
    by_name = records("/api/heroes/MiYa")[0]
    assert by_id["hero"]["data"]["name"] == "Miya"
    assert by_name["hero"]["data"]["heroid"] == MIYA


@pytest.mark.parametrize(("rank", "code"), [("all", "101"), ("mythic", "7"), ("glory", "9")])
def test_hero_stats_respect_rank(rank: str, code: str) -> None:
    stats = records(f"/api/heroes/{MIYA}/stats", rank=rank)[0]
    assert stats["main_heroid"] == MIYA
    assert stats["bigrank"] == code
    assert stats["match_type"] == "1"


def test_hero_skill_combos() -> None:
    combos = records(f"/api/heroes/{MIYA}/skill-combos")
    assert all(combo["hero_id"] == MIYA and combo["skill_id"] for combo in combos)


@pytest.mark.parametrize(("device", "resolution"), [("desktop", "1920x1080"), ("mobile", "1080x1920")])
def test_hero_wallpapers_match_hero_and_device(device: str, resolution: str) -> None:
    wallpapers = records("/api/heroes/hirara/wallpapers", device=device)
    for wallpaper in wallpapers:
        assert 133 in wallpaper["heroid"]
        assert resolution in {picture["resolution"] for picture in wallpaper["pictures"]}
        assert all(picture["url"].startswith("https://") for picture in wallpaper["pictures"])


@pytest.mark.parametrize("days", ["7", "15", "30"])
def test_hero_trends_cover_requested_window(days: str) -> None:
    trend = records(f"/api/heroes/{MIYA}/trends", **{"past-days": days})[0]
    assert trend["main_heroid"] == MIYA
    assert len(trend["win_rate"]) == int(days)


def test_hero_relations() -> None:
    relation = records(f"/api/heroes/{MIYA}/relations")[0]
    assert relation["hero_id"] == MIYA
    assert set(relation["relation"]) >= {"assist", "strong", "weak"}


@pytest.mark.parametrize(("path", "match_type"), [("counters", "0"), ("compatibility", "1")])
def test_hero_matchups(path: str, match_type: str) -> None:
    matchup = records(f"/api/heroes/{MIYA}/{path}", days="3", rank="legend")[0]
    assert matchup["main_heroid"] == MIYA
    assert matchup["match_type"] == match_type
    assert matchup["bigrank"] == "6"
    assert matchup["sub_hero"]


def test_hero_errors() -> None:
    assert client.get("/api/heroes/99999").status_code == 422
    assert client.get("/api/heroes/definitely-not-a-hero").status_code == 404


def test_localized_hero_list() -> None:
    assert records("/api/heroes", size=1, lang="id")


# ---------------------------------------------------------------- academy


@pytest.mark.parametrize(
    "path",
    [
        "/api/academy/heroes/catalog",
        "/api/academy/roles",
        "/api/academy/equipment",
        "/api/academy/equipment/expanded",
        "/api/academy/spells",
        "/api/academy/emblems",
        "/api/academy/ranks",
    ],
)
def test_academy_reference_lists(path: str) -> None:
    assert records(path, size=3)
    assert total(path) > 0


def test_academy_patch_versions() -> None:
    versions = records("/api/academy/meta/version", size=3)
    assert all(version["game_version"].count(".") == 2 for version in versions)


def test_academy_rank_lookup_contains_rank_id() -> None:
    rank = records("/api/academy/ranks/5")[0]
    assert rank["rankid_start"] <= 5 <= rank["rankid_end"]


def test_academy_recommended_list_and_detail() -> None:
    response = client.get("/api/academy/recommended", params={"size": 1})
    post = response.json()["data"]["records"][0]
    detail = client.get(f"/api/academy/recommended/{post['id']}").json()
    assert detail["data"]["records"][0]["id"] == post["id"]


def test_academy_heroes_filter_by_role() -> None:
    assert total("/api/academy/heroes", role="tank") < total("/api/academy/heroes/catalog")


def test_academy_hero_stats_and_trends() -> None:
    assert records(f"/api/academy/heroes/{MIYA}/stats")[0]["main_heroid"] == MIYA
    trend = records(f"/api/academy/heroes/{MIYA}/trends", days="15")[0]
    assert len(trend["win_rate"]) == 15


def test_academy_hero_lane() -> None:
    lane = records(f"/api/academy/heroes/{MIYA}/lane")[0]
    assert lane["hero_id"] == MIYA
    assert lane["hero"]["data"]["roadsort"]


@pytest.mark.parametrize("path", ["win-rate/timeline", "builds"])
def test_academy_lane_scoped_data(path: str) -> None:
    data = records(f"/api/academy/heroes/{MIYA}/{path}", lane="gold", rank="mythic")[0]
    assert data["heroid"] == MIYA
    assert data["real_road"] == 5
    assert data["big_rank"] == "7"


@pytest.mark.parametrize(("path", "camp_type"), [("counters", "0"), ("teammates", "1")])
def test_academy_matchups(path: str, camp_type: str) -> None:
    matchup = records(f"/api/academy/heroes/{MIYA}/{path}")[0]
    assert matchup["main_heroid"] == MIYA
    assert matchup["camp_type"] == camp_type


def test_academy_hero_recommended_posts_are_for_that_hero() -> None:
    response = client.get(f"/api/academy/heroes/{MIYA}/recommended", params={"size": 3})
    posts = response.json()["data"]["records"]
    assert posts
    assert all(post["data"]["data"]["hero"]["hero_id"] == MIYA for post in posts)


# ---------------------------------------------------------------- addon


def test_win_rate_calculator() -> None:
    body = client.get("/api/addon/win-rate-calculator", params={"match-now": 100, "wr-now": 50, "wr-future": 75}).json()
    assert body["required_no_lose_matches"] == 100


def test_ip_lookup() -> None:
    body = client.get("/api/addon/ip").json()
    assert body["code"] == 0
    assert {"city", "country"} <= set(body["data"])
