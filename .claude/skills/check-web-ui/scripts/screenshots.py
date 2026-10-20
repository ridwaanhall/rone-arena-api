"""Screenshot Rone Arena pages at every screen tier, light and dark.

Usage (with the app running locally):
    uv run --with playwright python .claude/skills/check-web-ui/scripts/screenshots.py \
        [--base http://127.0.0.1:8000] [--out screenshots] [--full] / /web/heroes ...

Writes <out>/<page>-<tier>-<theme>.png and prints any console errors or failed requests.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

# The five tiers from src/app/web/CLAUDE.md (width, height).
TIERS = {"mobile": (390, 844), "tablet": (768, 1024), "laptop": (1280, 800), "monitor": (1440, 900), "extra": (1920, 1080)}
DEFAULT_PAGES = ["/", "/web/heroes", "/showcase", "/tools/standings", "/patch-notes", "/blog"]


def chromium_path() -> str | None:
    """The preinstalled Chromium in Claude Code cloud sessions; None lets Playwright find its own."""
    path = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")) / "chromium"
    return str(path) if path.is_file() else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pages", nargs="*", default=DEFAULT_PAGES)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--out", default="screenshots")
    parser.add_argument("--full", action="store_true", help="capture the full page, not just the first screen")
    parser.add_argument("--tiers", default=",".join(TIERS), help="comma-separated subset of tiers")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium_path())
        for tier in args.tiers.split(","):
            width, height = TIERS[tier]
            for theme in ("light", "dark"):
                context = browser.new_context(viewport={"width": width, "height": height}, color_scheme=theme)
                page = context.new_page()
                problems: list[str] = []
                page.on("pageerror", lambda error: problems.append(f"page error: {error}"))
                page.on("console", lambda msg: problems.append(f"console {msg.type}: {msg.text}") if msg.type == "error" else None)
                page.on("requestfailed", lambda req: problems.append(f"failed: {req.url}"))
                for path in args.pages:
                    page.goto(args.base.rstrip("/") + path, wait_until="networkidle")
                    name = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-") or "home"
                    target = out / f"{name}-{tier}-{theme}.png"
                    page.screenshot(path=str(target), full_page=args.full)
                    print(target)
                for problem in problems:
                    print(f"  ! [{tier}/{theme}] {problem}")
                context.close()
        browser.close()


if __name__ == "__main__":
    main()
