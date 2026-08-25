from __future__ import annotations

from typing import Any

from app.core.config import RONE_DEV_ACCESS_KEY, RONE_DEV_ACCESS_KEY_V2
from app.core.http import UpstreamHeaderBuilder, request_json
from app.core.security import BasePathProvider
from app.utils.client_ip import get_bound_client_ip


def fetch_academy_post(endpoint_id: str, payload: dict[str, Any], lang: str) -> Any:
    base_path = BasePathProvider.get_base_path_academy()
    url = f"{RONE_DEV_ACCESS_KEY}{base_path}/{endpoint_id}"
    headers = UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip())
    return request_json(method="POST", url=url, payload=payload, headers=headers)


def fetch_ratings_all(lang: str) -> Any:
    base_path = BasePathProvider.get_base_path_ratings()
    url = f"{RONE_DEV_ACCESS_KEY_V2}{base_path}?offset=0"
    headers = UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip())
    return request_json(method="GET", url=url, headers=headers)


def fetch_ratings_subject(lang: str, subject: str) -> Any:
    base_path = BasePathProvider.get_base_path_ratings()
    url = f"{RONE_DEV_ACCESS_KEY_V2}{base_path}/{subject}"
    headers = UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip())
    return request_json(method="GET", url=url, headers=headers)
