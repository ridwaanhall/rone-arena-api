# Rone Arena API & Web

**Rone Arena API & Web** is a REST API and web interface for **Mobile Legends: Bang Bang** game data. It is an unofficial, community-maintained project with no affiliation to or endorsement by Moonton; the game name is used descriptively only, and the brand must never incorporate the "MLBB" or "Mobile Legends" marks.

Web UI conventions (design system, design language, JS layout) live in `src/app/web/CLAUDE.md`.

## Configuration

- `IS_MAINTENANCE`: set to `true` to restrict the API and show the maintenance page on `/`.
- `IS_HIGH_TRAFFIC`: set to `true` to restrict the API and point callers at the high-volume host.
  Both default to `false` (fully available) when unset; maintenance wins when both are true, and
  `IS_AVAILABLE` in `config.py` is derived from them, not read from the environment.
- Settings are read from `os.environ` (plus `.env` locally), and on Cloudflare Workers from the
  Worker's `env` binding (`from workers import env`), since `os.environ` is empty there.
- **Version**: `PROJECT_VERSION` is hardcoded in `src/app/core/config.py` (not read from the
  environment). Bump it there and in `pyproject.toml` together for each release.
- **API URL**: `API_URL` in `config.py` is derived, not read from the environment:
  `http://127.0.0.1:8000/api/` when `DEBUG=True`, otherwise `{BASE_URL}api/`, so a deployment
  automatically calls its own host and the playground avoids CORS errors locally. There is no
  request-volume host switch.

## Layout & Deploy

- App code lives in `src/app` (installable package, `[tool.fastapi] entrypoint = "app.main:app"`);
  web assets (CSS, JS, blog images) live in `public/`. Run locally with
  `uv run uvicorn app.main:app --app-dir src --reload` or `uv run fastapi dev`.
- **Production is a Cloudflare Python Worker** (`rone-arena-api`, custom domain `arena.rone.dev`):
  `wrangler.jsonc` points at `src/worker.py`, which wraps the FastAPI app with
  `workers.asgi.entrypoint`. `public/` is served as Workers Static Assets before the app runs.
- **Workers Builds** deploys on every push to `main` (`uv run pywrangler deploy`); other branches
  upload preview versions. pywrangler vendors `[project].dependencies` for Pyodide into
  `python_modules/`, so anything the app imports must be pure Python or Pyodide-built; keep
  server/CLI extras behind `sys_platform != 'emscripten'`.
- Non-secret vars live in `wrangler.jsonc` (`vars`); the three secrets (`SECRET_KEY`,
  `RONE_DEV_ACCESS_KEY`, `RONE_DEV_ACCESS_KEY_V2`) are set on the Worker and listed under
  `secrets.required`, so a deploy fails loudly if one is missing.
- Worker constraints: top-level imports run once at deploy time and are snapshotted (no
  randomness or network at import, e.g. the httpx client is created on first use); sync routes
  run inline (the runtime SDK patches anyio's threadpool); web pages are cached per isolate
  (`app/web/page_cache.py`) to stay inside the per-request CPU budget.
- FastAPI Cloud (`fastapi deploy`) still works and hosts the high-traffic fallback
  `arena-hv.fastapicloud.dev`; `.fastapicloudignore` keeps Worker build files out of it.

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
- The `Origin`/`Referer` headers pointing at `https://www.mobilelegends.com` in `src/app/core/http.py`
  are **required by the upstream service** - never rewrite them in a branding sweep.
- Upstream CDN asset URLs (`akmweb.youngjoygame.com/.../mlbb/...`) inside OpenAPI response examples
  are real upstream paths - leave them alone.
- Blog post slugs are pinned explicitly in `src/app/web/routers/blog.py` so rebranded titles never change
  a published URL. Add a `"slug"` key when adding a post whose title may later change.
