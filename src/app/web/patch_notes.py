"""Plain-language patch notes shown on /patch-notes, newest release first.

Write for people who do not code: short points, everyday words, what changed for them.
A section with no points is left out. The newest entry must match `PROJECT_VERSION`
(a test enforces it), so add an entry whenever the version is bumped.
"""
from __future__ import annotations

from typing import Any

# (key in an entry, heading shown on the page)
SECTIONS: tuple[tuple[str, str], ...] = (
    ("new", "New"),
    ("improved", "Improved"),
    ("fixed", "Fixed"),
    ("removed", "Removed"),
)

PATCH_NOTES: list[dict[str, Any]] = [
    {
        "version": "1.6.2",
        "date": "2026-10-25",
        "summary": "Malaysian team names read cleanly in match details.",
        "fixed": [
            "A Malaysian team whose name the league cuts short with dots (\"iG ........\") is named as in the schedule (\"iG\").",
        ],
    },
    {
        "version": "1.6.1",
        "date": "2026-10-25",
        "summary": "Malaysian match pages load every time and never show another team's numbers.",
        "fixed": [
            "Malaysian match pages no longer fail at random: the league site sometimes sends a faulty copy, which is now fetched again.",
            "Team 2's kills, deaths and assists in Malaysian matches are always their own, never a copy of team 1's.",
            "A Malaysian game the league published without heroes is left out instead of breaking the whole match.",
        ],
    },
    {
        "version": "1.6.0",
        "date": "2026-10-25",
        "summary": "Two more pro leagues: Malaysia and Cambodia, with their seasons, standings and playoffs.",
        "new": [
            "Follow the Malaysian league: every week's matches, the standings and the playoff bracket days.",
            "Open any Malaysian match to see each game's heroes, KDA, items, gold and damage.",
            "Follow the Cambodian league: every week's matches, the standings and the playoff seeds.",
            "The standings simulator now has Malaysia and Cambodia tabs, starting from their real seasons.",
        ],
        "improved": [
            "Every page now credits where its data comes from: the official league sites and the game's public services.",
        ],
    },
    {
        "version": "1.5.0",
        "date": "2026-10-25",
        "summary": "Answers come back faster on repeat visits, and spell and item texts read cleanly.",
        "improved": [
            "Hero, academy and esports answers are reused for 5 minutes, so repeat visits load faster.",
        ],
        "fixed": [
            "Retribution's description no longer shows broken placeholders like <Num9>.",
            "Boots no longer show the game's live counter text, such as \"Current: <#bv 25>\".",
        ],
    },
    {
        "version": "1.4.0",
        "date": "2026-10-24",
        "summary": "Playoffs for the Indonesian and Philippine pro leagues, and match pages that load again.",
        "new": [
            "See each league's playoffs: the bracket picture, the seeds and every playoff match.",
            "Indonesian playoff matches show their round, such as Upper Bracket Finals.",
            "Every match now says how many games it is played over and who won it.",
            "Philippine games show an estimated length, worked out from the gold earned.",
            "Philippine games will show highlight videos and screenshots once the league adds them.",
        ],
        "improved": [
            "Matches not decided yet show TBD without borrowing the league's logo.",
        ],
        "fixed": [
            "Philippine match details load on our own server again instead of failing.",
        ],
    },
    {
        "version": "1.3.0",
        "date": "2026-10-20",
        "summary": "Pick which of our two servers the site uses, plus a new site icon and share picture.",
        "new": [
            "A switch on the home page and playground picks the primary or the mirror server. Primary is the default.",
            "The site remembers your server choice on this device.",
            "AI assistants can now ask any page for a plain text version.",
        ],
        "improved": [
            "Links shared on chat apps and social media show a new preview picture.",
            "The site now has its own icon in browser tabs and on phone home screens.",
        ],
        "fixed": [
            "The site icon no longer fails to load.",
        ],
    },
    {
        "version": "1.2.3",
        "date": "2026-10-11",
        "summary": "Pro league data loads faster and the site keeps working when the main server struggles.",
        "improved": [
            "League schedules and standings now load faster, because recent answers are shared between servers.",
            "If the main server fails a request, you are sent to the backup server automatically.",
        ],
    },
    {
        "version": "1.2.2",
        "date": "2026-10-10",
        "summary": "The Indonesian league pages now load reliably.",
        "fixed": [
            "The Indonesian league schedule and standings no longer fail with an error some of the time.",
            "Some data that needs a private setting now says so clearly instead of failing to start.",
        ],
    },
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
        "fixed": [
            "The Indonesian league schedule and standings load again instead of failing with an error.",
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
