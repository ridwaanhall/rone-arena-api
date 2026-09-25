"""Products built on the Rone Arena API, shown on the home and showcase pages.

Each feature lists the endpoints (method, OpenAPI path) it is built from, so
readers can open the same request in the playground and reproduce the page.
Keep this in step with the sister sites when they change.
"""
from __future__ import annotations

from typing import Any

SHOWCASE: list[dict[str, Any]] = [
    {
        "name": "Arena Academy",
        "url": "https://arena-academy.rone.dev/",
        "about": (
            "A hero encyclopedia and stats site for Mobile Legends: Bang Bang. Every hero page, "
            "ranking, and guide is rendered from public Rone Arena endpoints."
        ),
        "shows": "How to build a full website on the public hero and academy endpoints, without any sign-in.",
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
        products.append({**product, "features": features})
    return products
