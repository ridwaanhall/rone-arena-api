from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.web.routers.root import _shared_context, templates

router = APIRouter(tags=["web"])


_BLOG_POSTS: list[dict[str, object]] = [
    {
        "title": "Migrating to Rone Arena: What Changed and What You Need to Update",
        "slug": "migrating-to-rone-arena",
        "excerpt": "The MLBB Public Data API is now Rone Arena. Every endpoint path is unchanged, but the hostname moved and the Python package was renamed and republished. Here is everything you need to update.",
        "cover_image": "/images/blog/rebrand.webp",
        "published_at": "2026-08-29",
        "read_time": "7 min read",
        "category": "Announcement",
        "is_featured": True,
        "is_pinned": True,
        "key_points": [
            "Every API endpoint path is unchanged - only the hostname moved",
            "pip install OpenMLBB no longer works; the package is now rone-arena",
            "The SDK version restarts at 1.0.0 after the old package reached 4.2.0",
        ],
        "sections": [
            {
                "heading": "What Changed at a Glance",
                "body": "The project formerly published as the MLBB Public Data API is now Rone Arena. Four public names moved, and the rest of this post covers exactly what each one means for your integration.",
                "bullets": [
                    "API host: mlbb.rone.dev -> arena.rone.dev",
                    "Python package: OpenMLBB -> rone-arena",
                    "Hero data site: MLBB Academy -> arena-academy.rone.dev",
                    "Player profile: MLBB Identity Card -> arena-card.rone.dev",
                ],
            },
            {
                "heading": "Updating Your API Calls",
                "body": "Every endpoint path is identical to before, so a single find-and-replace on your base URL is the whole migration. Replace the host and everything after /api/ stays exactly as it was.",
                "bullets": [
                    "Old: https://mlbb.rone.dev/api/heroes",
                    "New: https://arena.rone.dev/api/heroes",
                    "No path, parameter, or response shape changed in this move.",
                ],
                "callout": "The old host currently redirects, but a 301 will not carry an authenticated POST through - most HTTP clients downgrade it to a GET. Point write requests at the new host directly rather than relying on the redirect.",
            },
            {
                "heading": "Regenerating Typed Clients",
                "body": "The OpenAPI tag mlbb was renamed to heroes. Tags become class and method names in generated clients, so anything built from the schema needs regenerating even though no URL moved. The full tag set is now user, heroes, academy, and addon.",
                "bullets": [
                    "Only the tag changed - the paths behind it are untouched.",
                    "Hand-written clients that call URLs directly need no change beyond the hostname.",
                    "Generated clients will see renamed classes or methods wherever the mlbb tag was used.",
                ],
            },
            {
                "heading": "Reading Service Status",
                "body": "A 503 previously meant one undifferentiated unavailable state. The response body now distinguishes two independent conditions, so retry logic can tell them apart.",
                "bullets": [
                    "Maintenance: the service is being worked on and there is no alternative host to try.",
                    "High traffic: this host is shedding load and names a failover endpoint in alternative_endpoint.",
                    "If you retry on 503, read alternative_endpoint rather than assuming a host.",
                ],
            },
            {
                "heading": "Migrating the Python Package",
                "body": "OpenMLBB has been removed from PyPI. Installs of the old name will fail, so this is a breaking change - there is no transitional shim package. Install rone-arena and update your imports.",
                "bullets": [
                    "Install: pip install rone-arena (was: pip install OpenMLBB)",
                    "Import: from rone_arena import RoneArena (was: from OpenMLBB import OpenMLBB)",
                    "Construct: client = RoneArena() (was: client = OpenMLBB())",
                ],
                "callout": "The version number goes backwards. The old package had reached 4.2.0; the renamed one restarts at 1.0.0, because it is a new package rather than a continuation. A rone-arena 4.2.0 was briefly published by mistake and has been yanked, so a fresh install resolves to 1.0.0. Avoid a >=4 style pin.",
            },
            {
                "heading": "New: Typed Service Errors",
                "body": "A 503 from the API now raises ServiceUnavailableError instead of failing during response parsing, so maintenance windows are catchable rather than surfacing as a confusing decode error. Import it alongside the client and handle it where you already handle network failures.",
                "bullets": [
                    "from rone_arena import RoneArena, ServiceUnavailableError",
                    "The exception carries the status message and any failover endpoint the API named.",
                ],
            },
            {
                "heading": "If You Use the Websites",
                "body": "Both companion sites moved to new addresses, but nothing is lost in the move.",
                "bullets": [
                    "You stay signed in. Saved sessions, theme, and language carry across the rename automatically the first time you load the new address.",
                    "Update bookmarks to arena-academy.rone.dev and arena-card.rone.dev.",
                    "Sign-in on the player profile is working again. It had been failing because every API host it was configured against had been retired.",
                ],
            },
            {
                "heading": "Deprecated Endpoints",
                "body": "These still respond and are not being removed on a published date, but they are marked deprecated in the schema and will not receive further work. Plan to move off them.",
                "bullets": [
                    "GET /api/academy/heroes/catalog",
                    "GET /api/academy/heroes/ratings",
                    "GET /api/academy/heroes/ratings/{subject}",
                    "GET /api/addon/ip",
                    "GET /api/user/stats",
                    "GET /api/user/season",
                    "GET /api/user/friends",
                    "GET /api/user/matches",
                    "GET /api/user/matches/{match_id}",
                    "GET /api/user/matches/hero/{hero_identifier}",
                    "GET /api/user/heroes/frequent",
                    "GET /api/user/privacy/settings",
                    "POST /api/user/privacy/settings",
                ],
            },
            {
                "heading": "Why the Rename",
                "body": "MLBB and Mobile Legends: Bang Bang are trademarks of Shanghai Moonton Technology. Using them as this project's own name - in a package name, a domain, or a product title - puts someone else's mark in the position that identifies who made the software. That is the use trademark law restricts, and it was never something this project was entitled to.",
                "bullets": [
                    "Describing what the data covers has not changed: this is still an API for Mobile Legends: Bang Bang game data, and it still says so.",
                    "What moved is the branding. The project is Rone Arena; the game is named only as a description of the data it serves.",
                    "Rone Arena is unofficial and community-maintained, with no affiliation to or endorsement by Moonton.",
                ],
            },
            {
                "heading": "Where the Code Lives",
                "body": "All four repositories were renamed to match the new brand. Existing GitHub links redirect, but update your remotes when convenient.",
                "bullets": [
                    "rone-arena-api - REST API and web playground",
                    "rone-arena-python - Python SDK",
                    "arena-academy - hero data, stats and builds",
                    "arena-card - player profile cards",
                ],
            },
        ],
    },
    {
        "title": "Rone Arena Web v4.0.7 Release Notes (4.0.6 to 4.0.8)",
        "slug": "mlbb-api-web-v4-0-7-release-notes-4-0-6-to-4-0-8",
        "excerpt": "Version 4.0.8 extends the 4.0.6 maintenance hardening with clearer availability defaults, refreshed SDK versioning, and a TypeScript SDK alternative path for JavaScript/TypeScript projects.",
        "cover_image": "/images/blog/update-v4.0.7.webp",
        "published_at": "2026-04-19",
        "read_time": "6 min read",
        "category": "Release Notes",
        "is_featured": False,
        "is_pinned": False,
        "key_points": [
            "Range: 4.0.6 -> 4.0.8",
            "Version move: 4.0.6 -> 4.0.8",
            "Scope from baseline: 9 files changed, 116 insertions, 23 deletions",
        ],
        "sections": [
            {
                "heading": "Release Summary",
                "body": "This release finalizes the next patch step after 4.0.6 by aligning project version defaults to 4.0.8 and keeping maintenance-mode behavior and endpoint messaging consistent for production users.",
                "bullets": [
                    "Project version defaults now target 4.0.8 in runtime and SDK package metadata.",
                    "Landing and availability defaults are set for normal operation while preserving fallback endpoint guidance.",
                    "Release messaging keeps the same operational safety model introduced in 4.0.6.",
                ],
            },
            {
                "heading": "Maintenance and Availability Hardening",
                "body": "The maintenance gate introduced in 4.0.6 remains the foundation for traffic control and endpoint safety when the primary service is limited.",
                "bullets": [
                    "503 responses now consistently include alternative endpoint details for API consumers.",
                    "Limited-mode web access continues to preserve tutorial/blog routes and blog assets.",
                    "The root landing page still acts as the canonical status and fallback handoff surface.",
                ],
            },
            {
                "heading": "SDK Track Updates",
                "body": "The official Python SDK remains the primary documented path, and this release now explicitly points TypeScript users to a maintained alternative package.",
                "bullets": [
                    "Python SDK remains available through OpenMLBB with endpoint coverage aligned to API routers.",
                    "TypeScript users now have a documented alternative: npm install mlbb-sdk.",
                    "SDK onboarding text in docs and web UI now clarifies Python-first plus TypeScript-alternative usage.",
                ],
            },
            {
                "heading": "Configuration and Donation Defaults",
                "body": "Configuration defaults were refreshed to match current operational expectations and support messaging.",
                "bullets": [
                    "Availability defaults target active service mode for regular traffic conditions.",
                    "Support message baseline now reflects donation minimum guidance from $5.",
                    "Date/version metadata in config has been moved forward for the 4.0.8 release line.",
                ],
            },
            {
                "heading": "Upgrade Guidance",
                "body": "No major API route break is introduced in this patch. Existing clients can upgrade with minimal friction.",
                "bullets": [
                    "If you use OpenMLBB, update to the 4.0.8 package version and re-validate your environment defaults.",
                    "If your project uses TypeScript, evaluate mlbb-sdk as an alternative client integration path.",
                    "Keep fallback endpoint handling in your client for limited-mode or high-traffic windows.",
                ],
            },
        ],
    },
    {
        "title": "Rone Arena Web v4.0.4 Release Notes (3.2.3 -> 4.0.4)",
        "slug": "mlbb-api-web-v4-0-4-release-notes-3-2-3-4-0-4",
        "excerpt": "Version 4.0.4 is now released from 3.2.3, introducing the OpenMLBB SDK track, full web documentation coverage, and a refined release workflow aligned to manual config versioning.",
        "cover_image": "/images/blog/update-v4.0.4.webp",
        "published_at": "2026-04-11",
        "read_time": "7 min read",
        "category": "Release Notes",
        "is_featured": False,
        "is_pinned": False,
        "key_points": [
            "Version move: 3.2.3 -> 4.0.4",
            "OpenMLBB SDK and web docs now fully aligned with API groups",
            "Release automation now reads manual version from app/core/config.py",
        ],
        "sections": [
            {
                "heading": "Release Summary",
                "body": "This release marks the transition from 3.2.3 to 4.0.4 and focuses on making the project easier to consume as both a web API and a Python package.",
                "bullets": [
                    "OpenMLBB SDK documentation is now available directly in the web interface.",
                    "Navigation and landing page messaging were improved for Python users.",
                    "Release flow remains automated while version control is now manual from config.",
                ],
            },
            {
                "heading": "OpenMLBB Documentation Expansion",
                "body": "The OpenMLBB documentation was expanded from a single endpoint page to structured coverage for all SDK groups.",
                "bullets": [
                    "Academy, MLBB, User, and Addon clients are documented with endpoint-level examples.",
                    "Endpoint cards now include concise Python examples and request requirement tables.",
                    "Open-only endpoint navigation and sidebar grouping improve discoverability.",
                ],
            },
            {
                "heading": "User Experience Improvements",
                "body": "This release improves clarity for onboarding users who start from the website home page.",
                "bullets": [
                    "Landing page now prominently highlights the install command: pip install OpenMLBB.",
                    "OpenMLBB endpoint descriptions now use a proper collapsed/expanded behavior for long text.",
                    "Navbar paths are aligned with the latest OpenMLBB documentation flow.",
                ],
            },
            {
                "heading": "Versioning and Publishing Flow",
                "body": "The release process is now explicitly tied to manually managed project version configuration.",
                "bullets": [
                    "Version source for release and PyPI publish is PROJECT_VERSION in app/core/config.py.",
                    "GitHub release creation and PyPI publishing stay automated in workflow execution.",
                    "Tag naming remains in 4.x.x format without a v prefix.",
                ],
            },
            {
                "heading": "Migration Notes",
                "body": "Existing API consumers can keep current integrations while adopting the SDK and docs improvements gradually.",
                "bullets": [
                    "If you publish a new release, update PROJECT_VERSION in config first.",
                    "Use the /openmlbb docs route for endpoint-by-endpoint SDK mapping.",
                    "Validate client examples against the updated docs for best onboarding experience.",
                ],
            },
        ],
    },
    {
        "title": "Rone Arena Web v3.2.3 Changelog (3.2.2 -> 3.2.3)",
        "slug": "mlbb-api-web-v3-2-3-changelog-3-2-2-3-2-3",
        "excerpt": "Clear release notes for the 3.2.2 to 3.2.3 update, covering API docs, versioning, dependency refresh, UI polish, and documentation improvements.",
        "cover_image": "/images/blog/update-v3.2.3.webp",
        "published_at": "2026-04-10",
        "read_time": "8 min read",
        "category": "Release Notes",
        "is_featured": False,
        "is_pinned": False,
        "key_points": [
            "Range: a89c7c5b667b88c80f49fa330c03bc22291a8bbe -> cf535dd87394f04def39e6e3ff4557791ec54bec",
            "Scope: 8 files changed, 138 insertions, 118 deletions",
            "Version move: v3.2.2 to v3.2.3",
        ],
        "sections": [
            {
                "heading": "Release Scope",
                "body": "This update tracks all changes from commit a89c7c5b667b88c80f49fa330c03bc22291a8bbe to the cf535dd87394f04def39e6e3ff4557791ec54bec in this project branch and prepares the project for the v3.2.3 release line.",
                "bullets": [
                    "Core version upgrade from 3.2.2 to 3.2.3 in project and runtime config.",
                    "Balanced scope with both implementation cleanup and documentation quality improvements.",
                    "Includes merged updates from main plus branch-specific release notes polish.",
                ],
            },
            {
                "heading": "Versioning and Dependency Updates",
                "body": "Release metadata and cryptography dependency were updated to keep runtime configuration and lock state aligned with the new version.",
                "bullets": [
                    "app/core/config.py: default API version changed to 3.2.3.",
                    "app/core/config.py: availability date updated to April 10, 2026.",
                    "pyproject.toml: project version moved to 3.2.3.",
                    "pyproject.toml and uv.lock: cryptography bumped to 46.0.7.",
                ],
            },
            {
                "heading": "MLBB Router Improvements",
                "body": "The hero rank payload flow was refactored for readability and easier maintenance while preserving endpoint behavior.",
                "bullets": [
                    "Removed nested payload builder function and inlined payload composition in hero_rank.",
                    "Kept ranking maps explicit with cleaner url_map and sort mapping definitions.",
                    "Added clearer query parameter documentation for days in related MLBB endpoint docs.",
                    "Updated docs note around days defaults and accepted values: 1, 3, 7, 15, 30.",
                ],
            },
            {
                "heading": "Web UI and Styling Updates",
                "body": "The web interface received visual consistency upgrades focused on discoverability and cross-browser polish.",
                "bullets": [
                    "Global scrollbar styling standardized across Firefox and WebKit engines with thin scrollbars and 10px size.",
                    "Footer now includes a BSD-3-Clause license badge for quick legal visibility.",
                    "License badge icon usage in documentation and UI aligned to BSD branding.",
                ],
            },
            {
                "heading": "Documentation and Developer Experience",
                "body": "README improvements make project entry points and deployment flow easier to scan for new and returning contributors.",
                "bullets": [
                    "Documentation links converted into a clearer Title / Link / Description table.",
                    "Deployment guidance for FastAPI Cloud added in the run section.",
                    "Website home link formatting and docs structure refined for readability.",
                ],
            },
            {
                "heading": "Legal and Attribution Refresh",
                "body": "License text and attribution were updated to better reflect current ownership and stewardship.",
                "bullets": [
                    "LICENSE copyright line updated to 2024-2026.",
                    "Attribution now references ridwaanhall / RoneAI in the core legal header.",
                ],
            },
            {
                "heading": "Upgrade Guidance for Users",
                "body": "No major endpoint-path break was introduced in this release, but users should still sync docs and dependency state to avoid drift.",
                "bullets": [
                    "Regenerate local lock/dependency state when upgrading to v3.2.3.",
                    "Review MLBB endpoint query docs if your client hardcodes days defaults.",
                    "Use updated docs table and deployment section as the source of truth for project onboarding.",
                ],
            },
        ],
    },
    {
        "title": "Rone Arena Web v3.2.2 Changelog (v3.2.1 -> v3.2.2)",
        "slug": "mlbb-api-web-v3-2-2-changelog-v3-2-1-v3-2-2",
        "excerpt": "Detailed release notes covering API additions, UI redesign, docs updates, and testing changes from commit 3.2.1 to 3.2.2.",
        "cover_image": "/images/blog/landing-page-v3.2.2.webp",
        "published_at": "2026-04-05",
        "read_time": "9 min read",
        "category": "Release Notes",
        "is_featured": True,
        "is_pinned": False,
        "key_points": [
            "Range: 3.2.1 -> 3.2.2",
            "Scope: 21 files changed, 1305 insertions, 338 deletions",
            "Version move: v3.2.1 to v3.2.2",
        ],
        "sections": [
            {
                "heading": "Release Scope and Baseline",
                "body": "This release stream starts at v3.2.1 and includes all commits up to main.",
                "bullets": [
                    "Version bump and API metadata refresh to v3.2.2.",
                    "Significant expansion of web UX and endpoint interaction quality.",
                    "Changelog includes both committed work and present workspace edits.",
                ],
            },
            {
                "heading": "API and Schema Enhancements",
                "body": "User domain capabilities were expanded and documentation accuracy was improved across multiple endpoint groups.",
                "bullets": [
                    "New user endpoint for matches filtered by hero, with dedicated schema examples and response model coverage.",
                    "Pagination guidance clarified around pageInfo.nextCursor behavior for user routes.",
                    "Hero identifier input docs normalized to accept numeric IDs and normalized hero names.",
                    "Router-level docs cleanup in academy, mlbb, addon, and user modules.",
                ],
            },
            {
                "heading": "Web App UX Redesign",
                "body": "The interactive web workspace received a major usability pass focused on clarity, response readability, and authentication flow.",
                "bullets": [
                    "New sign-in modal flow with Send VC + Login handling and JWT copy action.",
                    "Navbar/account panel improvements with richer signed-in state details.",
                    "Readable response renderer hardened with safe inline markup sanitation.",
                    "Dual readable response table modes: key-value and key-as-header.",
                    "Landing page and metadata refinements for clearer entry points and page titles.",
                    "Donation interaction replaced with themed modal workflow.",
                ],
            },
            {
                "heading": "Blog and Tutorial Foundation",
                "body": "A content system was introduced to help new users onboard through guided walkthroughs and release communication.",
                "bullets": [
                    "New /blog index and /blog/{slug} detail pages with SEO-focused metadata.",
                    "Tutorial post structure added with step-by-step sections and image slots.",
                    "Static image serving mounted at /images for blog/tutorial assets.",
                    "Tutorial entry linked from primary navbar for discoverability.",
                ],
            },
            {
                "heading": "Docs, Versioning, and Quality",
                "body": "Project documentation and test coverage were aligned to ensure behavioral consistency and safer iteration speed.",
                "bullets": [
                    "README refreshed to reflect modern web flow, auth usage, and tutorial availability.",
                    "API version references synchronized in templates and config to v3.2.2.",
                    "Web interface tests expanded for navbar/auth, blog pages, and response rendering helpers.",
                    "Current regression status before this post update: previously validated at 59 passing tests.",
                ],
            },
            {
                "heading": "Migration Notes for Integrators",
                "body": "No breaking URL path changes were introduced for existing API endpoints, but consumers should review behavior updates around user auth and documentation semantics.",
                "bullets": [
                    "Use JWT sign-in before calling protected user endpoints in web or docs workflows.",
                    "If your client consumed old last_cursor wording, align with pageInfo.nextCursor semantics.",
                    "If your client accepted free-form hero naming, follow normalized hero_identifier examples for best results.",
                ],
            },
        ],
    },
    {
        "title": "How to Use the Rone Arena API Web Project",
        "slug": "how-to-use-mlbb-public-data-api-web-project",
        "excerpt": "Complete beginner tutorial to sign in, run endpoint requests, use snippets, read responses, and authorize API docs.",
        "cover_image": "/images/blog/landing-page-v3.2.2.webp",
        "published_at": "2026-04-04",
        "read_time": "8 min read",
        "category": "Tutorial",
        "is_featured": True,
        "is_pinned": True,
        "key_points": [
            "User endpoints require sign-in first",
            "Covers both web workspace and Swagger authorization flow",
            "Includes response reading and snippet export tips",
        ],
        "sections": [
            {
                "heading": "Step 1: Open the Website",
                "body": "Visit https://arena.rone.dev. On the home page you will see two options: Open Demo Website and Open API Docs. Start with Open Demo Website if you want the guided interactive flow.",
                "image": "/images/blog/landing-page-v3.2.2.webp",
                "image_note": "Landing page with clear entry points to web playground and API docs.",
            },
            {
                "heading": "Step 2: Sign In First (Mandatory for User Endpoints)",
                "body": "Click Sign In in the navbar, then fill Role ID and Zone ID. Click Send VC. A verification code is sent to in-game mail and expires in 5 minutes.",
                "bullets": [
                    "Without sign-in, user endpoints can fail or return unauthorized responses.",
                    "This applies to both web endpoint execution and API docs authorization.",
                ],
                "image": "/images/blog/tutorial-step-2-signin-send-vc.webp",
                "image_note": "Sign-in modal with Role ID, Zone ID, and Send VC button.",
                "callout": "Important: User endpoint routes are designed for authenticated usage. Always complete login and keep JWT available.",
            },
            {
                "heading": "Step 3: Login with VC",
                "body": "In the same popup, enter VC and click Sign In. On success, navbar shows your avatar, username, and country. Open account panel to view roleId (zoneId) and copy JWT.",
                "image": "/images/blog/tutorial-step-3-login-vc.webp",
                "image_note": "Sign-in form with VC input and post-login navbar state showing user details.",
            },
            {
                "heading": "Step 4: Execute Endpoint Requests",
                "body": "Choose a group and endpoint. For example, the hero detail endpoint. Fill required parameters like hero_identifier (numeric ID or normalized name), plus optional size/index/lang.",
                "image": "/images/blog/tutorial-step-4-execute-endpoint.webp",
                "image_note": "Endpoint execution interface with parameter inputs.",
            },
            {
                "heading": "Step 5: Read Responses and Export Snippets",
                "body": "After execution, use snippet tabs (curl, python, javascript, go, node, php, java, csharp) and copy actions. Inspect Readable Response with the view-mode switch, then verify raw JSON if needed.",
                "bullets": [
                    "Key-Value mode is best for object inspection.",
                    "Key As Header mode is best for compact table-style scanning.",
                ],
                "image": "/images/blog/tutorial-step-5-response-views.webp",
                "image_note": "Response viewing options with different display modes.",
            },
            {
                "heading": "Step 6: Optionally Use API Docs",
                "body": "If you prefer Swagger UI, open API Docs from home. For user endpoints, authorize with Bearer token using JWT copied from navbar.",
                "image": "/images/blog/tutorial-step-6-api-docs-auth.webp",
                "image_note": "API docs authorization with Bearer token.",
            },
            {
                "heading": "Step 7: Paste JWT for API Docs Authorization",
                "body": "In the API docs, click Authorize. Paste JWT in the Bearer token field. After successful auth, you can execute user endpoints directly from the docs interface.",
                "image": "/images/blog/tutorial-step-7-paste-jwt-api-docs.webp",
                "image_note": "API docs with JWT pasted in Bearer token field for authorization.",
            }
        ],
    },
]


