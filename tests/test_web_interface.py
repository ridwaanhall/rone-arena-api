from __future__ import annotations

import os
import sys
from collections import defaultdict

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.config import PROJECT_VERSION
from app.main import app
from app.web.openapi_catalog import get_group_operations


client = TestClient(app)


WEB_GROUPS = {"user", "heroes", "academy", "addon"}


def test_landing_page_has_docs_and_demo_options() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Read the API docs" in response.text
    assert "Open the playground" in response.text
    assert "/api/docs" in response.text
    assert "/web/user" in response.text
    assert "family=Archivo:wdth,wght" in response.text
    assert "IBM+Plex+Mono" in response.text
    assert "rone.dev/static/img/favicon/favicon.ico" in response.text
    assert "application/ld+json" in response.text
    assert "/static/css/arena.css?v=" in response.text
    assert "/static/js/arena.js?v=" in response.text
    assert "/static/js/home.js?v=" in response.text
    assert "data-live-rank" in response.text
    assert "Not Signed In" in response.text
    assert "Sign In" in response.text
    assert "API version" in response.text


def test_landing_page_indexes_every_endpoint() -> None:
    response = client.get("/")
    operations = [op for group in ("user", "heroes", "academy", "addon") for op in get_group_operations(app, group)]

    assert f"{len(operations)} endpoints in 4 groups" in response.text
    for operation in operations:
        assert f'href="{operation["web_path"]}"' in response.text


def test_showcase_links_sister_sites_to_real_endpoints() -> None:
    from app.web.showcase import SHOWCASE

    response = client.get("/showcase")
    documented = {
        (method.upper(), path)
        for path, item in client.get("/api/openapi.json").json()["paths"].items()
        for method in item
    }

    assert response.status_code == 200
    assert "https://arena-academy.rone.dev/" in response.text
    assert "https://arena-card.rone.dev/" in response.text
    for product in SHOWCASE:
        for _, endpoints in product["features"]:
            for method, path in endpoints:
                # A renamed or removed endpoint would silently leave a dead showcase row.
                assert (method, path) in documented, (product["name"], method, path)


def test_home_page_shows_both_sister_sites() -> None:
    response = client.get("/")

    assert "Arena Academy" in response.text
    assert "Arena Card" in response.text
    assert 'href="/showcase"' in response.text


def test_ui_avoids_generic_ai_template_tells() -> None:
    # Guard rails from the design research: no stock fonts, no decorative glow,
    # no gradient text, no em dashes in interface copy.
    css = client.get("/static/css/arena.css").text
    pages = [client.get(path).text for path in ("/", "/showcase", "/web/heroes", "/blog")]

    for banned in ("Inter", "Geist", "Space Grotesk", "backdrop-filter", "radial-gradient", "background-clip: text"):
        assert banned not in css
    for page in pages:
        assert "—" not in page.split("<main>")[1].split("</main>")[0]


def test_site_script_manages_session_and_theme() -> None:
    response = client.get("/static/js/arena.js")

    assert response.status_code == 200
    assert 'const AUTH_KEY = "arena_user_auth";' in response.text
    assert "24 * 60 * 60 * 1000" in response.text
    assert "renderNavbarState()" in response.text
    assert "arena_theme" in response.text
    assert "window.ArenaWebAuth" in response.text


def test_static_assets_are_versioned_by_content_hash() -> None:
    from app.web.routers.root import ASSET_VERSION

    response = client.get("/web/heroes")

    assert f"/static/css/arena.css?v={ASSET_VERSION}" in response.text
    assert f"/static/js/playground.js?v={ASSET_VERSION}" in response.text
    assert client.get("/static/css/arena.css").status_code == 200


def test_navbar_shows_api_version_badge() -> None:
    response = client.get("/web/user")

    assert response.status_code == 200
    assert "Rone Arena" in response.text
    assert f"v{PROJECT_VERSION}" in response.text
    assert "https://buymeacoffee.com/ridwaanhall" in response.text
    assert "user-menu-trigger" in response.text
    assert "user-menu-panel" in response.text


def test_web_group_pages_are_available() -> None:
    for group in WEB_GROUPS:
        response = client.get(f"/web/{group}")

        assert response.status_code == 200
        assert f"/web/{group}" in response.text


def test_mobile_endpoint_jump_strip_is_present_on_group_pages() -> None:
    response = client.get("/web/academy")

    assert response.status_code == 200
    assert "data-mobile-endpoint-strip" in response.text
    assert "Jump to endpoint" in response.text


