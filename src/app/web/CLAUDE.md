# Web UI (`src/app/web`, assets in `public/`)

- **Styling**: One hand-written design system, `public/static/css/arena.css`: tokens first
  (light "paper" and dark themes), then the shell, then components (`.button`, `.input`/`.select`,
  `.toggle`, `.tabs`, `.segmented`, `.ruled` tables, `.ep-row`, `.method--get|post`, `.menu`,
  `.modal`, `.prose`). No build step, no Tailwind. Restyle through the tokens.
- **Design language ("field manual")**: the API presented like a printed reference. Black ink on
  paper, ruled lines instead of cards, Archivo (condensed width for headings, normal for body) and
  IBM Plex Mono for data. One highlighter accent (`--mark`, chartreuse) used only behind marks, on
  the primary button, and on selected states; never as text colour. Data colours carry meaning
  (win/loss/info). Light is the designed default; dark follows the system or the toggle.
- **Layout (console shell), exactly four tiers**, mobile first, `min-width` queries at 640 / 1024 /
  1440 only (a test holds this):
  - mobile: slim top bar + fixed bottom tab bar (`partials/tabbar.html`; "More" opens a sheet).
  - tablet: two-row top bar (brand, search, account; then section tabs).
  - laptop: persistent left rail (`partials/rail.html`, one header that changes shape per tier and
    holds the account menu exactly once); workbench shows request | response side by side.
  - extra: wider rail; workbench adds a sticky endpoint list as a third pane.
  - `<details data-open-from="1024">` is rendered open and folded by `arena.js` below that width.
- **Pages**: home is a board of working modules (live hero meta with Win/Pick/Ban sort, the real
  first request and its response, the endpoint catalogue, showcase and posts). `/web/{group}` is a
  filterable endpoint index; `/web/{group}/{path}` is the workbench (`web/_operation.html`), where
  the `<form>` itself is the grid so the response stays inside it for `playground.js`. Showcase and
  blog posts use `.with-toc` (sticky contents from laptop up). A command palette
  (`partials/palette.html`, Ctrl/Cmd+K or `/`) lists every page and endpoint, rendered server-side.
- **Avoid generic AI-template tells** (enforced in part by `test_ui_avoids_generic_ai_template_tells`):
  Inter/Geist/Space Grotesk, purple or neon-on-dark palettes, glows and radial halos, glass/blur,
  gradient text, badges or eyebrow labels above headlines, icon tiles over headings, identical card
  grids, huge stat rows, nested cards, pulsing dots, decorative terminals, slogan copy, em dashes.
  Prefer real data (the home page loads live rankings) over decoration. `<main>` carries no
  attributes (the em-dash test splits on it).
- **Showcase**: `src/app/web/showcase.py` maps pages of each community project to the endpoints they
  call, with `contributors` as `(name, link)` pairs; rendered on `/` and `/showcase`. A test fails if
  a listed endpoint stops existing. Submissions come in through the issue form
  `.github/ISSUE_TEMPLATE/showcase.yml` as one Python dict in the `SHOWCASE` format (the page's LLM
  prompt writes it); to accept one, paste it into `SHOWCASE`. `format_entry` renders that format
  and a test checks it round-trips.
- **JavaScript**: Vanilla JS, no build tools. `public/static/js/arena.js` (theme, palette, More
  sheet, responsive details, TOC highlight, session/JWT cache, modals; exposes
  `window.ArenaWebAuth`), `public/static/js/home.js` (live rankings + first-request exchange) and
  `public/static/js/playground.js` (endpoint forms, readable/raw/code response tabs, phone
  Request/Response switch). API calls go to the page's own origin. Asset URLs are cache-busted with
  `ASSET_VERSION` (content hash locally, the Worker version id on Cloudflare). `public/static` stays
  under 120 KB (tested).
