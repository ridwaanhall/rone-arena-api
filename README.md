# Rone Arena API & Web

[![Web Live](https://img.shields.io/badge/API-Live-brightgreen?logo=fastapi&logoColor=white)](https://arena.rone.dev)
![License](https://img.shields.io/github/license/ridwaanhall/rone-arena-api?logo=bsd&logoColor=white)
![Stars](https://img.shields.io/github/stars/ridwaanhall/rone-arena-api?logo=github)
![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)

![Landing Page](images/blog/landing-page-v3.2.2.webp)

Rone Arena is an unofficial, community-maintained data API for the game **Mobile Legends: Bang Bang**.
It provides access to hero analytics, in-game performance data, academy resources, player endpoints, and utility tools. It is designed with a consistent RESTful structure, supports flexible hero identifiers (ID or name), and delivers standardized responses for seamless integration into applications, dashboards, analytics systems, and internal tooling.

## Disclaimer

> **Rone Arena** is an unofficial, community-maintained project. It is not affiliated with, endorsed by,
> sponsored by, or associated with Shanghai Moonton Technology Co., Ltd. "Mobile Legends: Bang Bang",
> "MLBB", and all related names, marks, logos, and in-game assets are trademarks of their respective
> owners. Data is sourced from publicly accessible endpoints and provided for informational,
> educational, and analytical purposes only.

> [!IMPORTANT]
> **Built with Dedication:** This project is the result of over [![wakatime](https://wakatime.com/badge/user/018b799e-de53-4f7a-bb65-edc2df9f26d8/project/07151d3c-c9e1-4f53-bb7f-f706f8261ac4.svg)](https://wakatime.com/badge/user/018b799e-de53-4f7a-bb65-edc2df9f26d8/project/07151d3c-c9e1-4f53-bb7f-f706f8261ac4) of meticulous coding, architecting, and performance tuning to ensure the best developer experience.

## Features

- **Public REST API for game data**: user, heroes, academy, and addon service groups
- **Web playground for all endpoints**: form-driven execution at `/web/*`
- **Flexible hero identifier support**: hero ID or hero name (including compact slug-like names)
- **Readable response views**: switch between Key-Value and Key-As-Header table modes
- **Language snippets**: curl, python, javascript, go, node, php, java, csharp
- **Copy helpers**: copy snippet, copy response, copy JWT from signed-in menu
- **Auth modal flow for user endpoints**: Send VC + Login in one popup
- **JWT-aware navbar state**: profile photo, username, country, roleId(zoneId), sign out
- **Tutorial & blog pages**: step-by-step guides with SEO-ready detail pages
- **OpenAPI-first docs**: Swagger UI, ReDoc, and OpenAPI JSON

## Documentation

| Title | Link | Description |
| --- | --- | --- |
| Website Home | [arena.rone.dev](https://arena.rone.dev) | Main landing page with quick access to Demo Website and API Docs. |
| Tutorial and Blog | [arena.rone.dev/blog](https://arena.rone.dev/blog) | Guides, tutorials, and release/changelog posts. |
| Web Playground | [arena.rone.dev/web](https://arena.rone.dev/web) | Interactive endpoint workspace for executing API requests from browser forms. |
| Swagger UI | [arena.rone.dev/api/docs](https://arena.rone.dev/api/docs) | OpenAPI-powered docs with live request execution and authorization support. |
| ReDoc | [arena.rone.dev/api/redoc](https://arena.rone.dev/api/redoc) | Alternative API documentation view optimized for reference reading. |
| OpenAPI JSON | [arena.rone.dev/api/openapi.json](https://arena.rone.dev/api/openapi.json) | Raw OpenAPI schema for tooling, SDK generation, and integrations. |

### Web Interface Highlights

- Home page provides two entry points: **Open Demo Website** and **Open API Docs**
- Demo Website (`/web/*`) is recommended for most usage and exploration
- Sign In modal supports **Send VC** then **Login with VC** (same role/zone fields, VC expires in 5 minutes)
- Signed-in menu shows profile details and **Copy JWT** for quick docs authorization
- Endpoint cards include request forms, snippets, readable/JSON responses, and copy actions
- Readable response section supports view switching: **Key-Value** or **Key As Header**

## Base URLs

> [!NOTE]
> Recommended for 500+ requests per day: https://arena-hv.fastapicloud.dev
> Standard for 0 - 500 requests per day: https://arena.rone.dev

```txt
https://arena-hv.fastapicloud.dev/     # Recommended base for high-volume traffic
https://arena-hv.fastapicloud.dev/api  # API base (fastapicloud)
https://arena.rone.dev/                 # Landing page
https://arena.rone.dev/blog             # Tutorial and blog list
https://arena.rone.dev/blog/{slug}      # Blog detail page
https://arena.rone.dev/web              # Web interface (redirects to /web/user)
https://arena.rone.dev/web/user         # User endpoints playground
https://arena.rone.dev/web/heroes       # Hero endpoints playground
https://arena.rone.dev/web/academy      # Academy endpoints playground
https://arena.rone.dev/web/addon        # Addon endpoints playground
https://arena.rone.dev/api              # API index/status
https://arena.rone.dev/api/docs         # Swagger UI
https://arena.rone.dev/api/redoc        # ReDoc
https://arena.rone.dev/api/openapi.json # OpenAPI schema
```

## Client SDKs

The Python SDK lives in its own repository and is published to PyPI separately from this API:

```bash
pip install OpenMLBB
```

A TypeScript/JavaScript alternative is available on npm as `mlbb-sdk`.

## API Coverage

Full endpoint lists, operation summaries, and request/response schemas are always available in:

- `https://arena.rone.dev/api/docs` (Swagger UI)
- `https://arena.rone.dev/web` (interactive web endpoint explorer)

This ensures API coverage documentation stays up to date with every release without maintaining manual endpoint lists in README.

## Changelog

See [Releases](https://github.com/ridwaanhall/rone-arena-api/releases) for migration notes and updates.

## License & Attribution

This project is licensed under the **BSD 3-Clause License**.
Attribution must be preserved to **Moonton (the creator of Mobile Legends: Bang Bang)** and either
**ridwaanhall (the maintainer of this API project)** *or*
**RoneAI (the organization behind this API)** in all downstream usage and derivative projects.

### Notice

All data is sourced from publicly available content and provided for educational, analytical, and community purposes only.
Visual assets and references are used respectfully and do not imply official partnership or endorsement.

### Example Attribution (README or app footer)

> Powered by Rone Arena API
> Game data © Moonton (Mobile Legends: Bang Bang)
> API maintained by ridwaanhall / RoneAI
> Unofficial project, not affiliated with or endorsed by Moonton

<details>
<summary>Local Development (internal)</summary>

### Setup

```bash
# use this if already have pyproject.toml and uv.lock
uv sync
cp .env.example .env
```

### Run

#### Development

```bash
fastapi dev
```

#### Production

```bash
fastapi run
```

#### Deploy

```bash
# deploy via fastapicloud
fastapi deploy
```

### Test

```bash
pytest
```

### Environment Variables

- `SECRET_KEY`
- `RONE_DEV_ACCESS_KEY`
- `RONE_DEV_ACCESS_KEY_V2`

See `.env.example` for full configuration.

</details>
