"""Markdown versions of the web pages, plus `/llms.txt` and `/llms-full.txt`, for AI agents.

Follows https://llmstxt.org: `/llms.txt` is an H1, a blockquote summary, a few plain
paragraphs, then H2 lists of `[name](url): notes` links, with an `Optional` section an
agent may skip. Every web page has a markdown twin at the same URL plus `.md` (`/index.md`
for the home page), linked from the HTML head with `rel="alternate" type="text/markdown"`.

Everything here is built from the same data the HTML pages use (the OpenAPI schema, blog
posts, patch notes, showcase), so new endpoints and posts appear without edits. Only the
hand-written prose (`SUMMARY`, `ABOUT`, `KEY_FACTS`) needs updating when the product changes;
the `llms-txt` skill in `.claude/skills/` walks through that.
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import FastAPI

from app.core.config import ALTERNATIVE_ENDPOINT_URL, IS_AVAILABLE, PROJECT_VERSION
from app.web.openapi_catalog import GROUP_META, WEB_GROUPS, get_group_operations
from app.web.patch_notes import PATCH_NOTES, SECTIONS
from app.web.routers.blog import _BLOG_POSTS
from app.web.routers.root import SITE_NAME, SITE_ORIGIN, absolute_url, image_url, markdown_path
from app.web.showcase import SHOWCASE, SUBMIT_URL

SUMMARY = (
    "Free, unofficial REST API for Mobile Legends: Bang Bang game data: heroes, win rates, "
    "builds, counters, academy guides, player records and pro league results, returned as JSON, "
    "with an interactive web playground."
)

ABOUT = (
    "Rone Arena is a community-maintained project. It is not affiliated with or endorsed by "
    "Moonton; the game is named only to describe the data. Data comes from publicly accessible "
    "game services and is provided for informational and educational use."
)

KEY_FACTS: list[str] = [
    "Base URL: `{api}`. Every endpoint is a GET or POST under `/api/` and answers JSON.",
    "No API key. Public endpoints need no sign-in; `user` endpoints need `Authorization: Bearer <jwt>`, "
    "obtained by `POST /api/user/auth/send-vc` (a code sent to the player's in-game mail) then `POST /api/user/auth/login`.",
    "Heroes are addressed by numeric ID or by name (`hero_identifier`, for example `1` or `miya`).",
    "Image URLs in responses go through the wsrv.nl image proxy.",
    "A 503 response means maintenance or high traffic; read `alternative_endpoint` in the body for a fallback host.",
    "A 429 `UPSTREAM_RATE_LIMITED` means the game service is throttling; back off for a few minutes instead of retrying in parallel.",
    "If `{host}` answers 5xx or times out, the same API is served by the backup host at `{backup}`.",
    "The full machine-readable schema is the OpenAPI document at `{openapi}`.",
]

# Response examples longer than this are cut in the per-endpoint pages so a page stays readable.
_MAX_EXAMPLE_CHARS = 6000


def _url(path: str) -> str:
    return absolute_url(path)


def _md_url(path: str) -> str:
    return absolute_url(markdown_path(path))


def _cell(value: object) -> str:
    """Text safe to put in one markdown table cell."""
    text = re.sub(r"\s*\n\s*", " ", str(value if value is not None else "")).strip()
    return text.replace("|", "\\|")


def _first_sentence(text: str) -> str:
    """The opening sentence of a description, skipping list items and "Path parameters:" lead-ins."""
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("-") and not line.endswith(":"):
            return re.split(r"(?<=\.)\s", line, maxsplit=1)[0]
    return ""


def _fence(body: str, lang: str = "") -> str:
    # A longer fence than any backtick run inside keeps the block intact.
    longest = max((len(run) for run in re.findall(r"`+", body)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{body}\n{ticks}"


def _all_operations(app: FastAPI) -> list[tuple[str, dict[str, Any]]]:
    return [(group, operation) for group in WEB_GROUPS for operation in get_group_operations(app, group)]


def _operation_line(operation: dict[str, Any]) -> str:
    notes = _first_sentence(str(operation["description"])) or str(operation["summary"])
    flags = []
    if operation["requires_auth"]:
        flags.append("sign-in required")
    if operation["deprecated"]:
        flags.append("deprecated")
    suffix = f" ({', '.join(flags)})" if flags else ""
    return (
        f"- [{operation['method']} {operation['api_path']}]({_md_url(str(operation['web_path']))}): "
        f"{operation['summary']}{suffix}. {notes}"
    ).rstrip()


def _key_facts() -> list[str]:
    return [
        "- " + fact.format(
            api=_url("/api"),
            openapi=_url("/api/openapi.json"),
            host=SITE_ORIGIN.removeprefix("https://"),
            backup=f"{ALTERNATIVE_ENDPOINT_URL.rstrip('/')}/api",
        )
        for fact in KEY_FACTS
    ]


def _status_note() -> list[str]:
    if IS_AVAILABLE:
        return []
    return ["", "**Service notice:** the API is currently restricted (maintenance or high traffic). See " + _url("/") + "."]


def _post_path(post: dict[str, Any]) -> str:
    return f"/blog/{post['slug']}"


def _post_md_url(post: dict[str, Any]) -> str:
    return _md_url(_post_path(post))


def _sorted_posts() -> list[dict[str, object]]:
    return sorted(_BLOG_POSTS, key=lambda post: str(post.get("published_at") or ""), reverse=True)


# --- llms.txt -------------------------------------------------------------------------


def llms_txt(app: FastAPI) -> str:
    lines = [
        f"# {SITE_NAME}",
        "",
        f"> {SUMMARY}",
        "",
        f"{ABOUT} Current version: {PROJECT_VERSION}.",
        *_status_note(),
        "",
        *_key_facts(),
        "",
        "Every page listed below is markdown. Each page of the website has the same markdown twin: "
        "add `.md` to its URL (the home page is `/index.md`).",
        "",
        "## Docs",
        "",
        f"- [Overview]({_md_url('/')}): what the API covers, how to call it, and every endpoint by group",
        f"- [OpenAPI schema]({_url('/api/openapi.json')}): the machine-readable definition of every endpoint, parameter and response",
        f"- [Swagger UI]({_url('/api/docs')}): interactive API docs",
        f"- [Patch notes]({_md_url('/patch-notes')}): what changed in each release, in plain words",
        f"- [Showcase]({_md_url('/showcase')}): projects built on the API and the endpoints each page calls",
    ]

    for group in WEB_GROUPS:
        meta = GROUP_META[group]
        lines += ["", f"## {meta['title']} endpoints", "", f"{meta['description']} Group page: {_md_url(f'/web/{group}')}", ""]
        lines += [_operation_line(operation) for operation in get_group_operations(app, group)]

    posts = _sorted_posts()
    recent, older = posts[:3], posts[3:]
    lines += ["", "## Blog", ""]
    lines += [f"- [{post['title']}]({_post_md_url(post)}): {post['excerpt']}" for post in recent]

    lines += ["", "## Optional", ""]
    lines += [f"- [Full text]({_url('/llms-full.txt')}): every page above in one file"]
    lines += [f"- [Blog index]({_md_url('/blog')}): all posts, newest first"]
    lines += [f"- [{post['title']}]({_post_md_url(post)}): {post['excerpt']}" for post in older]
    return "\n".join(lines) + "\n"


def llms_full_txt(app: FastAPI) -> str:
    """Every markdown page in one file, for agents that want the whole site in context."""
    parts = [home_markdown(app), patch_notes_markdown(), showcase_markdown()]
    parts += [endpoint_markdown(group, operation, include_response=False) for group, operation in _all_operations(app)]
    parts += [blog_post_markdown(post) for post in _sorted_posts()]
    return "\n\n---\n\n".join(part.strip() for part in parts) + "\n"


# --- pages ----------------------------------------------------------------------------


def home_markdown(app: FastAPI) -> str:
    operations = _all_operations(app)
    lines = [
        f"# {SITE_NAME}",
        "",
        f"> {SUMMARY}",
        "",
        ABOUT,
        *_status_note(),
        "",
        "## How to call it",
        "",
        *_key_facts(),
        "",
        "Example:",
        "",
        _fence(f"curl {_url('/api/heroes/rank')}", "bash"),
        "",
        "## Pages",
        "",
        f"- Playground: {_url('/web/heroes')} (forms for every endpoint, with readable responses and code in eight languages)",
        f"- API docs: {_url('/api/docs')}",
        f"- Showcase: {_md_url('/showcase')}",
        f"- Patch notes: {_md_url('/patch-notes')}",
        f"- Blog: {_md_url('/blog')}",
        f"- Python SDK: `pip install rone-arena`",
        "",
        f"## Endpoints ({len(operations)} in {len(WEB_GROUPS)} groups)",
    ]
    for group in WEB_GROUPS:
        lines += ["", f"### {GROUP_META[group]['title']}", "", str(GROUP_META[group]["description"]), ""]
        lines += [_operation_line(operation) for operation in get_group_operations(app, group)]
    return "\n".join(lines) + "\n"


def group_markdown(app: FastAPI, group: str) -> str:
    meta = GROUP_META[group]
    operations = get_group_operations(app, group)
    lines = [
        f"# {meta['title']} endpoints",
        "",
        f"> {meta['description']} Part of the {SITE_NAME}: {_md_url('/')}",
        "",
        f"{len(operations)} endpoints. Each link opens that endpoint's full reference.",
        "",
        *[_operation_line(operation) for operation in operations],
    ]
    return "\n".join(lines) + "\n"


def _parameter_row(parameter: dict[str, Any]) -> str:
    type_name = f"array of {parameter['item_type']}" if parameter["is_array"] else str(parameter["type"])
    notes = [str(parameter["description"] or "")]
    if parameter["enum_values"]:
        notes.append("One of: " + ", ".join(f"`{value}`" for value in parameter["enum_values"]) + ".")
    if parameter["minimum"] is not None or parameter["maximum"] is not None:
        notes.append(f"Range: {parameter['minimum'] if parameter['minimum'] is not None else ''}..{parameter['maximum'] if parameter['maximum'] is not None else ''}.")
    default = f"`{parameter['default_display']}`" if parameter["default_display"] else ""
    return "| " + " | ".join(
        _cell(value)
        for value in (
            f"`{parameter['name']}`",
            parameter["location"],
            type_name,
            "yes" if parameter["required"] else "no",
            default,
            " ".join(note for note in notes if note),
        )
    ) + " |"


def _curl(operation: dict[str, Any]) -> str:
    query = [
        f"{parameter['name']}={parameter['default_display'] or '<' + parameter['name'] + '>'}"
        for parameter in operation["parameters"]
        if parameter["location"] == "query" and parameter["required"]
    ]
    url = _url(str(operation["api_path"])) + (("?" + "&".join(query)) if query else "")
    parts = [f"curl -X {operation['method']} '{url}'"]
    if operation["requires_auth"]:
        parts.append("-H 'Authorization: Bearer <jwt>'")
    if operation["request_body"]:
        body = json.dumps(json.loads(operation["request_body"]["example_json"]))
        parts += ["-H 'Content-Type: application/json'", f"-d '{body}'"]
    return " \\\n  ".join(parts)


def endpoint_markdown(group: str, operation: dict[str, Any], include_response: bool = True) -> str:
    group_title = GROUP_META[group]["title"]
    lines = [
        f"# {operation['summary']}",
        "",
        f"> `{operation['method']} {operation['api_path']}`: {group_title} endpoint of the {SITE_NAME}.",
        "",
    ]
    if operation["deprecated"]:
        lines += ["**Deprecated:** still answers, but will not receive further work. Prefer another endpoint.", ""]
    if operation["requires_auth"]:
        lines += [
            "**Sign-in required:** send `Authorization: Bearer <jwt>`. Get the JWT from "
            "`POST /api/user/auth/send-vc` then `POST /api/user/auth/login`.",
            "",
        ]
    description = str(operation["description"]).strip()
    if description:
        lines += [description, ""]

    lines += ["## Request", "", f"`{operation['method']} {_url(str(operation['api_path']))}`", ""]
    if operation["parameters"]:
        lines += [
            "### Parameters",
            "",
            "| Name | In | Type | Required | Default | Description |",
            "| --- | --- | --- | --- | --- | --- |",
            *[_parameter_row(parameter) for parameter in operation["parameters"]],
            "",
        ]
    if operation["request_body"]:
        lines += [
            "### Request body",
            "",
            f"`{operation['request_body']['content_type']}`" + (", required" if operation["request_body"]["required"] else ""),
            "",
            _fence(str(operation["request_body"]["example_json"]), "json"),
            "",
        ]
    lines += ["### Example", "", _fence(_curl(operation), "bash"), ""]

    example = operation.get("response_example_json")
    if include_response and example:
        if len(example) > _MAX_EXAMPLE_CHARS:
            example = example[:_MAX_EXAMPLE_CHARS].rstrip() + "\n... (cut; see the OpenAPI schema for the full example)"
        lines += ["## Example response", "", _fence(str(example), "json"), ""]

    lines += [
        "## Links",
        "",
        f"- Try it in the playground: {_url(str(operation['web_path']))}",
        f"- {group_title} endpoints: {_md_url(f'/web/{group}')}",
        f"- OpenAPI schema: {_url('/api/openapi.json')}",
    ]
    return "\n".join(lines) + "\n"


def showcase_markdown() -> str:
    lines = [
        "# Showcase: projects built on the Rone Arena API",
        "",
        "> Projects the community built on the Rone Arena API, with the endpoints behind each page.",
        "",
        f"Add your own project with one issue: {SUBMIT_URL}",
    ]
    for product in SHOWCASE:
        credits = ", ".join(f"[{name}]({link})" for name, link in product["contributors"])
        lines += [
            "",
            f"## {product['name']}",
            "",
            f"{product['url']}",
            "",
            str(product["about"]),
            "",
            f"What it shows: {product['shows']}",
            "",
            f"Contributors: {credits}",
            "",
            "| Feature | Endpoints |",
            "| --- | --- |",
        ]
        for label, endpoints in product["features"]:
            calls = ", ".join(f"`{method} {path}`" for method, path in endpoints)
            lines.append(f"| {_cell(label)} | {_cell(calls)} |")
    return "\n".join(lines) + "\n"


def patch_notes_markdown() -> str:
    lines = [
        "# Patch notes: what is new in Rone Arena API",
        "",
        "> What is new, improved, fixed and removed in each release, in plain words. Newest first.",
    ]
    for release in PATCH_NOTES:
        lines += ["", f"## {release['version']} ({release['date']})", "", str(release["summary"])]
        for key, heading in SECTIONS:
            points = release.get(key) or []
            if points:
                lines += ["", f"### {heading}", "", *[f"- {point}" for point in points]]
    return "\n".join(lines) + "\n"


def blog_list_markdown() -> str:
    lines = [
        "# Blog: tutorials and release notes",
        "",
        "> Guides, release notes, and walkthroughs for the Rone Arena API & Web. Newest first.",
        "",
    ]
    lines += [
        f"- [{post['title']}]({_post_md_url(post)}) ({post['published_at']}, {post['category']}): {post['excerpt']}"
        for post in _sorted_posts()
    ]
    return "\n".join(lines) + "\n"


def blog_post_markdown(post: dict[str, Any]) -> str:
    lines = [
        f"# {post['title']}",
        "",
        f"> {post['excerpt']}",
        "",
        f"Published {post['published_at']} · {post['category']} · {post['read_time']} · {_url(_post_path(post))}",
        "",
        f"![{post['title']}]({image_url(str(post['cover_image']))})",
    ]
    if post.get("key_points"):
        lines += ["", "## Key points", "", *[f"- {point}" for point in post["key_points"]]]
    for section in post.get("sections") or []:
        lines += ["", f"## {section['heading']}", "", str(section["body"])]
        if section.get("bullets"):
            lines += ["", *[f"- {bullet}" for bullet in section["bullets"]]]
        if section.get("image"):
            lines += ["", f"![{section.get('image_note') or section['heading']}]({image_url(str(section['image']))})"]
        if section.get("callout"):
            lines += ["", f"> **Note:** {section['callout']}"]
    return "\n".join(lines) + "\n"
