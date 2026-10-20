---
name: accept-showcase
description: Review and accept a community project submitted to the Rone Arena showcase (/showcase). Use when the user shares a "[Showcase]" issue, pastes a showcase entry dict, or asks to add, update or remove a showcase project.
argument-hint: "[issue number or URL]"
---

# Accept a showcase submission

Submissions arrive through the issue form `.github/ISSUE_TEMPLATE/showcase.yml` (label `showcase`) as one
Python dict in the `SHOWCASE` format. The page's LLM prompt (`llm_prompt` in `src/app/web/showcase.py`)
writes that dict for submitters, so it should paste in as-is.

## Steps

1. Read the issue (`$ARGUMENTS`) and copy the dict from the "Showcase entry" field.
2. Review it before pasting:
   - `name` must not use "MLBB", "Mobile Legends" or "Bang Bang" as its brand (see Branding in `CLAUDE.md`).
     Naming the game descriptively in `about` is fine.
   - `url` opens now and the site really calls this API.
   - `contributors` are `(name, link)` pairs; links go to the person (site, GitHub, X, Instagram).
   - `features` are `(feature, [(method, path), ...])` with paths exactly as the OpenAPI schema lists them,
     parameters in braces (`/api/heroes/{hero_identifier}/stats`, not `/api/heroes/1/stats`).
   - No em dashes in any text (the UI tests ban them).
3. Paste the dict into `SHOWCASE` in `src/app/web/showcase.py`. Order is display order.
4. Run the showcase tests:

   ```bash
   uv run pytest tests/test_web_interface.py -q -k showcase
   ```

   `test_showcase_links_sister_sites_to_real_endpoints` fails if a listed endpoint does not exist;
   `test_showcase_entry_format_pastes_back_into_showcase` checks `format_entry` round-trips the format.
5. Open `/showcase` locally and check the card. `llms.txt` and `/showcase.md` update themselves.
6. Commit (`✨feat(showcase): Add <name>`), open a PR that closes the issue, and thank the submitter.

If something is wrong (a renamed endpoint, a brand problem), comment on the issue with the exact fix
instead of editing their wording silently.
