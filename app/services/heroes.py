from __future__ import annotations

import re
from typing import Any

from app.core.config import RONE_DEV_ACCESS_KEY
from app.core.http import UpstreamHeaderBuilder, request_json
from app.core.security import BasePathProvider
from app.utils.client_ip import get_bound_client_ip


def normalize_hero_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", name.lower())


def _hero_list_payload() -> dict[str, Any]:
    return {
        "pageSize": 10000,
        "sorts": [
            {
                "data": {
                    "field": "hero_id",
                    "order": "desc",
                },
                "type": "sequence",
            }
        ],
        "pageIndex": 1,
        "fields": [
            "hero_id",
            "hero.data.head",
            "hero.data.name",
            "hero.data.smallmap",
        ],
    }


def get_hero_id_by_name(hero_name: str, lang: str = "en") -> int:
    base_path = BasePathProvider.get_base_path()
    url = f"{RONE_DEV_ACCESS_KEY}{base_path}/2756564"
    data = request_json(
        method="POST",
        url=url,
        payload=_hero_list_payload(),
        headers=UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip()),
    )
    search_name = normalize_hero_name(hero_name)

    for record in data.get("data", {}).get("records", []):
        hero_data = record.get("data", {}).get("hero", {}).get("data", {})
        normalized_actual_name = normalize_hero_name(hero_data.get("name", ""))
        if normalized_actual_name == search_name:
            return int(record.get("data", {}).get("hero_id", 0) or 0)
    return 0


def resolve_hero_id(hero_identifier: str, lang: str) -> int:
    try:
        return int(hero_identifier)
    except ValueError:
        return get_hero_id_by_name(hero_identifier, lang)


def fetch_hero_post(endpoint_id: str, payload: dict[str, Any], lang: str) -> Any:
    base_path = BasePathProvider.get_base_path()
    url = f"{RONE_DEV_ACCESS_KEY}{base_path}/{endpoint_id}"
    headers = UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip())
    return request_json(method="POST", url=url, payload=payload, headers=headers)
