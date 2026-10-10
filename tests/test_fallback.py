from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path

import pytest

from app.core.fallback import FALLBACK_STATUSES, backup_url, redirect_headers

BACKUP = "https://arena.fastapicloud.dev"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://arena.rone.dev/api/heroes/rank?days=7&size=1", f"{BACKUP}/api/heroes/rank?days=7&size=1"),
        ("https://arena.rone.dev/web/esports/{league}/standings/simulate", f"{BACKUP}/web/esports/{{league}}/standings/simulate"),
        ("https://arena.rone.dev/", f"{BACKUP}/"),
        ("https://arena.rone.dev/robots.txt#x", f"{BACKUP}/robots.txt"),
    ],
)
def test_backup_url_keeps_path_and_query(url: str, expected: str) -> None:
    assert backup_url(url, BACKUP) == expected


def test_no_backup_url_on_the_backup_host_or_without_one() -> None:
    assert backup_url(f"{BACKUP}/api/heroes", BACKUP) is None
    assert backup_url("https://ARENA.fastapicloud.dev/api", BACKUP) is None
    assert backup_url("https://arena.rone.dev/api", "") is None


def test_redirect_headers_are_not_cacheable() -> None:
    headers = redirect_headers(f"{BACKUP}/api", "exception")

    assert headers == {"Location": f"{BACKUP}/api", "Cache-Control": "no-store", "X-Rone-Fallback": "exception"}


def test_only_server_errors_another_host_can_avoid_fall_back() -> None:
    assert FALLBACK_STATUSES == {500, 502, 504}
    assert 503 not in FALLBACK_STATUSES  # maintenance, high traffic, missing access keys


# ---- the Worker entry point, with a stand-in for the Cloudflare `workers` module


class _Headers(dict):
    def set(self, key: str, value: str) -> None:
        self[key] = value


class _Response:
    def __init__(self, body: str = "", status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.body, self.status, self.headers = body, status, _Headers(headers or {})

    def clone(self) -> "_Response":
        return _Response(self.body, self.status, dict(self.headers))

    @staticmethod
    def new(body: str, init: "_Response") -> "_Response":
        return _Response(body, init.status, dict(init.headers))


class _EdgeCache:
    def __init__(self) -> None:
        self.stored: dict[str, _Response] = {}

    async def match(self, url: str) -> _Response | None:
        return self.stored.get(url)

    def put(self, url: str, response: _Response) -> None:
        self.stored[url] = response


@pytest.fixture
def worker(monkeypatch):
    """Import src/worker.py with a fake `workers` module; `outcome` sets what the app does."""
    outcome: dict[str, object] = {}

    async def fetch(app, request, env, ctx):
        outcome["calls"] = int(outcome.get("calls", 0)) + 1  # type: ignore[arg-type]
        if isinstance(outcome.get("raise"), BaseException):
            raise outcome["raise"]  # type: ignore[misc]
        return _Response(status=int(outcome.get("status", 200)))  # type: ignore[arg-type]

    fake = types.ModuleType("workers")
    fake.WorkerEntrypoint = type("WorkerEntrypoint", (), {"env": None, "ctx": None})  # type: ignore[attr-defined]
    fake.asgi = types.SimpleNamespace(fetch=fetch)  # type: ignore[attr-defined]
    fake.Response = _Response  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "workers", fake)
    cache = _EdgeCache()
    fake_js = types.ModuleType("js")
    fake_js.caches = types.SimpleNamespace(default=cache)  # type: ignore[attr-defined]
    fake_js.Response = _Response  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "js", fake_js)
    outcome["cache"] = cache
    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent / "src"))
    monkeypatch.delitem(sys.modules, "worker", raising=False)
    module = importlib.import_module("worker")
    setattr(module, "outcome", outcome)
    return module


def _call(worker, url: str, method: str = "GET"):
    request = types.SimpleNamespace(url=url, cf=None, method=method)
    entry = worker.Default()
    entry.ctx = types.SimpleNamespace(waitUntil=lambda promise: None)
    return asyncio.run(entry.fetch(request))


def test_a_crash_redirects_to_the_backup_host(worker) -> None:
    worker.outcome["raise"] = RuntimeError("ErrnoError")

    response = _call(worker, "https://arena.rone.dev/api/heroes/rank?days=7")

    assert response.status == 307
    assert response.headers["Location"] == f"{BACKUP}/api/heroes/rank?days=7"
    assert response.headers["X-Rone-Fallback"] == "exception"


@pytest.mark.parametrize("status", [500, 502, 504])
def test_a_server_error_redirects_to_the_backup_host(worker, status: int) -> None:
    worker.outcome["status"] = status

    response = _call(worker, "https://arena.rone.dev/api/esports/id/standings")

    assert response.status == 307
    assert response.headers["X-Rone-Fallback"] == f"status-{status}"


@pytest.mark.parametrize("status", [200, 404, 422, 429, 503])
def test_other_answers_pass_through(worker, status: int) -> None:
    worker.outcome["status"] = status

    assert _call(worker, "https://arena.rone.dev/api/esports/id/standings").status == status


def test_a_crash_on_the_backup_host_itself_is_not_redirected(worker) -> None:
    worker.outcome["raise"] = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        _call(worker, f"{BACKUP}/api/heroes")


def test_esports_answers_are_shared_through_the_edge_cache(worker) -> None:
    url = "https://arena.rone.dev/api/esports/id/standings?lang=en"
    first = _call(worker, url)
    second = _call(worker, url)

    assert first.status == second.status == 200
    assert worker.outcome["calls"] == 1  # the second answer came from the cache, not the app
    stored = worker.outcome["cache"].stored[url]
    assert stored.headers["Cache-Control"] == "public, max-age=300"
    assert second.headers["X-Rone-Edge-Cache"] == "HIT"


@pytest.mark.parametrize(
    ("url", "method", "status"),
    [
        ("https://arena.rone.dev/api/heroes/rank", "GET", 200),  # not esports
        ("https://arena.rone.dev/api/esports/id/standings/simulate", "POST", 200),  # not a GET
        ("https://arena.rone.dev/api/esports/id/standings", "GET", 404),  # not a success
    ],
)
def test_other_requests_are_not_edge_cached(worker, url: str, method: str, status: int) -> None:
    worker.outcome["status"] = status
    _call(worker, url, method)
    _call(worker, url, method)

    assert worker.outcome["calls"] == 2
    assert worker.outcome["cache"].stored == {}


def test_edge_cacheable() -> None:
    from app.core.fallback import edge_cacheable

    assert edge_cacheable("GET", "https://arena.rone.dev/api/esports/ph/schedule?week=2")
    assert edge_cacheable("get", "https://arena.rone.dev/api/esports/id/matches/1036")
    assert not edge_cacheable("POST", "https://arena.rone.dev/api/esports/standings/calculate")
    assert not edge_cacheable("GET", "https://arena.rone.dev/api/heroes/rank")
