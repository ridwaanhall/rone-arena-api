# Rone Arena API & Web

**Rone Arena API & Web** is a REST API and web interface for **Mobile Legends: Bang Bang** game data. It is an unofficial, community-maintained project with no affiliation to or endorsement by Moonton; the game name is used descriptively only, and the brand must never incorporate the "MLBB" or "Mobile Legends" marks.

Web UI conventions (design system, design language, JS layout) live in `src/app/web/CLAUDE.md`.
Release notes for non-technical readers live in `src/app/web/patch_notes.py` (shown on `/patch-notes`). Project
skills in `.claude/skills/`: `release` (end to end), `bump-version`, `patch-notes`, `llms-txt`, `check-web-ui`
(browser screenshots at every tier), `brand-assets` (favicon, icons, share card) and `accept-showcase`.
For AI agents, `/llms.txt`, `/llms-full.txt` and a `.md` twin of every web page (`/index.md`, `/web/heroes.md`, ...)
are generated in `src/app/web/llms.py`; the `llms-txt` skill keeps them current when pages or product facts change.

## Working with the owner

- **Every finished change is released on its branch**: bump the version (`bump-version`), add patch notes
  (`patch-notes`), commit and push to the working branch (never to `main`), then **ask the owner whether to open a PR**.
  Open or merge a PR only when asked.
- An instruction such as "don't bump" or "don't merge" applies only to the task it was given for, not to later work.
- When the owner asks to merge, merge without waiting for the builds or checks to finish.

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
  Link-preview images (`og:image`, `twitter:image`: the default card and blog covers) are the exception: they go through
  `share_image_url` in `web/routers/root.py` and are served straight from the site; the same images shown on a page stay proxied.
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
- **Releases**: use the `release` skill. Tags and GitHub Releases are automatic: merging a version bump to `main`
  makes `.github/workflows/release-tag.yml` tag `X.Y.Z` (no `v`) and publish the release; never create them by hand.
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
- FastAPI Cloud hosts `arena.fastapicloud.dev` (`ALTERNATIVE_ENDPOINT_URL`, the site's "Primary" host). It is
  connected to the GitHub repo, so every push to `main` deploys it too, alongside the Worker; `fastapi deploy` is
  only for a manual deploy. `.fastapicloudignore` keeps Worker build files out of it.
- **Backup host on the server**: `src/worker.py` answers 307 to the same path and query on `ALTERNATIVE_ENDPOINT_URL`
  when the app raises or returns 500/502/504 (`app/core/fallback.py`; 503 is left alone). It cannot help when the
  Worker dies before Python runs (Cloudflare 1102 CPU/memory limits).
- **Shared edge cache**: `src/worker.py` keeps successful `GET /api/esports/...` answers in Cloudflare's Cache API
  for 300s (`EDGE_CACHE_*` in `app/core/fallback.py`), so Worker copies in one data center share one scrape instead
  of each paying the CPU of a cold parse. Hits carry `X-Rone-Edge-Cache: HIT`.
- **Browser and shared caching**: `core/cache_headers.py` (`PublicCacheHeaders`) adds `Cache-Control: public, max-age=300,
  stale-while-revalidate=60` to successful `GET` answers under `/api/heroes`, `/api/academy` and `/api/esports/`, so callers'
  browsers and CDNs reuse them. Never on `/api/user` or `/api/addon` (the IP lookup is per visitor), on requests with an
  `Authorization` or `Cookie` header, on errors, or when a route set its own `Cache-Control`.
- **Host choice and backup in the browser**: `public/static/js/api.js` (`window.ArenaApi.request`) wraps every API
  call the site's scripts make and sends it to the host picked on the base URL switch (`PUBLIC_API_HOSTS`, passed as
  `data-api-hosts`; "Primary" (FastAPI Cloud) by default, remembered in localStorage), whatever host the URL was built for. On a
  network error, 5xx, 429 or non-JSON body it retries on the other host and keeps using it for 5 minutes. It has to be
  client-side: Cloudflare error 1102 or an outage leaves no server code to forward. Under `DEBUG` there are no hosts and
  calls stay on the local server.

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
7. **Esports endpoints scrape HTML, not JSON** (rules for every league: "Adding or changing an MPL league" below): `services/esports/` parses the league sites with BeautifulSoup. Their base URLs are Fernet tokens in `EsportsSourceProvider` (`core/security.py`), so no host name appears in the repo; fixtures in `tests/fixtures/esports/` use `*.test` hosts. Parsed results are cached for 300s (`utils/ttl_cache.py`). The Indonesian schedule page is 2.4 MB (mostly pop-ups); building a BeautifulSoup tree of it used the Worker's whole CPU budget (Cloudflare error 1102, about 2s of CPU), so `indonesia.py` reads the weeks with targeted regexes and only the small standings table with BeautifulSoup. The Philippine
   match page (0.8 MB, five games in a playoff series) and its item-sequence responses hit the same 1102, so `philippines.get_match`
   reads them with regexes too (`balanced_div`/`div_block` in `common.py` slice the blocks; live markup splits attributes across lines,
   so patterns must allow `\s+` between them). Keep it that way; measure CPU with the Workers analytics (`workersInvocationsAdaptive`) rather than locally, where it looks about 5x cheaper. The Indonesian site's item images are presigned for 6h, so never cache longer. Playoffs (`/api/esports/{league}/playoffs`) come
   from the same schedule fetch as the regular season (ID: the `#playoffs` and `#standing-playoffs` blocks; PH: the first
   `#playoffs` block, since its cards are repeated lower on the page), so they cost no extra request. Undecided sides are
   `TBD` with the league's own logo, which is dropped (`logo: null`) so no league host leaks. Series length (`best_of`
   3/5/7; the lower bracket final and grand final are 7, found by round name in ID and as the last two matches in PH) drives `status`/`winner` on every match. PH games have no clock,
   so `duration_estimate` is total gold over gold per minute The Philippine item sequences are a CSRF-protected POST: the token comes from the match page and the request must carry that page's cookies explicitly (the pooled client's jar is shared across callers)

