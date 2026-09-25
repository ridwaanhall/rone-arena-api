"""Building blocks for upstream content-source queries.

Every hero and academy endpoint is a POST of a JSON query to
``{access key}{base path}/{source id}``. The query always has the same shape
(page, filters, sorts, plus optional selectors), so routers only describe what
differs and these helpers assemble the body.
"""
from __future__ import annotations

from typing import Any

from app.core.config import RONE_DEV_ACCESS_KEY
from app.core.http import UpstreamHeaderBuilder, request_json
from app.utils.client_ip import get_bound_client_ip


def where(field: str, operator: str, value: Any) -> dict[str, Any]:
    return {"field": field, "operator": operator, "value": value}


def eq(field: str, value: Any) -> dict[str, Any]:
    return where(field, "eq", value)


def has_any_of(field: str, values: list[Any]) -> dict[str, Any]:
    return where(field, "hasAnyOf", values)


def sort_by(field: str, order: str) -> dict[str, Any]:
    return {"data": {"field": field, "order": order}, "type": "sequence"}


def build_query(
    size: int,
    index: int,
    *,
    filters: list[dict[str, Any]] | None = None,
    sorts: list[dict[str, Any]] | None = None,
    **selectors: Any,
) -> dict[str, Any]:
    """Assemble a source query.

    ``filters``/``sorts`` are only sent when given (some sources are queried
    without them); ``selectors`` carries source-specific keys such as
    ``fields``, ``object`` or ``type``.
    """
    query: dict[str, Any] = {"pageSize": size, "pageIndex": index}
    if filters is not None:
        query["filters"] = filters
    if sorts is not None:
        query["sorts"] = sorts
    query.update(selectors)
    return query


def post_source(base_path: str, source_id: str, payload: dict[str, Any], lang: str) -> Any:
    url = f"{RONE_DEV_ACCESS_KEY}{base_path}/{source_id}"
    headers = UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip())
    return request_json(method="POST", url=url, payload=payload, headers=headers)
