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


class _Response:
    def __init__(self, body: str = "", status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.body, self.status, self.headers = body, status, headers or {}


@pytest.fixture
def worker(monkeypatch):
    """Import src/worker.py with a fake `workers` module; `outcome` sets what the app does."""
    outcome: dict[str, object] = {}

    async def fetch(app, request, env, ctx):
        if isinstance(outcome.get("raise"), BaseException):
            raise outcome["raise"]  # type: ignore[misc]
        return _Response(status=int(outcome.get("status", 200)))  # type: ignore[arg-type]

    fake = types.ModuleType("workers")
    fake.WorkerEntrypoint = type("WorkerEntrypoint", (), {"env": None, "ctx": None})  # type: ignore[attr-defined]
    fake.asgi = types.SimpleNamespace(fetch=fetch)  # type: ignore[attr-defined]
    fake.Response = _Response  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "workers", fake)
    monkeypatch.syspath_prepend(str(Path(__file__).parent.parent / "src"))
    monkeypatch.delitem(sys.modules, "worker", raising=False)
    module = importlib.import_module("worker")
    setattr(module, "outcome", outcome)
    return module


def _call(worker, url: str):
    request = types.SimpleNamespace(url=url, cf=None)
    return asyncio.run(worker.Default().fetch(request))


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
