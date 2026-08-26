# Rone Arena API & Web - Project Overview

## Project Purpose

**Rone Arena API & Web** is a comprehensive, production-grade REST API and web interface for **Mobile Legends: Bang Bang** game data. It is an unofficial, community-maintained project with no affiliation to or endorsement by Moonton; the game name is used descriptively only, and the brand must never incorporate the "MLBB" or "Mobile Legends" marks. It provides developers, analysts, and fans with structured, reliable access to hero information, academy resources, player statistics, and utility tools.

## Key Features

### 1. **RESTful Public API** (`/api/*`)
- **Hero Data**: Hero listings, rankings, positions, stats, skill combos, counters, relationships
- **Academy Resources**: Roles, equipment, emblems, spells, builds, lane distributions, win rate timelines
- **User Endpoints**: Authentication (with verification codes), profile data, match history, player statistics
- **Utility Tools**: Win rate calculators, IP lookup, hero compatibility analysis
- **Flexible Identifiers**: Support for hero ID or hero name (including slug-like names)
- **OpenAPI/Swagger**: Full OpenAPI 3.0 schema with interactive documentation

### 2. **Web Playground** (`/web/*`)
- **Form-Driven Endpoint Testing**: Interactive forms for all API endpoints
- **Response Viewers**: Readable (Key-Value & Key-As-Header modes) + Raw JSON views
- **Code Snippets**: Auto-generated curl, Python, JavaScript, Go, Node.js, PHP, Java, C# examples
- **Live Execution**: Test endpoints directly from the browser
- **Authentication Modal**: Integrated sign-in flow with JWT caching
- **User Profile Display**: JWT-aware navbar showing profile photo, username, country, role/zone

### 3. **Blog & Tutorials** (`/blog/*`)
- **SEO-Optimized Pages**: Markdown-based guides and release notes
- **Step-by-Step Tutorials**: Getting started, authentication, integration examples

## Architecture

### Backend Stack
- **Framework**: FastAPI (Python 3.12+)
- **Async**: Built with async/await for high concurrency
- **Database**: None (stateless API - all data fetched from upstream game-data services)
- **Upstream Services**: 
  - `https://arena.rone.dev` (Standard - 0-500 requests/day)
  - `https://arena-hv.fastapicloud.dev` (High volume - 500+ requests/day)
- **Templates**: Jinja2 for server-side rendering
- **Static Files**: Tailwind CSS, Alpine.js or vanilla JavaScript

### Frontend Stack
- **Templating**: Jinja2 (server-rendered HTML)
- **Styling**: Tailwind CSS v4
- **JavaScript**: Vanilla JS (no build tools required) with localStorage for session management
- **Interactive Features**: Dynamic forms, code snippet generation, authentication modal

### Deployment
- **Production**: Vercel (runs FastAPI via ASGI)
- **Alternative High-Volume**: arena-hv.fastapicloud.dev (for 500+ requests/day)
- **Local Dev**: FastAPI dev server at `http://127.0.0.1:8000`

## Project Structure

```
rone-arena-api/
├── app/
│   ├── api/                    # REST API endpoints
│   │   ├── routers/
│   │   │   ├── user.py         # Authentication & user profiles
│   │   │   ├── heroes.py       # Hero data, stats, analytics
│   │   │   ├── academy.py      # Game guides, builds, resources
│   │   │   ├── addon.py        # Utility endpoints (IP lookup, etc.)
│   │   │   └── root.py         # Root & metadata endpoints
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py           # Environment & configuration
│   │   ├── errors.py           # Custom error handling
│   │   ├── exceptions.py       # FastAPI exception handlers
│   │   ├── security.py         # JWT, auth helpers
│   │   ├── enums.py            # Game-related enums
│   │   ├── hero_limits.py      # Hero validation & limits
│   │   └── http.py             # HTTP client for upstream
│   ├── schemas/                # Pydantic models (request/response)
│   ├── services/               # Business logic layer
│   ├── utils/
│   │   ├── client_ip.py
│   │   ├── filters.py
│   ├── web/                    # Web UI (forms, playground)
│   │   ├── routers/
│   │   │   ├── root.py         # Landing page
│   │   │   └── blog.py         # Blog pages
│   │   ├── templates/          # Jinja2 templates
│   │   └── openapi_catalog.py  # Web endpoint metadata
│   └── main.py                 # FastAPI app setup
├── tests/                      # Pytest suite
├── pyproject.toml              # Dependencies & metadata
├── .env.example                # Environment template
└── README.md                   # User documentation
```

## Configuration

### Environment Variables

**Core Settings**:
- `DEBUG`: Set to `true` in dev; when true, API playground uses `http://127.0.0.1:8000/api` locally
- `SECRET_KEY`: Secret for signing JWTs (required)
- `IS_MAINTENANCE`: Set to `true` to restrict the API and show the maintenance page on `/`
- `IS_HIGH_TRAFFIC`: Set to `true` to restrict the API and point callers at the high-volume host
  (both default to a restricted service when unset; maintenance wins when both are true, and
  `IS_AVAILABLE` in `config.py` is derived from them, not read from the environment)
- `PROJECT_VERSION`: Current version string

