"""Rewrite image URLs so they are served through the wsrv.nl image proxy."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlsplit

from app.core.config import USE_WSRV

WSRV_HOST = "wsrv.nl"
# .ico is left alone: the proxy cannot serve it.
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp", ".svg")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def wsrv_url(url: str) -> str:
    """Proxy an absolute image URL through wsrv.nl; anything else is returned unchanged.

    Already-proxied URLs and local hosts (which the proxy could not reach) are skipped,
    so the rewrite is idempotent. SVGs are proxied too; the proxy serves them rasterised.
    """
    if not USE_WSRV or not url.startswith(("http://", "https://")):
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return url
    host = (parts.hostname or "").lower()
    if host == WSRV_HOST or host in _LOCAL_HOSTS or host.endswith(".localhost"):
        return url
    if not parts.path.lower().endswith(IMAGE_EXTENSIONS):
        return url
    return f"https://{WSRV_HOST}/?url={quote(url, safe='')}"


def wsrv_json(data: Any) -> Any:
    """Proxy every image URL found in a JSON-like structure."""
    if isinstance(data, str):
        return wsrv_url(data)
    if isinstance(data, list):
        return [wsrv_json(item) for item in data]
    if isinstance(data, dict):
        return {key: wsrv_json(value) for key, value in data.items()}
    return data