8. **Unfilled game-text placeholders**: the content source sometimes ships a text without the numbers the game fills in at
   run time (Retribution's `<Num9> kills or assists to gain <Num10> ...`, the boots' live `(Current: <#bv 25>)`).
   `core/game_text.py` (`clean_game_json`, applied in `services/source.post_source`, so every hero and academy answer)
   cuts the clause that needs a missing number and drops live counters. `skilldesc_text` keeps its placeholders: it is a
   template filled from `numdescribe`, and `skilldesc` beside it is already filled

9. **Standings formula (shared by every league)**: matches are first to 2 games; rank by match points, then net game wins,
   then head-to-head among the tied teams, else `unresolved`. `services/esports/standings.py` reproduces all four official tables
   exactly (`tests/fixtures/esports/season_snapshots.json` holds the four real seasons). Indonesia, the Philippines and
   Malaysia play a double round robin, Cambodia a single one; the simulator always starts from the league's real schedule. The `/api/esports/{league}/standings/simulate` and `/standings/calculate` tools and the
   `/tools/standings` page all call that one engine, so the page has no ranking logic of its own. Playoff cut defaults:
   bottom 3 for Indonesia, bottom 2 for the Philippines and Malaysia, bottom 4 for Cambodia, 3 for custom. Head-to-head among 3+ tied teams and the PH tie-breaks
   are assumptions (no such tie exists in the data yet)

## Adding or changing an MPL league (esports scrapers)

Four leagues today: Indonesia (`id`), the Philippines (`ph`), Malaysia (`my`) and Cambodia (`kh`). Rules for any league:

