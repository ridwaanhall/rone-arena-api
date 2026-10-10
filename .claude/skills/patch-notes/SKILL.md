---
name: patch-notes
description: Write the plain-language patch notes entry for a Rone Arena release (the /patch-notes page). Use when releasing, after bumping the version, or when the user asks to add or update patch notes.
---

# Write patch notes

Patch notes live in `src/app/web/patch_notes.py` (`PATCH_NOTES`, newest first) and are shown on `/patch-notes`.
`test_latest_patch_notes_match_the_project_version` fails if the newest entry is not the current `PROJECT_VERSION`.

## Steps

1. Find what changed since the last entry: `git log --oneline` from the previous release commit
   (`git log -S'"version": "X.Y.Z"' -- src/app/web/patch_notes.py` finds it), and skim the diff.
2. Add a new dict at the TOP of `PATCH_NOTES`:
   - `version`: same as `PROJECT_VERSION` (use the `bump-version` skill first if it is not bumped yet)
   - `date`: release date, `YYYY-MM-DD`
   - `summary`: one short sentence for the whole release
   - `new`, `improved`, `fixed`, `removed`: lists of short points. Leave a section out when it has no points.
3. Run `uv run pytest tests/test_web_interface.py -q -k patch_notes`, then look at `/patch-notes`.

## How to write the points

The readers are players and fans, not developers.

- One short sentence per point, about 15 words or fewer. Say what the person can now do or no longer can.
- Everyday words. Avoid: endpoint, API call, cache, schema, refactor, JSON, parameter, status code, dependency.
  Say "feature", "page", "answers come back faster", "pictures load" instead.
- Group by meaning: **new** (things you can now do), **improved** (faster, easier, better looking),
  **fixed** (something that was wrong), **removed** (gone or turned off, and what to do instead).
- Skip internal work nobody notices (tests, code cleanup, build changes).
- No em dashes (the site's tests ban them in page copy).
- Technical details belong in the blog release post, not here.
