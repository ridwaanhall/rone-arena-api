"""Where a request that failed on this host is sent instead: the same path on the backup host.

Used by `src/worker.py` (Cloudflare Workers). When the app raises, or answers with a server
error that another host could avoid, the Worker answers 307 to the same path and query on
ALTERNATIVE_ENDPOINT_URL, which runs the same app. A 307 tells clients to repeat the same
method and body there. 503 is left alone: it means maintenance or high traffic (with its own
`alternative_endpoint`) or a deployment without its access keys, which the body explains.
"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

# Server errors worth retrying elsewhere: a crash, a bad upstream answer, an upstream timeout.
FALLBACK_STATUSES = frozenset({500, 502, 504})


def backup_url(url: str, backup: str) -> str | None:
    """``url`` moved to the backup host, or None when there is no backup or it is this host."""
    target = urlsplit(backup)
    source = urlsplit(url)
    if not target.scheme or not target.netloc or source.netloc.lower() == target.netloc.lower():
        return None
    return urlunsplit((target.scheme, target.netloc, source.path, source.query, ""))


def redirect_headers(location: str, reason: str) -> dict[str, str]:
    # no-store: a cached redirect would keep sending visitors away after this host recovers.
    return {"Location": location, "Cache-Control": "no-store", "X-Rone-Fallback": reason}