**API URLs** (automatically switched based on request volume):
- `PROD_URL_STANDARD`: Standard endpoint (0-500 req/day), default: `https://arena.rone.dev/api/`
- `PROD_URL_HIGH_VOLUME`: High-volume endpoint (500+ req/day), default: `https://arena-hv.fastapicloud.dev/api/`

**Upstream Access** (for fetching game data):
- `RONE_DEV_ACCESS_KEY`: Key for rone.dev API
- `RONE_DEV_ACCESS_KEY_V2`: Alternative key for v2 endpoints

**Public Links**:
- `BASE_URL`: Homepage URL (e.g., `https://arena.rone.dev/`)
- `API_BASE_URL`: API docs URL
- `DOCS_BASE_URL`: Docs page URL

### Key Settings in `app/core/config.py`

- `PROD_URL_STANDARD` & `PROD_URL_HIGH_VOLUME`: Automatically uses local dev server when `DEBUG=True`
- All URL configs stripped of trailing slashes for consistency
- Request threshold: 500 requests/day before switching to high-volume endpoint

## CORS & Dev Mode Fix

**Issue**: When `DEBUG=True`, the frontend was still trying to fetch from production URLs (`https://arena.rone.dev`), causing CORS errors.

**Solution**:
1. Added `is_debug`, `prod_url_standard`, `prod_url_high_volume` to template context in `app/web/routers/root.py`
2. Updated JavaScript in `app/web/templates/web/group_page.html` to use local URL (`http://127.0.0.1:8000`) when DEBUG mode is active
3. API playground now respects the `IS_DEBUG` flag and routes all requests to localhost in dev mode
4. No more CORS errors when running locally with `DEBUG=True`

## Running the Project

### Development
```bash
# Activate virtual environment
source .venv/Scripts/activate  # or .venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -e .

# Set environment (create .env from .env.example)
# Make sure DEBUG=True for local development

# Run development server
uvicorn app.main:app --reload

# Access:
# - API Docs: http://127.0.0.1:8000/api/docs
# - Web Playground: http://127.0.0.1:8000/web/
```

### Production
- Deployed to Vercel (uses `prod/index.py` as ASGI handler)
- Environment variables set in Vercel dashboard
- Automatic CORS handling for production domain
- Request routing based on daily volume

## Key Dependencies

- **FastAPI**: Modern async web framework
- **Pydantic**: Data validation
- **Jinja2**: Template rendering
- **httpx**: Async HTTP client
- **python-dotenv**: Environment variable management

## Testing

```bash
pytest tests/
```

Test coverage includes:
- Client IP extraction
- Validation errors
- User router endpoints
- Web interface rendering
- OpenAPI schema generation

## Notable Implementation Details

1. **Sync-Yield ContextVar Bug (Fixed)**: FastAPI sync-yield dependencies don't reset ContextVar across thread contexts; use async-yield instead
2. **Enum String Rendering**: `str(MyStrEnum.MEMBER)` returns `MyStrEnum.MEMBER`, not the value; use `.value` or normalize with property
3. **Jinja2 TemplateResponse Order**: Requires `(request, name, context)` order; using old order triggers TypeError
4. **Two-Tier Prod URLs**: Standard for low traffic (arena.rone.dev), High-Volume for 500+ requests/day (arena-hv.fastapicloud.dev)
5. **Upstream Auth Returns HTTP 200 with Errors**: Always validate `code` field in response, not just HTTP status
6. **Debug Mode URL Switching**: When DEBUG=True, frontend automatically uses local dev server via template variables

## Branding & Trademark Constraints

The project was rebranded from "MLBB Public Data API" to **Rone Arena** because the MLBB /
Mobile Legends marks belong to Moonton and cannot be used as this project's brand identity.

- **Never** put `MLBB`, `Mobile Legends`, or `Bang Bang` in the product name, domain, repo name,
  package name, OpenAPI tag, or any other source-identifying position.
- Naming the game **descriptively** ("data for the game Mobile Legends: Bang Bang") is fine and
  intentional - that is nominative fair use.
- The `Origin`/`Referer` headers pointing at `https://www.mobilelegends.com` in `app/core/http.py`
  are **required by the upstream service** - never rewrite them in a branding sweep.
- Upstream CDN asset URLs (`akmweb.youngjoygame.com/.../mlbb/...`) inside OpenAPI response examples
  are real upstream paths - leave them alone.
- Blog post slugs are pinned explicitly in `app/web/routers/blog.py` so rebranded titles never change
  a published URL. Add a `"slug"` key when adding a post whose title may later change.

## Future Enhancements

- WebSocket support for real-time hero updates
- Advanced caching strategies (Redis)
- GraphQL layer
- Mobile app integration examples
- Battle statistics timeline analysis
- Automated meta-game updates

## Support & Donations

- GitHub Sponsors: https://github.com/sponsors/ridwaanhall
- Buy Me a Coffee: https://www.buymeacoffee.com/ridwaanhall
- Support helps sustain development and cover hosting costs

## License

BSD 3-Clause License - See [LICENSE](LICENSE) file

---

**Built by**: RoneAI  
**Contact**: founder@rone.dev  
**Website**: https://rone.dev  
**API Status**: Check https://arena.rone.dev for current availability
