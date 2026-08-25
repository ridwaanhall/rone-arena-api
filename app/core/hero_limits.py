from __future__ import annotations

from time import monotonic

from app.core.exceptions import AppError
from app.services.academy import fetch_academy_post
from app.services.heroes import fetch_hero_post

_HERO_MAX_CACHE_TTL_SECONDS = 3600
_hero_max_id_cache: dict[str, tuple[float, int]] = {}


def _cache_key(source: str, lang: str) -> str:
    return f"{source}:{lang}"


def _get_cached_max(source: str, lang: str) -> int | None:
    key = _cache_key(source, lang)
    cached = _hero_max_id_cache.get(key)
    if cached is None:
        return None

    cached_at, cached_value = cached
    if monotonic() - cached_at < _HERO_MAX_CACHE_TTL_SECONDS:
        return cached_value
    return None


def _set_cached_max(source: str, lang: str, value: int) -> None:
    _hero_max_id_cache[_cache_key(source, lang)] = (monotonic(), value)


def get_academy_hero_max_id(lang: str) -> int:
    cached_value = _get_cached_max("academy", lang)
    if cached_value is not None:
        return cached_value

    payload = {
        "pageSize": 1,
        "pageIndex": 1,
        "filters": [],
        "sorts": [],
        "fields": ["hero_id"],
        "object": [],
    }
    response = fetch_academy_post("2766683", payload, lang)

    total: int | None = None
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            value = data.get("total")
            if isinstance(value, int):
                total = value
            elif isinstance(value, str) and value.isdigit():
                total = int(value)

    if total is None or total < 1:
        raise AppError(
            status_code=502,
            code="UPSTREAM_REQUEST_FAILED",
            message="Failed to fetch data",
            details="Unable to determine latest hero total from academy guide source.",
        )

    _set_cached_max("academy", lang, total)
    return total


def get_hero_max_id(lang: str) -> int:
    cached_value = _get_cached_max("hero", lang)
    if cached_value is not None:
        return cached_value

    payload = {
        "pageSize": 1,
        "sorts": [{"data": {"field": "hero_id", "order": "desc"}, "type": "sequence"}],
        "pageIndex": 1,
        "fields": ["hero_id"],
        "object": [],
    }
    response = fetch_hero_post("2756564", payload, lang)

    max_hero_id: int | None = None
    if isinstance(response, dict):
        data = response.get("data")
        if isinstance(data, dict):
            records = data.get("records")
            if isinstance(records, list) and records:
                first_record = records[0]
                if isinstance(first_record, dict):
                    record_data = first_record.get("data")
                    if isinstance(record_data, dict):
                        value = record_data.get("hero_id")
                        if isinstance(value, int):
                            max_hero_id = value
                        elif isinstance(value, str) and value.isdigit():
                            max_hero_id = int(value)

    if max_hero_id is None or max_hero_id < 1:
        raise AppError(
            status_code=502,
            code="UPSTREAM_REQUEST_FAILED",
            message="Failed to fetch data",
            details="Unable to determine latest hero total from hero list source.",
        )

    _set_cached_max("hero", lang, max_hero_id)
    return max_hero_id


def validate_academy_hero_id(hero_id: int, lang: str) -> None:
    max_hero_id = get_academy_hero_max_id(lang)
    if hero_id > max_hero_id:
        raise AppError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Validation failed.",
            details=[
                {
                    "type": "less_than_equal",
                    "loc": ["path", "hero_id"],
                    "msg": f"Input should be less than or equal to {max_hero_id}",
                    "input": hero_id,
                    "ctx": {"le": max_hero_id},
                }
            ],
            extra={"code": "VALIDATION_ERROR"},
        )


def validate_hero_id(hero_id: int, lang: str) -> None:
    max_hero_id = get_hero_max_id(lang)
    if hero_id > max_hero_id:
        raise AppError(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Validation failed.",
            details=[
                {
                    "type": "less_than_equal",
                    "loc": ["path", "hero_identifier"],
                    "msg": f"Input should be less than or equal to {max_hero_id}",
                    "input": hero_id,
                    "ctx": {"le": max_hero_id},
                }
            ],
            extra={"code": "VALIDATION_ERROR"},
        )


def clear_hero_max_cache() -> None:
    _hero_max_id_cache.clear()
