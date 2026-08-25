"""
Reusable filter utilities for Rone Arena API input validation and mapping.
Provides DRY, auto-documented, and typo-tolerant mapping for roles, lanes, ranks, etc.
"""
from fastapi import HTTPException

ROLE_MAP: dict[str, list[int]] = {
    "tank": [1],
    "fighter": [2],
    "assassin": [3],
    "mage": [4],
    "marksman": [5],
    "support": [6],
}

LANE_MAP: dict[str, list[int]] = {
    "exp": [1],
    "mid": [2],
    "roam": [3],
    "jungle": [4],
    "gold": [5],
}

RANK_MAP: dict[str, str] = {
    "all": "101",
    "epic": "5",
    "legend": "6",
    "mythic": "7",
    "honor": "8",
    "glory": "9",
}

def parse_multi(value: str) -> list[str]:
    """
    Parse a comma-separated string into a list of stripped, lowercased, non-empty values.
    """
    return [v.strip().lower() for v in value.split(",") if v.strip()]

def suggest_closest(value: str, allowed: list[str]) -> str:
    """
    Suggest the closest allowed value for a typo input using difflib.
    """
    try:
        import difflib
        suggestion = difflib.get_close_matches(value, allowed, n=1)
        return suggestion[0] if suggestion else ""
    except Exception:
        return ""

def validate_and_map_multi(
    selected_raw: list[str],
    mapping: dict[str, list[int]],
    default: list[int],
    field_name: str,
) -> list[int]:
    """
    Validate and map a list of strings to a list of mapped values.
    Raises HTTPException on invalid input, with typo suggestions.
    """
    selected = [v.strip().lower() for v in selected_raw if v.strip()]
    if not selected:
        return default

    allowed = list(mapping.keys())
    invalid = [item for item in selected if item not in mapping]
    if invalid:
        suggestions = [f"{item} (did you mean: {suggest_closest(item, allowed)})" for item in invalid]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field_name}: {', '.join(suggestions)}. Allowed: {', '.join(allowed)}",
        )

    if "all" in selected:
        return default

    result = set()
    for item in selected:
        result.update(mapping[item])
    return list(result)

def validate_and_single(
    selected_raw: list[str],
    mapping: dict[str, list[int]],
    field_name: str,
) -> int:
    """
    Validate and map a list of strings to a single mapped value.
    Returns one integer instead of a list.
    Raises HTTPException on invalid input, with typo suggestions.
    """
    selected = [v.strip().lower() for v in selected_raw if v.strip()]
    if not selected:
        raise HTTPException(
            status_code=422,
            detail=f"No {field_name} provided. Allowed: {', '.join(mapping.keys())}",
        )

    allowed = list(mapping.keys())
    invalid = [item for item in selected if item not in mapping]
    if invalid:
        suggestions = [f"{item} (did you mean: {suggest_closest(item, allowed)})" for item in invalid]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field_name}: {', '.join(suggestions)}. Allowed: {', '.join(allowed)}",
        )

    # Return the first mapped integer only
    return mapping[selected[0]][0]

def validate_and_map_rank(rank_raw: str) -> str:
    """
    Validate and map a rank string to its code. Raises HTTPException on invalid input.
    """
    rank = rank_raw.strip().lower()
    if rank not in RANK_MAP:
        suggestion = suggest_closest(rank, list(RANK_MAP.keys()))
        raise HTTPException(
            status_code=422,
            detail=f"Invalid rank: {rank} (did you mean: {suggestion}). Allowed: {', '.join(RANK_MAP.keys())}",
        )
    return RANK_MAP[rank]