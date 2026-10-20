"""Rebuild the Rone Arena icons and link-preview card into public/.

Usage, from the repo root (needs network for the Google Fonts files):
    uv run --with pillow --with fonttools --with playwright python .claude/skills/brand-assets/scripts/build.py \
        [--card public/images/og/rone-arena-card.png] [--only icons|card]

The mark is the capital R of Archivo Condensed Black (wdth 75, wght 900), drawn as an SVG path so the
favicon needs no font, on a --mark (#d4f53c) tile in --mark-ink (#121212).
"""
from __future__ import annotations

import argparse
import io
import os
import re
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ICONS = ROOT / "public" / "images" / "icons"
MARK, MARK_INK = "#d4f53c", "#121212"
FONT_CSS = "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75,900"


def archivo_r(scratch: Path) -> tuple:
    """Glyph set and bounds of the R from a static Archivo instance (old user agent gets a .ttf)."""
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.ttLib import TTFont

    font_path = scratch / "archivo-75-900.ttf"
    if not font_path.exists():
        css = urllib.request.urlopen(urllib.request.Request(FONT_CSS, headers={"User-Agent": "Mozilla/4.0"})).read().decode()
        url = re.search(r"url\((https://[^)]+\.ttf)\)", css)[1]
        font_path.write_bytes(urllib.request.urlopen(url).read())
    glyphs = TTFont(font_path).getGlyphSet()
    bounds = BoundsPen(glyphs)
    glyphs["R"].draw(bounds)
    return glyphs, bounds.bounds


def tile_svg(glyphs, bounds, cap_height: float, radius: int) -> str:
    """A 64x64 tile with the R centred at the given cap height."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen

    x_min, y_min, x_max, y_max = bounds
    scale = cap_height / (y_max - y_min)
    dx = (64 - (x_max - x_min) * scale) / 2 - x_min * scale
    dy = (64 + cap_height) / 2 + y_min * scale
    pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    glyphs["R"].draw(TransformPen(pen, (scale, 0, 0, -scale, dx, dy)))
    corner = f' rx="{radius}"' if radius else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64"{corner} fill="{MARK}"/>'
        f'<path fill="{MARK_INK}" d="{pen.getCommands()}"/></svg>\n'
    )


def chromium_path() -> str | None:
    path = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")) / "chromium"
    return str(path) if path.is_file() else None


def main() -> None:
    from PIL import Image
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser()
    parser.add_argument("--card", default="public/images/og/rone-arena-card.png")
    parser.add_argument("--only", choices=["icons", "card"])
    args = parser.parse_args()

    scratch = ROOT / ".brand-build"
    scratch.mkdir(exist_ok=True)
    glyphs, bounds = archivo_r(scratch)
    favicon = tile_svg(glyphs, bounds, 40, radius=10)
    square = tile_svg(glyphs, bounds, 40, radius=0)  # iOS and launchers round it themselves
    maskable = tile_svg(glyphs, bounds, 30, radius=0)  # glyph inside the maskable safe zone

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium_path())
        page = browser.new_page()

        def raster(svg: str, size: int) -> Image.Image:
            page.set_viewport_size({"width": size, "height": size})
            page.set_content(f"<style>*{{margin:0}}svg{{display:block;width:{size}px;height:{size}px}}</style>{svg}")
            return Image.open(io.BytesIO(page.screenshot(omit_background=True)))

        if args.only != "card":
            ICONS.mkdir(parents=True, exist_ok=True)
            (ICONS / "favicon.svg").write_text(favicon)
            small = [raster(favicon, size) for size in (16, 32, 48)]
            small[2].save(ROOT / "public" / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=small[:2])
            raster(square, 180).convert("RGB").save(ICONS / "apple-touch-icon.png", optimize=True)
            raster(favicon, 192).save(ICONS / "icon-192.png", optimize=True)
            raster(favicon, 512).save(ICONS / "icon-512.png", optimize=True)
            raster(maskable, 512).convert("RGB").save(ICONS / "icon-maskable-512.png", optimize=True)
            print("icons written to public/favicon.ico and", ICONS.relative_to(ROOT))

        if args.only != "icons":
            inner = re.search(r"<svg[^>]*>(.*)</svg>", favicon, re.S)[1]
            card = browser.new_page(viewport={"width": 1200, "height": 630})
            card.set_content((HERE / "og-card.html").read_text().replace("{{MARK}}", inner))
            card.evaluate("document.fonts.ready")
            card.wait_for_timeout(1000)
            target = ROOT / args.card
            target.parent.mkdir(parents=True, exist_ok=True)
            Image.open(io.BytesIO(card.screenshot())).convert("RGB").save(target, optimize=True)
            print("card written to", target.relative_to(ROOT))
        browser.close()


if __name__ == "__main__":
    main()
