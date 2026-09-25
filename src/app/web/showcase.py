"""Products built on the Rone Arena API, shown on the home and showcase pages.

Each feature lists the endpoints (method, OpenAPI path) it is built from, so
readers can open the same request in the playground and reproduce the page.
Anyone can add a project: the showcase issue form
(`.github/ISSUE_TEMPLATE/showcase.yml`) asks for one entry in exactly this
format, so an accepted submission is pasted into `SHOWCASE` as-is.
"""
from __future__ import annotations

import json
import re
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


def slug(name: str) -> str:
    """Page anchor for a project; community names may carry any punctuation."""
    return "project-" + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed")


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
        products.append({**product, "slug": slug(product["name"]), "features": features, "contributors": contributors})
    return products


# The keys of one showcase entry, in order, with what to write in each.
ENTRY_KEYS: list[tuple[str, str]] = [
    ("name", "What the project is called. Keep \"MLBB\" and \"Mobile Legends\" out of the name; those marks belong to Moonton."),
    ("url", "Where anyone can open it right now: a website, an app store page, or a bot invite."),
    ("about", "One or two sentences: what it is and who it is for."),
    ("shows", "What another developer learns from it, for example which endpoint group or pattern it demonstrates."),
    ("contributors", "A list of (name, link) pairs, one per person to credit. The link can be a personal website, GitHub, X, or Instagram."),
    ("features", "A list of (feature, endpoints) pairs, one per page or feature. Endpoints are (method, path) pairs, with the path exactly as the API docs list it."),
]


def _text(value: str) -> str:
    # JSON string syntax is valid Python and always uses double quotes, like the file.
    return json.dumps(value, ensure_ascii=False)


def _pairs(pairs: list[tuple[str, str]]) -> str:
    return "[" + ", ".join(f"({_text(first)}, {_text(second)})" for first, second in pairs) + "]"


def format_entry(product: dict[str, Any]) -> str:
    """Write one entry as Python source, in the same layout as `SHOWCASE` above."""
    features = "\n".join(f"        ({_text(label)}, {_pairs(endpoints)})," for label, endpoints in product["features"])
    return (
        "{\n"
        f'    "name": {_text(product["name"])},\n'
        f'    "url": {_text(product["url"])},\n'
        f'    "about": {_text(product["about"])},\n'
        f'    "shows": {_text(product["shows"])},\n'
        f'    "contributors": {_pairs(product["contributors"])},\n'
        '    "features": [\n'
        f"{features}\n"
        "    ],\n"
        "},"
    )


def llm_prompt(base_url: str) -> str:
    """A prompt a contributor pastes into a coding assistant inside their own project."""
    example = format_entry(SHOWCASE[0])
    return f"""I want to submit this project to the Rone Arena API showcase: {base_url}showcase

Read this codebase and find every call to the Rone Arena API (paths that start with /api/, for example /api/heroes/rank or /api/user/info). Then write this project's showcase entry.

Rules:
- Use only what the code shows. Do not invent features, URLs, or endpoints.
- Write each endpoint as a (method, path) pair, with the path exactly as the API docs list it and path parameters in braces: ("GET", "/api/heroes/{{hero_identifier}}/stats"), not ("GET", "/api/heroes/1/stats"). The full list is at {base_url}api/openapi.json
- features: one (feature, endpoints) pair per page or feature. Group calls under the page that shows their data.
- about: one or two plain sentences. shows: one sentence on what another developer can learn from this project.
- contributors: one (name, link) pair per person. The link can be a personal website, GitHub, X, or Instagram.
- The project name must not contain "MLBB" or "Mobile Legends".
- If you cannot find something (the live URL, my name or link), write "TODO" so I can fill it in.

Output format: one Python dict literal, in a ```python code block, with exactly the keys, order, and layout of this example. Use double-quoted strings and tuples, keep the trailing comma after the closing brace, and write nothing else in the block:

```python
{example}
```

After the code block, give me one link that opens the submission form with the entry already filled in: {SUBMIT_URL}&title=%5BShowcase%5D%3A%20<project name, URL-encoded>&entry=<the entry, URL-encoded>
"""
