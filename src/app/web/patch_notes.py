"""Plain-language patch notes shown on /patch-notes, newest release first.

Write for people who do not code: short points, everyday words, what changed for them.
A section with no points is left out. The newest entry must match `PROJECT_VERSION`
(a test enforces it), so add an entry whenever the version is bumped.
"""
from __future__ import annotations

# (key in an entry, heading shown on the page)
SECTIONS: tuple[tuple[str, str], ...] = (
    ("new", "New"),
    ("improved", "Improved"),
    ("fixed", "Fixed"),
    ("removed", "Removed"),
)

PATCH_NOTES: list[dict[str, object]] = [
    {
        "version": "1.2.1",
        "date": "2026-10-10",
        "summary": "A standings simulator for pro leagues, and the site keeps working when the main server is down.",
        "new": [
            "A new Standings page lets you change any match result and watch the table and playoff line move.",
            "It works for the Indonesian and Philippine seasons, or for your own league with any number of teams.",
            "Every team shows its chance of reaching the playoffs, and whether it is already through or out.",
            "Pages now come with a plain text version, and a new llms.txt file helps AI assistants read the site.",
        ],
        "improved": [
            "If the main server has a problem, the website switches to the backup server by itself.",
        ],
    },
    {
        "version": "1.2.0",
        "date": "2026-10-10",
        "summary": "Pro league match data arrives, and pictures load more reliably.",
        "new": [
            "Pro league data for Indonesia and the Philippines: the season schedule, the standings and full match results.",
            "Every match shows each player's hero, kills, deaths, assists, items and damage.",
            "Philippine matches also show the order in which items were bought.",
            "Indonesian league schedules can be shown in English or in Indonesian.",
            "A new Esports section in the playground lets you try it all in your browser.",
        ],
        "improved": [
            "Pictures now come through an image helper, so they load faster and more reliably on the website and in the API.",
            "Repeat requests for league data come back quickly, because results are kept for 5 minutes.",
            "The version number in the header now opens these patch notes.",
            "Links to the site look better when shared, with a new preview image and clearer titles in search results.",
        ],
    },
    {
        "version": "1.1.0",
        "date": "2026-09-25",
        "summary": "Hero wallpapers, faster hero lookups and a new website.",
        "new": [
            "Hero wallpapers for phones and desktops.",
            "A new look for the whole website, with a light and a dark theme.",
            "A Showcase page with sites built on the API.",
            "The playground shows results as tables, plain data or ready-to-copy code.",
        ],
        "improved": [
            "Looking up a hero by name is much faster.",
            "Signing in now guides you through two simple steps.",
        ],
        "fixed": [
            "The IP lookup no longer slows down other requests.",
        ],
        "removed": [
            "The old hero ratings feature stopped working because the game turned it off. Please stop using it.",
        ],
    },
]
