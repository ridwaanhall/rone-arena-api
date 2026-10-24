from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.cache_headers import PUBLIC_CACHE_CONTROL, PublicCacheHeaders
from app.main import app as real_app

app = FastAPI()
app.add_middleware(PublicCacheHeaders)


@app.get("/api/heroes/rank")
@app.get("/api/academy/equipment")
@app.get("/api/esports/id/schedule")
@app.get("/api/user/me")
@app.get("/api/addon/ip")
def ok() -> dict[str, str]:
    return {"ok": "yes"}


@app.get("/api/heroes/missing")
def missing() -> JSONResponse:
    return JSONResponse({"error": "no"}, status_code=404)


@app.get("/api/heroes/own")
def own() -> JSONResponse:
    return JSONResponse({"ok": "yes"}, headers={"Cache-Control": "no-store"})


@app.post("/api/esports/id/standings/simulate")
def simulate() -> dict[str, str]:
    return {"ok": "yes"}


client = TestClient(app)


def test_public_answers_can_be_cached() -> None:
    for path in ("/api/heroes/rank?days=7", "/api/academy/equipment", "/api/esports/id/schedule"):
        assert client.get(path).headers["cache-control"] == PUBLIC_CACHE_CONTROL


def test_personal_and_per_visitor_answers_are_not_cached() -> None:
    assert "cache-control" not in client.get("/api/user/me").headers
    assert "cache-control" not in client.get("/api/addon/ip").headers
    assert "cache-control" not in client.get("/api/heroes/rank", headers={"Authorization": "Bearer x"}).headers
    assert "cache-control" not in client.get("/api/heroes/rank", headers={"Cookie": "session=x"}).headers


def test_errors_posts_and_answers_with_their_own_policy_are_left_alone() -> None:
    assert "cache-control" not in client.get("/api/heroes/missing").headers
    assert "cache-control" not in client.post("/api/esports/id/standings/simulate").headers
    assert client.get("/api/heroes/own").headers["cache-control"] == "no-store"


def test_the_app_uses_it() -> None:
    assert any(m.cls is PublicCacheHeaders for m in real_app.user_middleware)