def test_web_pages_cover_all_documented_group_operations() -> None:
    openapi = client.get("/api/openapi.json").json()
    grouped_operation_ids: dict[str, list[str]] = defaultdict(list)

    for path_item in openapi["paths"].values():
        for method in ("get", "post"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])
            if not tags:
                continue
            group = tags[0]
            if group not in WEB_GROUPS:
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str):
                grouped_operation_ids[group].append(operation_id)

    for group, operation_ids in grouped_operation_ids.items():
        response = client.get(f"/web/{group}")
        assert response.status_code == 200

        for operation_id in operation_ids:
            assert f'data-operation-id="{operation_id}"' in response.text


def test_user_login_page_has_jwt_cache_script() -> None:
    response = client.get("/web/user/auth/login")
    playground_js = client.get("/static/js/playground.js").text

    assert response.status_code == 200
    assert "/static/js/arena.js" in response.text
    assert "/static/js/playground.js" in response.text
    assert "/api/user/auth/login" in response.text
    assert "hydrateUserInfoIfMissing" in playground_js
    assert "writeAuth" in playground_js


def test_user_privacy_page_renders_get_and_post_forms() -> None:
    response = client.get("/web/user/privacy/settings")

    assert response.status_code == 200
    assert 'data-api-path="/api/user/privacy/settings"' in response.text
    assert 'data-method="GET"' in response.text
    assert 'data-method="POST"' in response.text
    assert "visibility" in response.text


def test_role_and_lane_array_params_render_checkbox_cards() -> None:
    response = client.get("/web/academy/heroes")

    assert response.status_code == 200
    assert 'data-param-kind="checkbox-group"' in response.text
    assert 'data-param-choice="true"' in response.text
    assert "tank" in response.text
    assert "fighter" in response.text
    assert "assassin" in response.text
    assert "marksman" in response.text
    assert "support" in response.text


def test_user_privacy_post_without_body_does_not_render_body_editor() -> None:
    response = client.get("/web/user/privacy/settings")

    assert response.status_code == 200
    assert "<textarea" not in response.text


def test_web_operations_keep_openapi_router_order() -> None:
    openapi = client.get("/api/openapi.json").json()
    openapi_user_order: list[str] = []

    for path_item in openapi["paths"].values():
        for method in ("get", "post"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags", [])
            if not tags or tags[0] != "user":
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str):
                openapi_user_order.append(operation_id)

    web_order = [operation["operation_id"] for operation in get_group_operations(app, "user")]
    assert web_order == openapi_user_order


def test_login_description_renders_markdown_tokens_as_readable_html() -> None:
    response = client.get("/web/user/auth/login")

    assert response.status_code == 200
    assert "**role_id**" not in response.text
    assert "<strong>role_id</strong>" in response.text
    assert "&lt;strong" not in response.text

    privacy_response = client.get("/web/user/privacy/settings")
    assert privacy_response.status_code == 200
    assert "<code" in privacy_response.text


def test_parameter_description_renders_inline_code_and_constraints() -> None:
    response = client.get("/web/academy/equipment")

    assert response.status_code == 200
    assert "<code>en</code>" in response.text
    assert "Minimum: 1." in response.text


def test_equipment_description_preserves_nested_list_indentation() -> None:
    response = client.get("/web/academy/equipment")

    assert response.status_code == 200
    assert "<li><strong>records</strong>: Array of equipment entries, each containing:<ul>" in response.text
    assert "<li><strong>data</strong>:<ul>" in response.text


def test_response_panel_has_readable_and_raw_views() -> None:
    response = client.get("/web/addon/win-rate-calculator")

    assert response.status_code == 200
    assert "Languages" in response.text
    assert "javascript" in response.text
    assert "python" in response.text
    assert "go" in response.text
    assert "node (axios)" in response.text
    assert "php" in response.text
    assert "java" in response.text
    assert "csharp" in response.text
    assert "data-response-readable" in response.text
    assert "data-response-content" in response.text
    assert "data-language-content" in response.text
    assert "data-copy-btn" in response.text
    assert "Copy Snippet" in response.text
    assert "Copy Response" in response.text

    curl_index = response.text.find('data-lang-key="curl"')
    python_index = response.text.find('data-lang-key="python"')
    javascript_index = response.text.find('data-lang-key="javascript"')
    assert -1 not in (curl_index, python_index, javascript_index)
    assert curl_index < python_index < javascript_index


def test_request_body_editor_uses_six_rows() -> None:
    response = client.get("/web/user/auth/login")

    assert response.status_code == 200
    assert 'rows="5"' in response.text


def test_login_request_body_example_follows_schema_order() -> None:
    response = client.get("/web/user/auth/login")

    assert response.status_code == 200
    expected = "{\n  &#34;role_id&#34;: 1234567890,\n  &#34;zone_id&#34;: 1234,\n  &#34;vc&#34;: 1234\n}"
    assert expected in response.text


