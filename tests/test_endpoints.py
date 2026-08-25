from __future__ import annotations

from urllib.parse import urlparse
from xml.etree import ElementTree

from fastapi.testclient import TestClient


import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app


client = TestClient(app)


def test_docs_and_redoc_available() -> None:
    docs_response = client.get("/api/docs")
    redoc_response = client.get("/api/redoc")

    assert docs_response.status_code == 200
    assert redoc_response.status_code == 200


def test_docs_html_configures_persist_authorization() -> None:
    response = client.get("/api/docs")

    assert response.status_code == 200
    assert "persistAuthorization" in response.text
    assert ": true" in response.text


def test_docs_auth_script_route_removed() -> None:
    response = client.get("/api/docs/auth.js")

    assert response.status_code == 404


def test_api_docs_redirects_to_swagger() -> None:
    response = client.get("/docs", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/api/docs"


def test_api_index_exposes_only_hero_and_academy_services() -> None:
    response = client.get("/api")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "success"
    assert "version" in payload["meta"]
    assert "endpoints" in payload
    assert all("mpl_id" not in endpoint for endpoint in payload["endpoints"])


def test_openapi_documents_hero_query_constraints() -> None:
    openapi = client.get("/api/openapi.json").json()
    params = openapi["paths"]["/api/heroes/rank"]["get"]["parameters"]
    hero_detail_params = openapi["paths"]["/api/heroes/{hero_identifier}"]["get"]["parameters"]

    days_param = next(param for param in params if param["name"] == "days")
    rank_param = next(param for param in params if param["name"] == "rank")
    hero_identifier_param = next(param for param in hero_detail_params if param["name"] == "hero_identifier")

    assert days_param["schema"]["enum"] == ["1", "3", "7", "15", "30"]
    assert "$ref" in rank_param["schema"] or "enum" in rank_param["schema"]
    assert "numeric hero ID or hero name" in hero_identifier_param["description"]


def test_openapi_documents_academy_path_and_query_constraints() -> None:
    openapi = client.get("/api/openapi.json").json()
    op = openapi["paths"]["/api/academy/heroes/{hero_identifier}/trends"]["get"]
    params = op["parameters"]

    hero_id_param = next(param for param in params if param["name"] == "hero_identifier")
    days_param = next(param for param in params if param["name"] == "days")

    assert "numeric hero ID or hero name" in hero_id_param["description"]
    assert days_param["schema"]["enum"] == ["7", "15", "30"]


def test_openapi_login_request_example_keeps_schema_field_order() -> None:
    openapi = client.get("/api/openapi.json").json()
    schema = openapi["components"]["schemas"]["UserLoginRequest"]
    example = schema["example"]

    assert list(example.keys()) == ["role_id", "zone_id", "vc"]


def test_robots_txt_allows_all_crawlers() -> None:
    response = client.get("/robots.txt")
    content = response.text

    assert response.status_code == 200
    assert "User-agent: *" in content
    assert "Allow: /" in content
