# Rone Arena API & Web

**Rone Arena API & Web** is a REST API and web interface for **Mobile Legends: Bang Bang** game data. It is an unofficial, community-maintained project with no affiliation to or endorsement by Moonton; the game name is used descriptively only, and the brand must never incorporate the "MLBB" or "Mobile Legends" marks.

Web UI conventions (design system, design language, JS layout) live in `src/app/web/CLAUDE.md`.
Release notes for non-technical readers live in `src/app/web/patch_notes.py` (shown on `/patch-notes`); the
`patch-notes` skill writes them and `bump-version` bumps the version.
For AI agents, `/llms.txt`, `/llms-full.txt` and a `.md` twin of every web page (`/index.md`, `/web/heroes.md`, ...)
are generated in `src/app/web/llms.py`; the `llms-txt` skill keeps them current when pages or product facts change.

## Configuration

- `IS_MAINTENANCE`: set to `true` to restrict the API and show the maintenance page on `/`.
- `IS_HIGH_TRAFFIC`: set to `true` to restrict the API and point callers at the high-volume host.
  Both default to `false` (fully available) when unset; maintenance wins when both are true, and
  `IS_AVAILABLE` in `config.py` is derived from them, not read from the environment.
- Settings are read from `os.environ` (plus `.env` locally), and on Cloudflare Workers from the
  Worker's `env` binding (`from workers import env`), since `os.environ` is empty there.
- `USE_WSRV` (default `true`): every image URL, SVG included, goes through the wsrv.nl proxy. `core/images.py` rewrites
  upstream JSON (`core/http.py`), the OpenAPI examples, the esports schemas and web pages (`| image` template filter).
  `.ico` is never proxied (wsrv cannot serve it), and wsrv rasterises SVGs.
- **Version**: `PROJECT_VERSION` is hardcoded in `src/app/core/config.py` (not read from the
  environment). Bump it there and in `pyproject.toml` together for each release (the `bump-version` skill does this).
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
- **Release tags**: `.github/workflows/release-tag.yml` runs only on pushes to `main` that change `pyproject.toml`.
  `.github/scripts/release_tag.py` compares the version before and after the push (not the old `4.x` tags, which
  predate the rename) and, if it went up and no tag exists, pushes an annotated tag `X.Y.Z` (no `v`). Tag only; the
  GitHub Release is still created by hand.
- **Workers Builds** deploys on every push to `main` (`uv run pywrangler deploy`); other branches
  upload preview versions. pywrangler vendors `[project].dependencies` for Pyodide into
  `python_modules/`, so anything the app imports must be pure Python or Pyodide-built; keep
  server/CLI extras behind `sys_platform != 'emscripten'`.
- Non-secret vars live in `wrangler.jsonc` (`vars`); the three secrets (`SECRET_KEY`,
  `RONE_DEV_ACCESS_KEY`, `RONE_DEV_ACCESS_KEY_V2`) are set on the Worker and listed under
  `secrets.required`, so a deploy fails loudly if one is missing.
  In code only `SECRET_KEY` is required at import; the two access keys default to empty so a pull request preview
  (which has no secrets, or only `SECRET_KEY`) still starts, and the endpoints that need one answer 503
  `NOT_CONFIGURED` via `require_access_key` in `core/config.py`.
- Worker constraints: top-level imports run once at deploy time and are snapshotted (no
  randomness or network at import, e.g. the httpx client is created on first use); sync routes
  run inline (the runtime SDK patches anyio's threadpool); web pages are cached per isolate
  (`app/web/page_cache.py`) to stay inside the per-request CPU budget.
- FastAPI Cloud (`fastapi deploy`) still works and hosts the high-traffic fallback
  `arena.fastapicloud.dev` (`ALTERNATIVE_ENDPOINT_URL`); `.fastapicloudignore` keeps Worker build files out of it.
- **Backup host in the browser**: `public/static/js/api.js` (`window.ArenaApi.request`) wraps every API call the
  site's scripts make; on a network error, 5xx, 429 or non-JSON body it retries on the backup host and keeps
  using it for 5 minutes. It has to be client-side: Cloudflare error 1102 or an outage leaves no server code to forward.
  Disabled under `DEBUG` and on the backup host itself.

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
5. **Upstream WAF answers bursts with an HTML 405**: `core/http.py` retries once, then returns 429 `UPSTREAM_RATE_LIMITED`. Don't fire many parallel upstream calls when testing; the block lasts minutes per address
6. **The upstream IP lookup is IPv4-only**: it answers an IPv6 address with `code: -1, data: ""`. `/api/addon/ip` answers IPv6 visitors from Cloudflare's `request.cf` geolocation instead (handed to the app by `src/worker.py` through a ContextVar)
7. **Esports endpoints scrape HTML, not JSON**: `services/esports/` parses the two league sites with BeautifulSoup. Their base URLs are Fernet tokens in `EsportsSourceProvider` (`core/security.py`), so no host name appears in the repo; fixtures in `tests/fixtures/esports/` use `*.test` hosts. Parsed results are cached for 300s (`utils/ttl_cache.py`). The Indonesian schedule page is 2.4 MB (mostly pop-ups); building a BeautifulSoup tree of it used the Worker's whole CPU budget (Cloudflare error 1102, about 2s of CPU), so `indonesia.py` reads the weeks with targeted regexes and only the small standings table with BeautifulSoup. Keep it that way; measure CPU with the Workers analytics (`workersInvocationsAdaptive`) rather than locally, where it looks about 5x cheaper. The Indonesian site's item images are presigned for 6h, so never cache longer. The Philippine item sequences are a CSRF-protected POST: the token comes from the match page and the request must carry that page's cookies explicitly (the pooled client's jar is shared across callers)

8. **Standings formula (shared by both leagues)**: matches are first to 2 games; rank by match points, then net game wins,
   then head-to-head among the tied teams, else `unresolved`. `services/esports/standings.py` reproduces both official tables
   exactly (`tests/fixtures/esports/season_snapshots.json` holds the two real seasons). A season has as many weeks as teams,
   every pair meets twice. The `/api/esports/{league}/standings/simulate` and `/standings/calculate` tools and the
   `/tools/standings` page all call that one engine, so the page has no ranking logic of its own. Playoff cut defaults:
   bottom 3 for Indonesia, bottom 2 for the Philippines, 3 for custom. Head-to-head among 3+ tied teams and the PH tie-breaks
   are assumptions (no such tie exists in the data yet)

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
