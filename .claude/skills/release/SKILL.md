---
name: release
description: Ship a Rone Arena release end to end (version, patch notes, PR, the automatic tag and GitHub Release after merge). Use for "release", "ship", "cut X.Y.Z", a missing tag or release, or backfilling one.
argument-hint: "[version, e.g. 1.4.0]"
---

# Release Rone Arena

Tags and GitHub Releases are created by CI. Never create a tag or release by hand for a new version.

## 1. Prepare on a branch

1. Branch off `main` (`release/X.Y.Z`, or ride on the feature branch being released).
2. Pick the version unless one was given (`$ARGUMENTS`): patch for fixes only, minor for new features or
   endpoints, major for breaking API changes. One PR ships one version: if the branch already bumped to an
   unreleased version, update that entry instead of bumping again.
3. Run the `bump-version` skill (`pyproject.toml`, `src/app/core/config.py`, `uv.lock`).
4. Run the `patch-notes` skill (`src/app/web/patch_notes.py`; the newest entry must equal `PROJECT_VERSION`).
5. If product facts changed (base URL, auth, errors, pages), run the `llms-txt` skill.
6. Check: `uv run pytest tests -q`.

## 2. Open the PR

Commit with the repo's gitmoji style (`🔖release: Bump version to X.Y.Z`), push, open a PR to `main`.
Workers Builds uploads a preview version for the branch; check it starts before merging.

## 3. After merge (automatic)

- Workers Builds deploys `main` to `arena.rone.dev` (`uv run pywrangler deploy`).
- `.github/workflows/release-tag.yml` runs on pushes to `main` that change `pyproject.toml`.
  `.github/scripts/release_tag.py` tags the merge commit `X.Y.Z` (no `v`) only when the version went **up**
  compared with the commit before the push and no tag of that name exists, then publishes a GitHub Release
  with generated notes (merged PRs since the previous release), marked latest.
- Same or lower version, an existing tag, or any other branch: nothing happens. The old `4.x` tags predate
  the rename and are never compared.
- Optional: edit the release on GitHub to add hand-written highlights.
- FastAPI Cloud (`arena.fastapicloud.dev`, the "Primary" host) deploys separately with `fastapi deploy`.

## Backfill a missing release

First automatic release: 1.2.3. For an older tag without a release:

```bash
gh api repos/ridwaanhall/rone-arena-api/releases/generate-notes -f tag_name=X.Y.Z --jq .body > notes.md
gh release create X.Y.Z --verify-tag --notes-file notes.md --latest=false
```

## Troubleshooting "no tag appeared"

Read the `release-tag` workflow log: it prints the decision. Usual causes: the version did not go up, the
tag already exists, or the push did not touch `pyproject.toml`.
