from __future__ import annotations

import json
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.core import http as upstream
from app.core import images
from app.core.images import wsrv_json, wsrv_url
from app.main import app

client = TestClient(app)


def proxied(url: str) -> str:
    return f"https://wsrv.nl/?url={quote(url, safe='')}"


@pytest.mark.parametrize(
    "url",
    [
        "https://akmweb.youngjoygame.com/web/gms/image/a.png",
        "https://akmweb.youngjoygame.com/web/svnres/img/b.SVG",
        "http://akmpicture.youngjoygame.com/dist/face/c.jpeg",
        "https://cdn.example.test/d.webp",
    ],
)
def test_image_urls_including_svg_are_proxied(url: str) -> None:
    assert wsrv_url(url) == proxied(url)


def test_signed_urls_keep_their_query_inside_the_encoded_target() -> None:
    url = "https://cdn.example.test/e.png?X-Amz-Signature=abc&X-Amz-Expires=1"

    assert wsrv_url(url) == proxied(url)
    assert wsrv_url(url).count("?") == 1


@pytest.mark.parametrize(
    "value",
    [
        "https://rone.dev/static/img/favicon/favicon.ico",
        "https://www.mobilelegends.com/page",
        "https://wsrv.nl/?url=https://ik.imagekit.io/x/y.png",
        "https://wsrv.nl?url=https://ik.imagekit.io/x/y.png",
        "http://127.0.0.1:8000/images/z.png",
        "http://localhost/z.png",
        "/images/blog/relative.webp",
        "Plain text ending in .png",
        "http://[bad.png",
    ],
)
def test_other_values_are_left_alone(value: str) -> None:
    assert wsrv_url(value) == value


def test_wsrv_json_rewrites_nested_values_only() -> None:
    data = {"head": "https://cdn.example.test/a.png", "list": [{"icon": "https://cdn.example.test/b.svg"}], "id": 7, "name": "Miya"}

    assert wsrv_json(data) == {
        "head": proxied("https://cdn.example.test/a.png"),
        "list": [{"icon": proxied("https://cdn.example.test/b.svg")}],
        "id": 7,
        "name": "Miya",
    }


def test_use_wsrv_false_returns_original_urls(monkeypatch) -> None:
    monkeypatch.setattr(images, "USE_WSRV", False)

    assert wsrv_url("https://cdn.example.test/a.png") == "https://cdn.example.test/a.png"


def test_upstream_json_images_are_proxied(monkeypatch) -> None:
    import httpx

    payload = {"data": {"records": [{"head": "https://akmweb.youngjoygame.com/web/gms/image/a.jpg"}]}}
    http_client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    monkeypatch.setattr(upstream, "_get_client", lambda: http_client)

    result = upstream.request_json(method="GET", url="https://upstream.test/x", headers={})

    assert result["data"]["records"][0]["head"] == proxied("https://akmweb.youngjoygame.com/web/gms/image/a.jpg")


def test_openapi_examples_show_proxied_images() -> None:
    text = json.dumps(client.get("/api/openapi.json").json())

    assert "https://akmweb.youngjoygame.com" not in text
    assert "wsrv.nl/?url=https%3A%2F%2Fakmweb.youngjoygame.com" in text


def test_web_pages_serve_no_unproxied_images() -> None:
    page = client.get("/blog/rone-arena-1-1-0-release-notes").text

    assert 'src="https://arena.rone.dev/images' not in page
    assert 'src="/images' not in page
    assert "wsrv.nl/?url=https%3A%2F%2Farena.rone.dev%2Fimages%2Fblog%2F" in page
