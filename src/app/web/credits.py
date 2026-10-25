"""Where the data comes from, named on every page (footer), in /llms.txt and in the README.

Sources are credited by name only: the league sites' addresses stay encrypted (`EsportsSourceProvider`), so no
host name is written here or anywhere else in the repository.
"""
from __future__ import annotations

# The professional leagues whose official public sites the esports endpoints read, in the order they were added.
ESPORTS_SOURCES: tuple[str, ...] = ("MPL Indonesia", "MPL Philippines", "MPL Malaysia", "MPL Cambodia")


def _listed(names: tuple[str, ...]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


DATA_CREDITS = (
    f"Esports data: the official public sites of {_listed(ESPORTS_SOURCES)}. "
    "Game data: Moonton's publicly available game services."
)
