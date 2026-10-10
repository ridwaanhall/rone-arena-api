from __future__ import annotations

import re
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from app.core.config import BASE_URL, PROJECT_VERSION
from app.main import app
from app.web.openapi_catalog import WEB_GROUPS, get_group_operations
from app.web.patch_notes import PATCH_NOTES
from app.web.routers.blog import _BLOG_POSTS
from app.web.routers.root import markdown_path

client = TestClient(app)
ORIGIN = BASE_URL.rstrip("/")


def _sitemap_paths() -> list[str]:
    root = ElementTree.fromstring(client.get("/sitemap.xml").text)
    return [loc.text.removeprefix(ORIGIN) or "/" for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]


def _all_operations() -> list[dict[str, object]]:
    return [operation for group in WEB_GROUPS for operation in get_group_operations(app, group)]


def test_llms_txt_follows_the_llmstxt_format() -> None:
    response = client.get("/llms.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    lines = response.text.splitlines()
    assert lines[0] == "# Rone Arena API"
    assert lines[1] == ""
    assert lines[2].startswith("> ")
    assert "## Optional" in lines
    assert PROJECT_VERSION in response.text
    # Every H2 section is a list of links.
    sections = re.split(r"^## .+$", response.text, flags=re.M)[1:]
    for section in sections:
        items = [line for line in section.splitlines() if line.startswith("- ")]
        assert items and all(re.match(r"- \[[^\]]+\]\([^)]+\)", item) for item in items)


def test_llms_txt_lists_every_endpoint_and_recent_post() -> None:
    text = client.get("/llms.txt").text

    for operation in _all_operations():
        assert f"[{operation['method']} {operation['api_path']}]({ORIGIN}{markdown_path(str(operation['web_path']))})" in text
    newest = max(_BLOG_POSTS, key=lambda post: str(post["published_at"]))
    assert f"{ORIGIN}/blog/{newest['slug']}.md" in text


def test_every_link_in_llms_txt_resolves() -> None:
    links = re.findall(r"\]\((https?://[^)]+)\)", client.get("/llms.txt").text)

    assert links
    for link in links:
        assert link.startswith(ORIGIN), link
        path = link.removeprefix(ORIGIN)
        response = client.get(path)
        assert response.status_code == 200, path


def test_every_sitemap_page_has_a_markdown_twin() -> None:
    for path in _sitemap_paths():
        response = client.get(markdown_path(path))
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/markdown"), path
        assert response.text.startswith("# "), path
        assert response.headers["link"] == f'<{ORIGIN}{path}>; rel="canonical"', path


def test_html_pages_link_their_markdown_twin_and_llms_txt() -> None:
    for path in ("/", "/showcase", "/blog", f"/blog/{_BLOG_POSTS[0]['slug']}", "/web/heroes"):
        text = client.get(path).text
        assert f'<link rel="alternate" type="text/markdown" href="{markdown_path(path)}" />' in text, path
        assert '<link rel="describedby" type="text/plain" href="/llms.txt" />' in text, path


def test_endpoint_markdown_documents_the_request() -> None:
    login = next(op for op in _all_operations() if op["api_path"] == "/api/user/auth/login")
    text = client.get(markdown_path(str(login["web_path"]))).text

    assert text.startswith("# Login with Verification Code")
    assert "`POST /api/user/auth/login`" in text
    assert "### Request body" in text
    assert f"curl -X POST '{ORIGIN}/api/user/auth/login'" in text

    info = next(op for op in _all_operations() if op["api_path"] == "/api/user/info")
    assert "**Sign-in required:**" in client.get(markdown_path(str(info["web_path"]))).text

    stats = next(op for op in _all_operations() if op["api_path"] == "/api/heroes/{hero_identifier}/stats")
    text = client.get(markdown_path(str(stats["web_path"]))).text
    assert "| `hero_identifier` | path |" in text


def test_llms_full_txt_holds_every_page() -> None:
    text = client.get("/llms-full.txt").text

    for operation in _all_operations():
        assert f"`{operation['method']} {operation['api_path']}`" in text
    for post in _BLOG_POSTS:
        assert f"# {post['title']}" in text
    assert f"## {PATCH_NOTES[0]['version']} ({PATCH_NOTES[0]['date']})" in text
    # Response examples stay in the per-endpoint pages to keep the file small.
    assert "## Example response" not in text


def test_unknown_markdown_pages_are_404() -> None:
    for path in ("/web/nope.md", "/web/heroes/nope.md", "/blog/nope.md"):
        assert client.get(path).status_code == 404, path


def test_page_cache_keeps_the_markdown_content_type(monkeypatch) -> None:
    from starlette.requests import Request
    from fastapi.responses import Response

    from app.web import page_cache

    monkeypatch.setattr(page_cache, "ENABLED", True)
    monkeypatch.setattr(page_cache, "_pages", {})
    calls = []

    @page_cache.page_cached
    def view(request: Request) -> Response:
        calls.append(1)
        return Response("# Page\n", media_type="text/markdown; charset=utf-8", headers={"Link": "<x>; rel=\"canonical\""})

    request = Request({"type": "http", "method": "GET", "path": "/x.md", "headers": [(b"host", b"arena.test")], "query_string": b""})
    view(request)
    cached = view(request)

    assert len(calls) == 1
    assert cached.body == b"# Page\n"
    assert cached.headers["content-type"] == "text/markdown; charset=utf-8"
    assert cached.headers["link"] == '<x>; rel="canonical"'
