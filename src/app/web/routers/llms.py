"""`/llms.txt`, `/llms-full.txt` and the `.md` twin of every web page (see `app/web/llms.py`)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response

from app.web import llms
from app.web.openapi_catalog import WEB_GROUPS, get_group_operations
from app.web.page_cache import page_cached
from app.web.routers.blog import _get_blog_post_or_404
from app.web.routers.root import _normalize_path, absolute_url

router = APIRouter(tags=["web"])


def _markdown(body: str, html_path: str) -> Response:
    # The canonical Link header keeps search engines on the HTML page.
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers={"Link": f'<{absolute_url(html_path)}>; rel="canonical"'},
    )


@router.get(path="/llms.txt", include_in_schema=False, name="web.llms_txt")
@page_cached
def llms_txt(request: Request) -> PlainTextResponse:
    return PlainTextResponse(llms.llms_txt(request.app))


@router.get(path="/llms-full.txt", include_in_schema=False, name="web.llms_full_txt")
@page_cached
def llms_full_txt(request: Request) -> PlainTextResponse:
    return PlainTextResponse(llms.llms_full_txt(request.app))


@router.get(path="/index.md", include_in_schema=False)
@page_cached
def home_md(request: Request) -> Response:
    return _markdown(llms.home_markdown(request.app), "/")


@router.get(path="/tools/standings.md", include_in_schema=False)
@page_cached
def standings_md(request: Request) -> Response:
    return _markdown(llms.standings_markdown(), "/tools/standings")


@router.get(path="/showcase.md", include_in_schema=False)
@page_cached
def showcase_md(request: Request) -> Response:
    return _markdown(llms.showcase_markdown(), "/showcase")


@router.get(path="/patch-notes.md", include_in_schema=False)
@page_cached
def patch_notes_md(request: Request) -> Response:
    return _markdown(llms.patch_notes_markdown(), "/patch-notes")


@router.get(path="/blog.md", include_in_schema=False)
@page_cached
def blog_list_md(request: Request) -> Response:
    return _markdown(llms.blog_list_markdown(), "/blog")


@router.get(path="/blog/{slug}.md", include_in_schema=False)
@page_cached
def blog_post_md(request: Request, slug: str) -> Response:
    post = _get_blog_post_or_404(slug)
    return _markdown(llms.blog_post_markdown(post), f"/blog/{post['slug']}")


@router.get(path="/web/{group}.md", include_in_schema=False)
@page_cached
def web_group_md(request: Request, group: str) -> Response:
    if group not in WEB_GROUPS:
        raise HTTPException(status_code=404, detail="Web group not found")
    return _markdown(llms.group_markdown(request.app, group), f"/web/{group}")


@router.get(path="/web/{group}/{endpoint_path:path}.md", include_in_schema=False)
@page_cached
def web_endpoint_md(request: Request, group: str, endpoint_path: str) -> Response:
    if group not in WEB_GROUPS:
        raise HTTPException(status_code=404, detail="Web group not found")
    web_path = _normalize_path(f"/web/{group}/{endpoint_path}")
    for operation in get_group_operations(request.app, group):
        if _normalize_path(str(operation["web_path"])) == web_path:
            return _markdown(llms.endpoint_markdown(group, operation), web_path)
    raise HTTPException(status_code=404, detail="Web endpoint not found")
