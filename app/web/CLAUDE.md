# Web UI (`app/web`)

- **Styling**: One hand-written design system, `app/web/static/css/arena.css`: tokens first
  (light "paper" and dark themes), then components (`.button`, `.input`/`.select`, `.toggle`,
  `.tabs`, `.ruled` tables, `.section`, `.endpoint`, `.method--get|post`, `.menu`, `.modal`,
  `.prose`). No build step, no Tailwind. Restyle through the tokens.
- **Design language ("field manual")**: the API presented like a printed reference. Black ink on
  paper, ruled lines instead of cards, section titles in a left margin column, Archivo (condensed
  width for headings, normal for body) and IBM Plex Mono for data. One highlighter accent
  (`--mark`, chartreuse) used only behind marks, on the primary button, and on selected states;
  never as text colour. Data colours carry meaning (win/loss/info). Light is the designed default;
  dark follows the system or the toggle.
- **Avoid generic AI-template tells** (enforced in part by `test_ui_avoids_generic_ai_template_tells`):
  Inter/Geist/Space Grotesk, purple or neon-on-dark palettes, glows and radial halos, glass/blur,
  gradient text, badges or eyebrow labels above headlines, icon tiles over headings, identical card
  grids, huge stat rows, nested cards, pulsing dots, decorative terminals, slogan copy, em dashes.
  Prefer real data (the home page loads live rankings) over decoration.
- **Showcase**: `app/web/showcase.py` maps pages of each community project to the endpoints they
  call, with `contributors` as `(name, link)` pairs; rendered on `/` and `/showcase`. A test fails if
  a listed endpoint stops existing. Submissions come in through the issue form
  `.github/ISSUE_TEMPLATE/showcase.yml`; its field ids and labels must match `SUBMISSION_FIELDS`
  (tested). To accept one, turn its "Feature | METHOD /path" lines into a new `SHOWCASE` entry.
- **JavaScript**: Vanilla JS, no build tools. `static/js/arena.js` (theme, nav, session/JWT cache,
  modals; exposes `window.ArenaWebAuth`), `static/js/home.js` (live rankings table) and
  `static/js/playground.js` (endpoint forms, readable/raw/code response tabs). Asset URLs are
  cache-busted with a content hash (`ASSET_VERSION` in `app/web/routers/root.py`).
