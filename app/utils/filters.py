"""Map public filter values (role, lane, rank names) to upstream codes.

Unknown values are rejected with a 422 that suggests the closest valid value.
"""
from __future__ import annotations

import difflib
from enum import Enum

from fastapi import HTTPException

ROLE_IDS: dict[str, int] = {"tank": 1, "fighter": 2, "assassin": 3, "mage": 4, "marksman": 5, "support": 6}
LANE_IDS: dict[str, int] = {"exp": 1, "mid": 2, "roam": 3, "jungle": 4, "gold": 5}
RANK_CODES: dict[str, str] = {"all": "101", "epic": "5", "legend": "6", "mythic": "7", "honor": "8", "glory": "9"}


def _normalize(value: str | Enum) -> str:
    raw = value.value if isinstance(value, Enum) else value
    return str(raw).strip().lower()


def _reject_unknown(values: list[str], allowed: list[str], field_name: str) -> None:
    invalid = [value for value in values if value not in allowed]
    if not invalid:
        return
    suggestions = []
    for value in invalid:
        closest = difflib.get_close_matches(value, allowed, n=1)
        suggestions.append(f"{value} (did you mean: {closest[0] if closest else ''})")
    raise HTTPException(
        status_code=422,
        detail=f"Invalid {field_name}: {', '.join(suggestions)}. Allowed: {', '.join(allowed)}",
    )


def map_many(selected_raw: list[str], ids: dict[str, int], field_name: str) -> list[int]:
    """Map several names to IDs; an empty selection means every ID."""
    selected = [_normalize(value) for value in selected_raw if _normalize(value)]
    if not selected:
        return list(ids.values())
    _reject_unknown(selected, list(ids), field_name)
    return list({ids[value] for value in selected})


def map_one(value: str | Enum, ids: dict[str, int], field_name: str) -> int:
    name = _normalize(value)
    _reject_unknown([name], list(ids), field_name)
    return ids[name]


def rank_code(rank: str | Enum) -> str:
    name = _normalize(rank)
    _reject_unknown([name], list(RANK_CODES), "rank")
    return RANK_CODES[name]
