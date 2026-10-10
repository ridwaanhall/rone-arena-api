---
name: bump-version
description: Bump the Rone Arena project version everywhere it lives (config.py, pyproject.toml, uv.lock). Use when releasing, or when the user says "bump/update the project version".
---

# Bump the project version

The version is hardcoded in two places that must always match, plus the lockfile:

1. `PROJECT_VERSION` in `src/app/core/config.py`
2. `version` under `[project]` in `pyproject.toml`
3. `uv.lock` (the `rone-arena-api` entry), refreshed with `uv lock`

## Steps

1. Read the current version from `pyproject.toml`.
2. Pick the new version (semver) unless the user gave one:
   - patch: fixes only
   - minor: new endpoints, groups or features, backwards compatible
   - major: breaking API changes
3. Edit both files above to the same new value.
4. Run `uv lock` so `uv.lock` follows.
5. Run `uv run pytest tests -q` and confirm it passes.
6. Verify no stale version is left: grep for the old version in `pyproject.toml`,
   `src/app/core/config.py` and `uv.lock`. Do not touch blog posts or tests that
   mention older versions in their text; those describe past releases.
7. Commit as `🔖release: Bump version to X.Y.Z`. Do not push unless asked.
