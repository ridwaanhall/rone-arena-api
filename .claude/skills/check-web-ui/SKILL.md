---
name: check-web-ui
description: Screenshot Rone Arena pages in a real browser at all five screen tiers, light and dark, and review them against the design rules. Use after changing templates, arena.css or site JavaScript, or when asked for screenshots.
argument-hint: "[page paths, e.g. / /web/heroes]"
allowed-tools: Bash(uv run *), Bash(curl *), Read
---

# Check a web UI change

Design rules live in `src/app/web/CLAUDE.md` (field-manual language, tokens, tiers, banned AI-template tells).
This skill is the routine for proving a change against them.

## 1. Start the app

```bash
SECRET_KEY=dev DEBUG=false uv run uvicorn app.main:app --app-dir src --port 8000
```

Run it in the background and wait until `curl -s -o /dev/null http://127.0.0.1:8000/favicon.ico` answers.
`DEBUG=false` renders what production renders (base URL switch, both API hosts, share tags); live tables
then call the public API, which is fine for a few page loads. Use `DEBUG=true` to keep calls local.
Do not fire many upstream calls in parallel: the upstream WAF blocks bursts for minutes.

## 2. Screenshot

```bash
uv run --with playwright python .claude/skills/check-web-ui/scripts/screenshots.py --out <scratch dir> $ARGUMENTS
```

Without page arguments it covers `/`, `/web/heroes`, `/showcase`, `/tools/standings`, `/patch-notes`, `/blog`.
Every tier (mobile 390, tablet 768, laptop 1280, monitor 1440, extra 1920) runs in light and dark.
Narrow it with `--tiers mobile,monitor` while iterating, add `--full` for whole pages.
The script prints console errors and failed requests per tier; treat any as a bug to explain.
Do not run `playwright install`: cloud sessions have Chromium at `/opt/pw-browsers`, and the script uses it.

## 3. Review

Read the screenshots and check:

- Nothing overflows sideways on mobile; wrapped rows (base URL switch, tabs, tables) still read in order.
- Dark mode: text on `--mark` (chartreuse) stays `--mark-ink`; no `--ink` text or borders on the green.
- No new AI-template tells (gradients, glows, badges above headlines, card grids, em dashes).
- Interactive bits work: click through switches and tabs with Playwright when the change touches them.

## 4. Finish

Run `uv run pytest tests -q` (`test_ui_avoids_generic_ai_template_tells` guards part of the rules), stop the
server, and show the user the key screenshots rather than describing them.
