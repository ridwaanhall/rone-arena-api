# LLM Context: Rone Arena API

## Project Purpose
- This repository provides an unofficial, community-maintained FastAPI service for Mobile Legends: Bang Bang game data. The brand is "Rone Arena"; the game name is only ever used descriptively.
- API surface includes four main groups: `user`, `heroes`, `academy`, and `addon`.
- It also includes a `/web` demo interface that mirrors API operations.

## High-Level Structure
- API app entrypoint: `app/main.py`
- API routers: `app/api/routers/`
  - `user.py`
  - `heroes.py`
  - `academy.py`
  - `addon.py`
  - `root.py`
- Schemas: `app/schemas/`
- Services/upstream requests: `app/services/`
- Shared utilities/enums/config: `app/core/`, `app/utils/`
- Web interface:
  - Router: `app/web/routers/root.py`
  - OpenAPI catalog parser: `app/web/openapi_catalog.py`
  - Templates: `app/web/templates/`
- Tests: `tests/`

## Implementation Conventions
- Keep API response models explicit with `response_model` where applicable.
- Query defaults and enum behavior must remain consistent with docs.
- If an endpoint does not require body input, do not render a request-body editor in web UI.
- Preserve endpoint listing order from OpenAPI/router declaration order (no alphabetical reshuffle in web catalog).
- Prefer non-breaking changes; avoid modifying endpoint contracts unless requested.

## Web Interface Behavior
- Base web route: `/web`
- Group routes:
  - `/web/user`
  - `/web/heroes`
  - `/web/academy`
  - `/web/addon`
- Detail route pattern: `/web/{group}/{endpoint_path}`
- UI design direction:
  - Black background
  - Border-defined cards (avoid filled bright panels)
  - Good mobile support and overflow safety
  - Custom scrollbars styled consistently for both axes

## Auth and Caching Rules
- User login (`/api/user/auth/login`) stores JWT in browser cache for 1 day.
- User info (`/api/user/info`) cache should use the exact JWT expiry timestamp (do not create a separate expiry timeline).
- Navbar can display cached user profile snippets (e.g., avatar and name) when available.

## Readable Response UX Rules
- Provide a readable response view for all endpoint cards.
- Use structured table-like rendering for objects and arrays.
- Show image values as image previews when value is an image URL.
- For image URLs, avoid duplicating the raw URL text in the readable section.
- Also provide raw JSON and generated cURL output for each request.

## Config and Environment
- Environment loading uses `python-dotenv` in `app/core/config.py`.
- Do not reintroduce `python-decouple` unless explicitly requested.

## Testing and Validation
- Run full test suite after changes:
  - `uv run pytest -q`
- Keep web behavior covered by `tests/test_web_interface.py`.
- When updating UI templates/scripts, ensure tests still validate key features (route coverage, auth cache hooks, response panels).

## Safe Update Checklist
1. Confirm endpoint metadata still loads from OpenAPI.
2. Preserve router order in web listing.
3. Validate no global horizontal page overflow appears on long responses.
4. Verify footer remains at page bottom on short-content screens.
5. Verify mobile viewport behavior at narrow widths.
6. Run tests and confirm all pass.
