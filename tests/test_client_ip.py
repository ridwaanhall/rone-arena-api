from __future__ import annotations

from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app


client = TestClient(app)


def test_addon_ip_prefers_public_from_x_forwarded_for(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_fetch(path: str, client_ip: str | None = None) -> dict[str, object]:
        captured["path"] = path
        captured["client_ip"] = client_ip
        return {"code": 0, "msg": "ok", "data": {"client_ip": client_ip}}

    monkeypatch.setattr("app.api.routers.addon.fetch_ip_get", fake_fetch)

    response = client.get(
        "/api/addon/ip",
        headers={"x-forwarded-for": "10.20.30.40, 36.72.11.22"},
    )

    assert response.status_code == 200
    assert captured["path"] == "c/ip"
    assert captured["client_ip"] == "36.72.11.22"


def test_addon_ip_ignores_private_only_forwarded_ip(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_fetch(path: str, client_ip: str | None = None) -> dict[str, object]:
        captured["path"] = path
        captured["client_ip"] = client_ip
        return {"code": 0, "msg": "ok", "data": {"client_ip": client_ip}}

    monkeypatch.setattr("app.api.routers.addon.fetch_ip_get", fake_fetch)

    response = client.get(
        "/api/addon/ip",
        headers={"x-forwarded-for": "10.20.30.40, 192.168.1.3"},
    )

    assert response.status_code == 200
    assert captured["path"] == "c/ip"
    assert captured["client_ip"] is None


def test_hero_service_header_uses_public_forwarded_ip(monkeypatch) -> None:
    captured_headers: dict[str, str] = {}

    def fake_request_json(*, method: str, url: str, headers: dict[str, str], payload: dict[str, object] | None = None, params: dict[str, object] | None = None) -> dict[str, object]:
        captured_headers.update(headers)
        return {"code": 0, "data": {"records": []}}

    monkeypatch.setattr("app.services.heroes.request_json", fake_request_json)

    response = client.get(
        "/api/heroes?size=1&index=1",
        headers={"x-forwarded-for": "10.0.0.1, 36.80.5.9"},
    )

    assert response.status_code == 200
    assert captured_headers.get("X-Forwarded-For") == "36.80.5.9"


def test_academy_service_header_uses_public_forwarded_ip(monkeypatch) -> None:
    captured_headers: dict[str, str] = {}

    def fake_request_json(*, method: str, url: str, headers: dict[str, str], payload: dict[str, object] | None = None, params: dict[str, object] | None = None) -> dict[str, object]:
        captured_headers.update(headers)
        return {"code": 0, "data": {"records": []}}

    monkeypatch.setattr("app.services.academy.request_json", fake_request_json)

    response = client.get(
        "/api/academy/meta/version?size=1&index=1",
        headers={"x-forwarded-for": "172.16.0.2, 103.90.20.10"},
    )

    assert response.status_code == 200
    assert captured_headers.get("X-Forwarded-For") == "103.90.20.10"