1. **Official sites only**: a league's own site, copyright Moonton. Fan sites, wikis and aggregators are out. Today no
   other country has one (Singapore's is gone, the Middle East and North Africa site only sells tickets).
2. **Never type a league host anywhere tracked**: code, tests, fixtures, docs, commit messages, PR text. A base URL
   exists only as a Fernet token in `EsportsSourceProvider` (`core/security.py`), made in a throwaway shell with
   `CryptoManager(SECRET_KEY).encrypt(url)`; add the getter and the host's SHA-256 to `HOST_DIGESTS` in
   `tests/test_esports.py`, also computed in a shell. The secrecy tests find leaks by those digests (every tracked file,
   OpenAPI, the website, llms.txt, the new answers) and, with `SECRET_KEY` set, by decrypting. Fixtures use `*.test`
   hosts and drop presigned or credentialed URLs. Images or links on the league's own domain must not reach an answer:
   Cambodia's logos are served by `/api/esports/kh/images/{name}` (`cambodia.get_image`) for that reason.
3. **CPU budget on the Worker (error 1102, about 2 s of CPU)**: check a page's size first. Above about 200 KB never
   build a BeautifulSoup tree; slice with `balanced_div`/`div_block` and read with targeted regexes (allow `\s+`
   between attributes). Parse once per fetch, cache the result 300 s (`ttl_cache(CACHE_SECONDS)`), and let one fetch
   feed several endpoints. Locally: Malaysia's 0.9 MB schedule parses in about 0.03 s, a match in about 0.005 s,
   a Cambodian week page in about 0.002 s. Confirm on the Worker with `workersInvocationsAdaptive`.
4. **Answer with the shared schemas** (`schemas/esports.py`): an undecided side is `TBD` with `logo: null`, `best_of`
   3/5/7 (`mark_finals` when the league names no rounds), `start_at` in UTC from the league's own time zone. An unknown
   match is 404 `MATCH_NOT_FOUND`, never a 500 (a 500 makes the Worker redirect to the backup host).
5. **CSRF-protected AJAX**: take the token and cookies from the page and pass the cookies explicitly (the pooled client's
   jar is shared). Malaysia's match details need neither: a plain GET of its match-detail fragment.
6. **Checklist for a new league**: token + getter (+ `all_base_urls`), `LeagueEnum`, `services/esports/<country>.py`,
   `<X>_ELIMINATED` in `common.py` + `DEFAULT_ELIMINATED`/`_season` in `simulation.py`, router endpoints and the
   simulate docs/examples, the standings page tab and `standings.js` (`LEAGUE_NAMES`, `edits`, `eliminated`),
   `llms.py`, `web/credits.py` (`ESPORTS_SOURCES`), fixtures + tests + `season_snapshots.json`, this file, patch notes.
7. **Credits name the league, never the host** (`web/credits.py`, shown in the footer, `/llms.txt` and the README).

League notes:
- **Malaysia**: one fetch of `/schedule` gives the 8 weeks and the playoff days (round names carry the series length,
  "(BO5)"), one of `/` the standings (the table marks 6 playoff and 2 eliminated rows). Match ids are the schedule's
  numeric detail ids. The match fragment's four figures per lane are labelled wrongly by the site; their real order is
  hero damage, gold, tower damage, damage taken. It prints the same emblem and talents for both players of a lane, so
  Malaysian players have no emblem or talents.
  The match fragment comes in two versions at random (about 2 in 5 fetches get the bad one, Oct 2026): the bad one
  repeats team 1's KDA for team 2 (`kda-content me-2`), and its real numbers are nowhere in it. `get_match` checks
  that each side's player kills add up to its score and fetches again, up to `_MATCH_TRIES` (6); a game still wrong is
  left out, as is a game published without heroes (empty `alt`). A long team name is cut with dots in the fragment ("iG ........"); `_team_name` drops them.
- **Cambodia**: single round robin, 10 teams, 5 weeks; one page per week (`?stage=regular&week=N`), streamed React
  markup (day headings hold `<template id="P:x">` placeholders filled by `<div hidden id="S:x">` cards later in the
  page). Standings from `/teams`; playoffs from `?stage=playoffs` (empty until the bracket is published); seeds are the
  top 6 (`KH_ELIMINATED = 4`, the format of past seasons). Today's matches show LIVE instead of a time. No match details.

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
