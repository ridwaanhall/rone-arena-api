"""Products built on the Rone Arena API, shown on the home and showcase pages.

Each feature lists the endpoints (method, OpenAPI path) it is built from, so
readers can open the same request in the playground and reproduce the page.
Anyone can add a project: the showcase issue form
(`.github/ISSUE_TEMPLATE/showcase.yml`) collects the same fields, and an
accepted submission becomes one more entry here.
"""
from __future__ import annotations

from typing import Any

REPO_URL = "https://github.com/ridwaanhall/rone-arena-api"
SUBMIT_URL = f"{REPO_URL}/issues/new?template=showcase.yml"

SHOWCASE: list[dict[str, Any]] = [
    {
        "name": "Arena Academy",
        "url": "https://arena-academy.rone.dev/",
        "about": (
            "A hero encyclopedia and stats site for Mobile Legends: Bang Bang. Every hero page, "
            "ranking, and guide is rendered from public Rone Arena endpoints."
        ),
        "shows": "How to build a full website on the public hero and academy endpoints, without any sign-in.",
        "contributors": [("ridwaanhall", "https://ridwaanhall.com")],
        "features": [
            ("Home: top win rates this week", [("GET", "/api/heroes/rank")]),
            ("Hero list with role and lane filters", [("GET", "/api/heroes/positions")]),
            ("Hero page: lore, skills, relations", [("GET", "/api/heroes/{hero_identifier}"), ("GET", "/api/heroes/{hero_identifier}/relations")]),
            ("Hero page: stats and trends", [("GET", "/api/heroes/{hero_identifier}/stats"), ("GET", "/api/heroes/{hero_identifier}/trends")]),
            ("Hero page: skill combos", [("GET", "/api/heroes/{hero_identifier}/skill-combos")]),
            ("Hero page: counters and compatibility", [("GET", "/api/heroes/{hero_identifier}/counters"), ("GET", "/api/heroes/{hero_identifier}/compatibility")]),
            ("Hero page: builds and guides", [("GET", "/api/academy/heroes/{hero_identifier}/builds"), ("GET", "/api/academy/heroes/{hero_identifier}/recommended")]),
            ("Rankings by rank tier", [("GET", "/api/heroes/rank")]),
            ("Academy: roles, items, spells, emblems, ranks", [
                ("GET", "/api/academy/roles"),
                ("GET", "/api/academy/equipment"),
                ("GET", "/api/academy/spells"),
                ("GET", "/api/academy/emblems"),
                ("GET", "/api/academy/ranks"),
            ]),
            ("Tools: win-rate calculator", [("GET", "/api/addon/win-rate-calculator")]),
        ],
    },
    {
        "name": "Arena Card",
        "url": "https://arena-card.rone.dev/",
        "about": (
            "A player identity card. Players sign in with a code sent to their in-game mail and "
            "get their profile, ranked statistics, and match history on one page."
        ),
        "shows": "How to use the user endpoints: the verification-code sign-in, the JWT, and the signed-in player data.",
        "contributors": [("ridwaanhall", "https://ridwaanhall.com")],
        "features": [
            ("Sign in with an in-game code", [("POST", "/api/user/auth/send-vc"), ("POST", "/api/user/auth/login")]),
            ("Profile card: name, avatar, rank, region", [("GET", "/api/user/info")]),
            ("Ranked statistics", [("GET", "/api/user/stats"), ("GET", "/api/user/season")]),
            ("Match history and match details", [("GET", "/api/user/matches"), ("GET", "/api/user/matches/{match_id}")]),
            ("Most played heroes", [("GET", "/api/user/heroes/frequent"), ("GET", "/api/user/matches/hero/{hero_identifier}")]),
            ("Friends", [("GET", "/api/user/friends")]),
            ("Sign out", [("POST", "/api/user/auth/logout")]),
        ],
    },
]


