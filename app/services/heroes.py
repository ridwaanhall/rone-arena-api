from __future__ import annotations

import re
from dataclasses import dataclass
from time import monotonic
from typing import Any

from app.core.exceptions import AppError, validation_error
from app.core.security import BasePathProvider
from app.services.source import build_query, eq, has_any_of, post_source, sort_by
from app.utils.filters import LANE_IDS, ROLE_IDS, map_many, rank_code

# Upstream source IDs under the hero base path.
HERO_LIST = "2756564"
HERO_SKILL_COMBOS = "2674711"
HERO_WALLPAPERS = "3255326"
# Rank/counter/compatibility statistics, one source per past-day window.
HERO_STATS_BY_DAYS = {"1": "2756567", "3": "2756568", "7": "2756569", "15": "2756565", "30": "2756570"}
# Win/pick/ban rate trends, one source per past-day window.
HERO_TRENDS_BY_DAYS = {"7": "2674709", "15": "2687909", "30": "2690860"}

_HERO_INDEX_TTL_SECONDS = 3600
_hero_index_cache: dict[str, tuple[float, "HeroIndex"]] = {}


def fetch_hero_post(source_id: str, payload: dict[str, Any], lang: str) -> Any:
    return post_source(BasePathProvider.get_base_path(), source_id, payload, lang)


def normalize_hero_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name.lower())


@dataclass(frozen=True)
class HeroIndex:
    max_id: int
    ids_by_name: dict[str, int]


def _as_hero_id(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def get_hero_index(lang: str) -> HeroIndex:
    """Latest hero ID and a name lookup, built from one hero-list fetch.

    Cached per language for an hour: the roster only changes when a hero is
    released, and without the cache every name-based request downloaded the
    whole list.
    """
    cached = _hero_index_cache.get(lang)
    if cached is not None and monotonic() - cached[0] < _HERO_INDEX_TTL_SECONDS:
        return cached[1]

    payload = build_query(
        10000,
        1,
        sorts=[sort_by("hero_id", "desc")],
        fields=["hero_id", "hero.data.head", "hero.data.name", "hero.data.smallmap"],
    )
    response = fetch_hero_post(HERO_LIST, payload, lang)
    data = response.get("data") if isinstance(response, dict) else None
    records = data.get("records") if isinstance(data, dict) else None

    max_id = 0
    ids_by_name: dict[str, int] = {}
    for record in records if isinstance(records, list) else []:
        record_data = record.get("data") if isinstance(record, dict) else None
        if not isinstance(record_data, dict):
            continue
        hero_id = _as_hero_id(record_data.get("hero_id"))
        if hero_id is None:
            continue
        max_id = max(max_id, hero_id)
        name = ((record_data.get("hero") or {}).get("data") or {}).get("name")
        if name:
            ids_by_name.setdefault(normalize_hero_name(name), hero_id)

    if max_id < 1:
        raise AppError(
            status_code=502,
            code="UPSTREAM_REQUEST_FAILED",
            message="Failed to fetch data",
            details="Unable to determine latest hero total from hero list source.",
        )

    index = HeroIndex(max_id=max_id, ids_by_name=ids_by_name)
    _hero_index_cache[lang] = (monotonic(), index)
    return index


def clear_hero_caches() -> None:
    _hero_index_cache.clear()


def require_hero_id(hero_identifier: str, lang: str) -> int:
    """Resolve a hero ID or name to a validated hero ID.

    Numeric IDs must fall within 1..latest hero ID (422 otherwise); names are
    matched case- and punctuation-insensitively (404 when nothing matches).
    """
    try:
        hero_id = int(hero_identifier)
    except ValueError:
        hero_id = get_hero_index(lang).ids_by_name.get(normalize_hero_name(hero_identifier), 0)
        if hero_id <= 0:
            raise AppError(
                status_code=404,
                code="RESOURCE_NOT_FOUND",
                message="Hero not found",
                details=f"No hero found with name: {hero_identifier}",
            )
        return hero_id

    if hero_id < 1:
        raise validation_error("greater_than_equal", "hero_identifier", "Input should be greater than or equal to 1", hero_id, {"ge": 1})

    max_hero_id = get_hero_index(lang).max_id
    if hero_id > max_hero_id:
        raise validation_error(
            "less_than_equal",
            "hero_identifier",
            f"Input should be less than or equal to {max_hero_id}",
            hero_id,
            {"le": max_hero_id},
        )
    return hero_id


def hero_stats_filters(hero_id: int, rank: str, *, match_type: str | int) -> list[dict[str, Any]]:
    """Filters for one hero's rank statistics (hero and academy stats sources)."""
    return [eq("main_heroid", hero_id), eq("bigrank", rank_code(rank)), eq("match_type", match_type)]


def role_lane_filters(role: list[str], lane: list[str]) -> list[dict[str, Any]]:
    """Filters that narrow a hero list by role and lane (both default to all)."""
    return [
        has_any_of("<hero.data.sortid>", map_many(role, ROLE_IDS, "role")),
        has_any_of("<hero.data.roadsort>", map_many(lane, LANE_IDS, "lane")),
    ]
