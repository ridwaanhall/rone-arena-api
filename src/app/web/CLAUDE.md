# Web UI (`src/app/web`, assets in `public/`)

- **Styling**: One hand-written design system, `public/static/css/arena.css`: tokens first
  (light "paper" and dark themes), then components (`.button`, `.input`/`.select`, `.toggle`,
  `.tabs`, `.ruled` tables, `.section`, `.endpoint`, `.method--get|post`, `.menu`, `.modal`,
  `.prose`). No build step, no Tailwind. Restyle through the tokens.
- **Design language ("field manual")**: the API presented like a printed reference. Black ink on
  paper, ruled lines instead of cards, section titles in a left margin column, Archivo (condensed
  width for headings, normal for body) and IBM Plex Mono for data. One highlighter accent
  (`--mark`, chartreuse) used only behind marks, on the primary button, and on selected states;
  never as text colour. Data colours carry meaning (win/loss/info). Light is the designed default;
  dark follows the system or the toggle. Anything on `--mark` takes `--mark-ink` text (dark in
  both themes); never put `--ink` text or borders on the green, since `--ink` turns light in dark mode.
- **Typography**: font sizes in `rem` (the reader's browser setting scales them); body 1rem at
  1.55 line height, running text capped near 70ch, headings `text-wrap: balance`, paragraphs
  `pretty`, numbers tabular. Form controls stay at 16px on touch screens (iOS zooms below that)
  and drop to 15px only with a fine pointer.
- **Screen tiers**: mobile < 640, tablet 640+, laptop 1024+, monitor 1440+ (1320px page),
  extra 1920+ (1480px page, root text 17px). Check all five, light and dark, after layout changes.
- **Avoid generic AI-template tells** (enforced in part by `test_ui_avoids_generic_ai_template_tells`):
  Inter/Geist/Space Grotesk, purple or neon-on-dark palettes, glows and radial halos, glass/blur,
  gradient text, badges or eyebrow labels above headlines, icon tiles over headings, identical card
  grids, huge stat rows, nested cards, pulsing dots, decorative terminals, slogan copy, em dashes.
  Prefer real data (the home page loads live rankings) over decoration.
- **Showcase**: `src/app/web/showcase.py` maps pages of each community project to the endpoints they
  call, with `contributors` as `(name, link)` pairs; rendered on `/` and `/showcase`. A test fails if
  a listed endpoint stops existing. Submissions come in through the issue form
  `.github/ISSUE_TEMPLATE/showcase.yml` as one Python dict in the `SHOWCASE` format (the page's LLM
  prompt writes it); to accept one, paste it into `SHOWCASE`. `format_entry` renders that format
  and a test checks it round-trips.
- **JavaScript**: Vanilla JS, no build tools. `public/static/js/arena.js` (theme, nav, session/JWT cache,
  modals; exposes `window.ArenaWebAuth`), `public/static/js/home.js` (live rankings table) and
  `public/static/js/playground.js` (endpoint forms, readable/raw/code response tabs). Asset URLs are
  cache-busted with a content hash (`ASSET_VERSION` in `src/app/web/routers/root.py`).
