from __future__ import annotations

from typing import Any

from app.core.http import request_form, request_json
from app.core.security import BaseUserPathProvider


def fetch_user_post(path: str, headers: dict, payload: dict[str, Any]) -> Any:
    base_path = BaseUserPathProvider.get_base_url_path_auth()
    url = f"{base_path}/{path}"
    return request_form(method="POST", url=url, headers=headers, payload=payload)

def fetch_user_actgateway(path: str, headers: dict, params: dict[str, Any]) -> Any:
    base_path = BaseUserPathProvider.get_base_url_path_stats()
    url = f"{base_path}/{path}"
    return request_json(method="GET", url=url, headers=headers, params=params)


def fetch_user_actgateway_post(path: str, headers: dict, params: dict[str, Any]) -> Any:
    base_path = BaseUserPathProvider.get_base_url_path_stats()
    url = f"{base_path}/{path}"
    return request_json(method="POST", url=url, headers=headers, params=params)