def test_web_script_contains_readable_table_and_image_render_helpers() -> None:
    response = client.get("/static/js/playground.js")

    assert response.status_code == 200
    assert "looksLikeImageUrl" in response.text
    assert "createObjectTable" in response.text
    assert "buildCurl" in response.text
    assert "buildLanguageSnippets" in response.text
    assert "setupDescriptionToggles" in response.text
    assert "setupCopyButtons" in response.text
    assert "setupLanguageTabs" in response.text
    assert "setupEndpointFilter" in response.text


def test_footer_contains_repository_link() -> None:
    response = client.get("/web/user")

    assert response.status_code == 200
    assert "https://github.com/ridwaanhall/rone-arena-api" in response.text


def test_method_badges_are_colorized() -> None:
    response = client.get("/web/user/auth/login")

    assert response.status_code == 200
    assert 'class="method method--post"' in response.text

    heroes = client.get("/web/heroes")
    assert 'class="method method--get"' in heroes.text


def test_description_expand_markers_present() -> None:
    response = client.get("/web/user/auth/login")

    assert response.status_code == 200
    assert "data-desc-toggle" in response.text
    assert "Show more" in response.text


def test_sign_out_requires_confirmation_prompt() -> None:
    response = client.get("/web/user")

    assert response.status_code == 200
    assert "Are you sure you want to sign out?" in response.text
    assert "/api/user/auth/logout" in response.text


def test_blog_list_page_renders_tutorial_cards() -> None:
    response = client.get("/blog")

    assert response.status_code == 200
    assert "Tutorial &amp; Blog" in response.text or "Tutorial & Blog" in response.text
    assert "Rone Arena Web v3.2.2 Changelog" in response.text
    assert "How to Use the Rone Arena API Web Project" in response.text
    assert "/blog/how-to-use-mlbb-public-data-api-web-project" in response.text
    assert "Read Featured Post" in response.text
    assert "High-priority reading" in response.text


def test_blog_changelog_page_renders_release_scope() -> None:
    response = client.get("/blog/mlbb-api-web-v3-2-2-changelog-v3-2-1-v3-2-2")

    assert response.status_code == 200
    assert "21 files changed, 1305 insertions, 338 deletions" in response.text
    assert "Migration Notes for Integrators" in response.text


def test_blog_detail_page_uses_slug_url_and_shows_steps() -> None:
    response = client.get("/blog/how-to-use-mlbb-public-data-api-web-project")

    assert response.status_code == 200
    assert "Step 1: Open the Website" in response.text
    assert "Mandatory for User Endpoints" in response.text
    assert "/images/blog/tutorial-step-2-signin-send-vc.webp" in response.text


def test_navbar_includes_tutorial_button() -> None:
    response = client.get("/web/user")

    assert response.status_code == 200
    assert "Tutorials" in response.text
    assert "href=\"/blog\"" in response.text


def test_endpoint_page_title_uses_operation_summary() -> None:
    response = client.get("/web/heroes/heroes/{hero_identifier}/wallpapers")

    assert response.status_code == 200
    assert "<title>Hero Wallpapers - Heroes API / Rone Arena API &amp; Web</title>" in response.text
    assert "Heroe Endpoint" not in response.text


def test_sidebar_breaks_paths_only_after_slashes() -> None:
    response = client.get("/web/heroes")

    assert "/<wbr>{hero_identifier}/<wbr>wallpapers" in response.text
    assert "&lt;wbr&gt;" not in response.text







def test_blog_list_includes_v4_0_4_release_notes() -> None:
    response = client.get("/blog")

    assert response.status_code == 200
    assert "Rone Arena Web v4.0.7 Release Notes (4.0.6 to 4.0.8)" in response.text
    assert "Rone Arena Web v4.0.4 Release Notes (3.2.3 -&gt; 4.0.4)" in response.text or "Rone Arena Web v4.0.4 Release Notes (3.2.3 -> 4.0.4)" in response.text


def test_blog_detail_v4_0_7_release_notes_includes_typescript_alternative() -> None:
    response = client.get("/blog/mlbb-api-web-v4-0-7-release-notes-4-0-6-to-4-0-8")

    assert response.status_code == 200
    assert "Version move: 4.0.6 -&gt; 4.0.8" in response.text or "Version move: 4.0.6 -> 4.0.8" in response.text


def test_blog_detail_v4_0_4_release_notes_no_commit_hash() -> None:
    response = client.get("/blog/mlbb-api-web-v4-0-4-release-notes-3-2-3-4-0-4")

    assert response.status_code == 200
    assert "Version move: 3.2.3 -&gt; 4.0.4" in response.text or "Version move: 3.2.3 -> 4.0.4" in response.text
    assert "OpenMLBB SDK documentation" in response.text
    assert "799250329d76cefce207c7ed425f2606c5d57a62" not in response.text



