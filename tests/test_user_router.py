from __future__ import annotations


import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_user_read_endpoints_use_get_and_authorization_header() -> None:
    openapi = client.get("/api/openapi.json").json()

    read_only_paths = [
        "/api/user/info",
        "/api/user/stats",
        "/api/user/season",
        "/api/user/matches",
        "/api/user/matches/{match_id}",
        "/api/user/heroes/frequent",
        "/api/user/friends",
    ]

    for path in read_only_paths:
        assert "get" in openapi["paths"][path]
        assert "post" not in openapi["paths"][path]
        assert {"HTTPBearer": []} in openapi["paths"][path]["get"]["security"]

    privacy_ops = openapi["paths"].get("/api/user/privacy/settings", {})
    assert "get" in privacy_ops
    assert "post" in privacy_ops
    assert {"HTTPBearer": []} in privacy_ops["get"]["security"]

    logout_op = openapi["paths"].get("/api/user/auth/logout", {}).get("post", {})
    assert {"HTTPBearer": []} in logout_op.get("security", [])
    assert "requestBody" not in logout_op
    logout_schema = logout_op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
    assert logout_schema.get("$ref") == "#/components/schemas/UserAuthSimpleResponse"

    login_op = openapi["paths"].get("/api/user/auth/login", {}).get("post", {})
    login_schema = login_op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
    assert login_schema.get("$ref") == "#/components/schemas/UserLoginResponse"

    privacy_post_op = openapi["paths"].get("/api/user/privacy/settings", {}).get("post", {})
    assert {"HTTPBearer": []} in privacy_post_op.get("security", [])
    assert "requestBody" not in privacy_post_op
    parameters = privacy_post_op.get("parameters", [])
    visibility_param = next((p for p in parameters if p.get("name") == "visibility"), None)
    assert visibility_param is not None
    assert visibility_param.get("required") is True
    assert visibility_param.get("schema", {}).get("default") is None
    visibility_schema = visibility_param.get("schema", {})
    enum_values = visibility_schema.get("enum")
    if enum_values is None:
        ref = visibility_schema.get("$ref", "")
        assert ref == "#/components/schemas/VisibilityEnum"
        enum_values = openapi["components"]["schemas"]["VisibilityEnum"].get("enum", [])
    assert sorted(enum_values) == ["invisible", "visible"]


def test_user_info_endpoint_strips_bearer_before_forwarding_upstream(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_fetch_user_post(path: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        captured["path"] = path
        captured["authorization"] = headers["authorization"]
        captured["x-token"] = headers["x-token"]
        return {"code": 0, "data": "", "msg": "ok"}

    monkeypatch.setattr("app.api.routers.user.fetch_user_post", fake_fetch_user_post)

    response = client.get(
        "/api/user/info?lang=en",
        headers={"Authorization": "Bearer test-jwt-token"},
    )

    assert response.status_code == 200
    assert captured["path"] == "base/getBaseInfo"
    assert captured["authorization"] == "test-jwt-token"
    assert captured["x-token"] == "test-jwt-token"


def test_user_logout_uses_authorization_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_fetch_user_post(path: str, headers: dict[str, str], payload: dict[str, object]) -> dict[str, object]:
        captured["path"] = path
        captured["authorization"] = headers["authorization"]
        captured["x-token"] = headers["x-token"]
        return {"code": 0, "data": "", "msg": "ok"}

    monkeypatch.setattr("app.api.routers.user.fetch_user_post", fake_fetch_user_post)

    response = client.post(
        "/api/user/auth/logout",
        headers={"Authorization": "Bearer test-jwt-token"},
    )

    assert response.status_code == 200
    assert captured["path"] == "base/logout"
    assert captured["authorization"] == "test-jwt-token"
    assert captured["x-token"] == "test-jwt-token"


def test_user_stats_invalid_upstream_shape_returns_standardized_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_user_actgateway(path: str, headers: dict[str, str], params: dict[str, object]) -> object:
        return ["invalid-shape"]

    monkeypatch.setattr("app.api.routers.user.fetch_user_actgateway", fake_fetch_user_actgateway)

    response = client.get(
        "/api/user/stats?lang=en",
        headers={"Authorization": "Bearer test-jwt-token"},
    )

    assert response.status_code == 502
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["code"] == "UPSTREAM_INVALID_RESPONSE"


def test_update_privacy_settings_requires_visibility_query() -> None:
    response = client.post(
        "/api/user/privacy/settings",
        headers={"Authorization": "Bearer test-jwt-token"},
    )

    assert response.status_code == 422


def test_update_privacy_settings_maps_visibility_to_upstream_privacy(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_fetch_user_actgateway_post(path: str, headers: dict[str, str], params: dict[str, object]) -> dict[str, object]:
        captured["path"] = path
        captured["params"] = params
        captured["x-token"] = headers.get("x-token")
        return {
            "code": 0,
            "message": "Success",
            "traceID": "test-trace-id",
            "data": {
                "popup_shown": True,
                "privacy": True,
            },
        }

    monkeypatch.setattr("app.api.routers.user.fetch_user_actgateway_post", fake_fetch_user_actgateway_post)

    response = client.post(
        "/api/user/privacy/settings?visibility=visible&lang=en",
        headers={"Authorization": "Bearer test-jwt-token"},
    )

    assert response.status_code == 200
    assert captured["path"] == "battlereport/privacy/settings"
    assert captured["params"] == {"privacy": 1}
    assert captured["x-token"] == "test-jwt-token"
