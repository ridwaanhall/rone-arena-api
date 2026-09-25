# Rone Arena API & Web

**Rone Arena API & Web** is a REST API and web interface for **Mobile Legends: Bang Bang** game data. It is an unofficial, community-maintained project with no affiliation to or endorsement by Moonton; the game name is used descriptively only, and the brand must never incorporate the "MLBB" or "Mobile Legends" marks.

Web UI conventions (design system, design language, JS layout) live in `app/web/CLAUDE.md`.

## Configuration

- `IS_MAINTENANCE`: set to `true` to restrict the API and show the maintenance page on `/`.
- `IS_HIGH_TRAFFIC`: set to `true` to restrict the API and point callers at the high-volume host.
  Both default to a restricted service when unset; maintenance wins when both are true, and
  `IS_AVAILABLE` in `config.py` is derived from them, not read from the environment.
- **Version**: `PROJECT_VERSION` is hardcoded in `app/core/config.py` (not read from the
  environment). Bump it there and in `pyproject.toml` together for each release.
- **API URL**: `API_URL` in `config.py` is derived, not read from the environment:
  `http://127.0.0.1:8000/api/` when `DEBUG=True`, otherwise `{BASE_URL}api/`, so a deployment
  automatically calls its own host and the playground avoids CORS errors locally. There is no
  request-volume host switch.

## Testing

```bash
pytest tests/
# Also hit the real upstream and assert on returned data:
LIVE_UPSTREAM=1 pytest tests/test_live_upstream.py
```

## Notable Implementation Details

1. **Sync-Yield ContextVar Bug (Fixed)**: FastAPI sync-yield dependencies don't reset ContextVar across thread contexts; use async-yield instead
2. **Enum String Rendering**: `str(MyStrEnum.MEMBER)` returns `MyStrEnum.MEMBER`, not the value; use `.value` or normalize with property
3. **Jinja2 TemplateResponse Order**: Requires `(request, name, context)` order; using old order triggers TypeError
4. **Upstream Auth Returns HTTP 200 with Errors**: Always validate `code` field in response, not just HTTP status

## Branding & Trademark Constraints

The project was rebranded from "MLBB Public Data API" to **Rone Arena** because the MLBB /
Mobile Legends marks belong to Moonton and cannot be used as this project's brand identity.

- **Never** put `MLBB`, `Mobile Legends`, or `Bang Bang` in the product name, domain, repo name,
  package name, OpenAPI tag, or any other source-identifying position.
- Naming the game **descriptively** ("data for the game Mobile Legends: Bang Bang") is fine and
  intentional - that is nominative fair use.
- The `Origin`/`Referer` headers pointing at `https://www.mobilelegends.com` in `app/core/http.py`
  are **required by the upstream service** - never rewrite them in a branding sweep.
- Upstream CDN asset URLs (`akmweb.youngjoygame.com/.../mlbb/...`) inside OpenAPI response examples
  are real upstream paths - leave them alone.
- Blog post slugs are pinned explicitly in `app/web/routers/blog.py` so rebranded titles never change
  a published URL. Add a `"slug"` key when adding a post whose title may later change.
