from __future__ import annotations

from collections.abc import AsyncGenerator
from contextvars import ContextVar
from ipaddress import ip_address

from fastapi import Request

_client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip", default=None)


def _normalize_ip_candidate(raw_value: str) -> str | None:
    value = raw_value.strip()
    if not value or value.lower() == "unknown":
        return None

    # RFC 7239 Forwarded values can include quoted values and optional ports.
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1].strip()

    if value.startswith("[") and "]" in value:
        value = value[1:value.index("]")]
    elif value.count(":") == 1:
        host, maybe_port = value.rsplit(":", 1)
        if maybe_port.isdigit():
            value = host

    try:
        ip_address(value)
    except ValueError:
        return None
    return value


def _parse_forwarded_header(forwarded_value: str) -> str | None:
    for entry in forwarded_value.split(","):
        for part in entry.split(";"):
            key, sep, value = part.partition("=")
            if sep and key.strip().lower() == "for":
                parsed = _normalize_ip_candidate(value)
                if parsed:
                    return parsed
    return None


def _is_public_ip(value: str) -> bool:
    parsed = ip_address(value)
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def _select_best_ip(candidates: list[str], public_only: bool) -> str | None:
    if not candidates:
        return None
    if not public_only:
        return candidates[0]

    for candidate in candidates:
        if _is_public_ip(candidate):
            return candidate
    return None


def extract_client_ip(request: Request, *, public_only: bool = False) -> str | None:
    candidates: list[str] = []

    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        for item in x_forwarded_for.split(","):
            parsed = _normalize_ip_candidate(item)
            if parsed:
                candidates.append(parsed)

    selected = _select_best_ip(candidates, public_only)
    if selected:
        return selected

    forwarded = request.headers.get("forwarded")
    if forwarded:
        parsed = _parse_forwarded_header(forwarded)
        if parsed:
            if not public_only or _is_public_ip(parsed):
                return parsed

    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        parsed = _normalize_ip_candidate(x_real_ip)
        if parsed:
            if not public_only or _is_public_ip(parsed):
                return parsed

    if request.client and request.client.host:
        parsed = _normalize_ip_candidate(request.client.host)
        if parsed:
            if not public_only or _is_public_ip(parsed):
                return parsed

    return None


async def bind_client_ip(request: Request) -> AsyncGenerator[None, None]:
    token = _client_ip_ctx.set(extract_client_ip(request, public_only=True))
    try:
        yield
    finally:
        _client_ip_ctx.reset(token)


def get_bound_client_ip() -> str | None:
    return _client_ip_ctx.get()