def with_playground_links(web_paths: dict[tuple[str, str], str]) -> list[dict[str, Any]]:
    """Attach the playground page for each endpoint a feature uses."""
    products = []
    for product in SHOWCASE:
        features = []
        for label, endpoints in product["features"]:
            features.append(
                {
                    "label": label,
                    "endpoints": [
                        {"method": method, "path": path, "web_path": web_paths.get((method, path))}
                        for method, path in endpoints
                    ],
                }
            )
        contributors = [{"name": name, "url": url} for name, url in product["contributors"]]
        products.append({**product, "features": features, "contributors": contributors})
    return products


# The showcase issue form, field by field, in the order the form asks for them.
# `id` must match the field id in `.github/ISSUE_TEMPLATE/showcase.yml`.
SUBMISSION_FIELDS: list[dict[str, str]] = [
    {"id": "name", "label": "Project name", "help": "What the project is called. Keep \"MLBB\" and \"Mobile Legends\" out of the name; those marks belong to Moonton."},
    {"id": "url", "label": "Live URL", "help": "Where anyone can open it right now: a website, an app store page, or a bot invite."},
    {"id": "source", "label": "Source code", "help": "Optional. A public repository, if the code is open."},
    {"id": "about", "label": "About", "help": "One or two sentences: what it is and who it is for."},
    {"id": "shows", "label": "Shows you", "help": "What another developer learns from it, for example which endpoint group or pattern it demonstrates."},
    {"id": "features", "label": "Features and endpoints", "help": "One line per page or feature: the feature, a pipe, then the endpoints it calls, comma separated. Use the paths exactly as the API docs list them."},
    {"id": "contributor", "label": "Contributor name", "help": "The name to credit on the showcase. Add more names separated by commas."},
    {"id": "contributor_url", "label": "Contributor link", "help": "One link per name, in the same order: a personal website, GitHub, X, or Instagram."},
    {"id": "screenshot", "label": "Screenshot", "help": "Optional. Drag an image into the field so reviewers can see it."},
]


def submission_example(product: dict[str, Any]) -> str:
    """Render one showcase entry the way the issue form expects it filled in."""
    features = "\n".join(
        f"{label} | " + ", ".join(f"{method} {path}" for method, path in endpoints)
        for label, endpoints in product["features"]
    )
    names, links = zip(*product["contributors"])
    values = {
        "name": product["name"],
        "url": product["url"],
        "source": "(optional)",
        "about": product["about"],
        "shows": product["shows"],
        "features": features,
        "contributor": ", ".join(names),
        "contributor_url": "\n".join(links),
        "screenshot": "(optional)",
    }
    return "\n\n".join(f"### {field['label']}\n{values[field['id']]}" for field in SUBMISSION_FIELDS)


def llm_prompt(base_url: str) -> str:
    """A prompt a contributor pastes into a coding assistant inside their own project."""
    headings = "\n".join(f"### {field['label']}" for field in SUBMISSION_FIELDS)
    return f"""I want to submit this project to the Rone Arena API showcase: {base_url}showcase

Read this codebase and find every call to the Rone Arena API (paths that start with /api/, for example /api/heroes/rank or /api/user/info). Then fill in the showcase submission below.

Rules:
- Use only what the code shows. Do not invent features, URLs, or endpoints.
- Write each endpoint as its method and the path exactly as the API docs list it, with path parameters in braces: GET /api/heroes/{{hero_identifier}}/stats, not GET /api/heroes/1/stats. The full list is at {base_url}api/openapi.json
- Features and endpoints: one line per page or feature, formatted as `Feature | METHOD /path, METHOD /path`. Group calls under the page that shows their data.
- About: one or two plain sentences. Shows you: one sentence on what another developer can learn from this project.
- The project name must not contain "MLBB" or "Mobile Legends".
- If you cannot find something (the live URL, my name or link), write TODO so I can fill it in.

Reply with exactly these sections as Markdown, in this order:

{headings}

Leave the Screenshot section empty. After the sections, give me one link that opens the form with the text fields already filled in: start from {SUBMIT_URL} and add title=[Showcase]: <project name>, then name, url, source, about, shows, features, contributor and contributor_url as query parameters, each value URL-encoded.
"""