def _slugify_title(title: str) -> str:
    return "-".join(filter(None, "".join(ch.lower() if ch.isalnum() else " " for ch in title).split()))


for post in _BLOG_POSTS:
    # Slugs are pinned per post so rebranded titles never change a published URL.
    # Posts without an explicit slug fall back to deriving one from the title.
    title = str(post.get("title") or "")
    post.setdefault("slug", _slugify_title(title))


def _get_blog_post_or_404(slug: str) -> dict[str, object]:
    normalized = slug.strip().lower()
    for post in _BLOG_POSTS:
        if str(post.get("slug") or "") == normalized:
            return post
    raise HTTPException(status_code=404, detail="Blog post not found")


@router.get(path="/blog", include_in_schema=False, response_class=HTMLResponse, name="web.blog.list")
def blog_list_page(request: Request) -> HTMLResponse:
    ordered_posts = sorted(
        _BLOG_POSTS,
        key=lambda post: str(post.get("published_at") or ""),
        reverse=True,
    )
    featured_posts = [post for post in ordered_posts if bool(post.get("is_featured"))]
    pinned_posts = [post for post in ordered_posts if bool(post.get("is_pinned"))]

    context = _shared_context(request)
    context.update(
        {
            "title": "Tutorial & Blog / Rone Arena API Web",
            "web_title": "Tutorial & Blog",
            "subtitle": "Guides, release notes, and practical walkthroughs for the Rone Arena API & Web.",
            "seo_description": "Read Rone Arena API tutorials and changelogs: sign-in flow, endpoint execution, snippets, response rendering, and release updates.",
            "seo_keywords": "rone arena api tutorial, changelog, mobile legends data api guide, swagger authorization",
            "blog_posts": ordered_posts,
            "featured_posts": featured_posts,
            "pinned_posts": pinned_posts,
        }
    )
    return templates.TemplateResponse(request, "blog/list_page.html", context)


@router.get(path="/blog/{slug}", include_in_schema=False, response_class=HTMLResponse, name="web.blog.detail")
def blog_detail_page(request: Request, slug: str) -> HTMLResponse:
    post = _get_blog_post_or_404(slug)
    context = _shared_context(request)
    context.update(
        {
            "title": f"{post['title']} / Rone Arena API Web",
            "web_title": str(post["title"]),
            "subtitle": str(post["excerpt"]),
            "seo_description": str(post["excerpt"]),
            "seo_keywords": "rone arena tutorial, changelog, endpoint guide, jwt login tutorial",
            "blog_post": post,
        }
    )
    return templates.TemplateResponse(request, "blog/detail_page.html", context)
