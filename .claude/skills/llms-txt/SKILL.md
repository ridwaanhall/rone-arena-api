---
name: llms-txt
description: Keep /llms.txt, /llms-full.txt and the .md twin of every Rone Arena web page up to date. Use when adding or renaming a web page, route, endpoint group or blog post, when the product's key facts change (auth, base URL, errors, SDK), when releasing, or when the user asks to update llms.txt or the markdown pages.
---

# Keep llms.txt and the markdown pages current

AI agents read the site through `/llms.txt` (the index, llmstxt.org format), `/llms-full.txt`
(every page in one file) and a markdown twin of each web page: the page URL plus `.md`
(`/index.md` for the home page). Each HTML page links its twin in `<head>`
(`rel="alternate" type="text/markdown"`) and points at `/llms.txt` (`rel="describedby"`).

- Builders: `src/app/web/llms.py` (one function per page type).
- Routes: `src/app/web/routers/llms.py`, included in `main.py` **before** the web router so
  `/web/{group}/{path}` does not swallow `.md` URLs.
- Tests: `tests/test_llms.py`. `test_every_sitemap_page_has_a_markdown_twin` fails when a page in
  `/sitemap.xml` has no `.md` twin; `test_every_link_in_llms_txt_resolves` fails on a dead link.

## What updates itself

Built from the same data as the HTML, so no edit is needed for:
endpoints (OpenAPI schema), blog posts (`_BLOG_POSTS`), patch notes (`PATCH_NOTES`), showcase
entries (`SHOWCASE`), the version number, and the maintenance notice.

## What needs a hand edit

1. **A new kind of web page** (a new HTML route):
   - add it to `/sitemap.xml` in `routers/blog.py` if it should be indexed;
   - write a `*_markdown()` builder in `llms.py` from the page's data (not by scraping HTML);
   - add a `/<path>.md` route in `routers/llms.py` that returns `_markdown(body, html_path)`;
   - link it from `llms_txt()` (under `## Docs`, or `## Optional` if an agent can skip it) and,
     if it is real content, append it in `llms_full_txt()`.
   - If the page is reachable during maintenance, also add the `.md` path to
     `ServiceStatusGuard._ALLOWED_PREFIXES` in `main.py`.
2. **A new endpoint group**: add it to `WEB_GROUPS`/`GROUP_META` (`openapi_catalog.py`); llms.txt
   picks it up as a new `## <Title> endpoints` section.
3. **Product facts changed** (auth flow, base URL, error codes, rate limits, image proxy, SDK
   name, what data is covered): update `SUMMARY`, `ABOUT` or `KEY_FACTS` at the top of `llms.py`.
   Re-read them against `CLAUDE.md` and the FastAPI `description` in `main.py` at each release.
4. **Blog**: the 3 newest posts sit under `## Blog`, the rest under `## Optional`. Nothing to do
   unless that split should change.

## Writing rules

- `llms.txt` order is fixed by the spec: H1 name, `> ` one-line summary, plain paragraphs (no
  headings), then `## ` sections that hold only `- [name](url): notes` lines.
- Use absolute production URLs (`absolute_url`, `markdown_path`), never the request host.
- Keep notes to one sentence. Say what the page or endpoint gives, not marketing.
- Branding rules from `CLAUDE.md` apply: the product is "Rone Arena"; name the game only to
  describe the data.

## Check

```bash
uv run pytest tests/test_llms.py -q
```

Then open `/llms.txt`, `/index.md` and one endpoint page (for example
`/web/heroes/heroes/{hero_identifier}/stats.md`) locally and read them as an agent would.
