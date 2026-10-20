---
name: brand-assets
description: Rebuild or change the Rone Arena favicon, app icons and 1200x630 link-preview card (og:image). Use when the logo, brand colours or card text change, or an icon or share image looks wrong.
argument-hint: "[icons|card]"
allowed-tools: Bash(uv run *), Read, Edit
---

# Rebuild the icons and share card

## What exists

| File | Use |
|---|---|
| `public/favicon.ico` | 16/32/48 px. Also served by the `/favicon.ico` route in `src/app/web/routers/root.py` for hosts without Static Assets |
| `public/images/icons/favicon.svg` | Modern browsers (`<link rel="icon" type="image/svg+xml">`) |
| `public/images/icons/apple-touch-icon.png` | 180 px, square corners (iOS rounds it) |
| `public/images/icons/icon-192.png`, `icon-512.png`, `icon-maskable-512.png` | Listed in `public/images/icons/site.webmanifest` |
| `public/images/og/rone-arena-card.png` | Default `og:image` / `twitter:image` (`DEFAULT_SHARE_IMAGE` in `root.py`) |

The mark is the capital R of Archivo Condensed Black on a `--mark` (`#d4f53c`) tile in `--mark-ink` (`#121212`),
drawn as an SVG path so the favicon needs no font. The card follows the field-manual design language in
`src/app/web/CLAUDE.md`: paper background, ruled lines, Archivo and IBM Plex Mono, highlighter only behind "API".

## Rebuild

From the repo root (needs network for the Google Fonts files; the font is cached in `.brand-build/`, gitignored):

```bash
uv run --with pillow --with fonttools --with playwright python .claude/skills/brand-assets/scripts/build.py $ARGUMENTS
```

`--only icons` or `--only card` limits the run. Edit the card's text and layout in
[scripts/og-card.html](scripts/og-card.html); `{{MARK}}` is replaced with the R tile.

## Rules

- **Rename the card file when its look changes** (for example `rone-arena-card-2.png`) and update
  `DEFAULT_SHARE_IMAGE` and the test in `tests/test_web_interface.py`. Share platforms cache by URL.
- **Never proxy share images.** `og:image` and `twitter:image` use `share_image_url` (a plain same-site URL), not
  wsrv. Images shown on pages keep the `| image` filter. `test_share_images_are_never_proxied` enforces it.
- **Keep text off the card that goes stale**: no version numbers or endpoint counts.
- **No hosting provider names** anywhere visible (`test_public_pages_never_name_the_hosting_providers`).
- **Card size stays 1200x630**, matching `DEFAULT_SHARE_SIZE`.

## Check

1. Read the PNGs back and look at them, including the 16 px favicon. It must still read as an R.
2. `uv run pytest tests -q -k "favicon or share or preview"`.
3. After deploy, re-scrape the card in the Facebook Sharing Debugger or LinkedIn Post Inspector.
