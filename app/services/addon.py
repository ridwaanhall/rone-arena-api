from __future__ import annotations

from typing import Any

from app.core.http import UpstreamHeaderBuilder, request_json
from app.core.security import BaseUserPathProvider


def fetch_ip_get(path: str, client_ip: str | None = None) -> Any:
    base_path = BaseUserPathProvider.get_base_url_path_auth()
    url = f"{base_path}/{path}"
    headers = UpstreamHeaderBuilder.get_ip_check_header(client_ip)
    return request_json(method="GET", url=url, headers=headers, payload=None, params=None)