"""Reusable parameter declarations shared by the API routers.

FastAPI recommends ``Annotated`` type aliases for parameters that repeat across
path operations: the metadata (title, description, constraints) lives in one
place, while each route still picks its own default, e.g. ``size: PageSize = 20``.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Path, Query

from app.core.enums import LanguageEnum, RankEnum

HeroIdentifier = Annotated[
    str,
    Path(
        title="Hero Identifier",
        description=(
            "Hero identifier as numeric hero ID or hero name. Accepts values like `30`, `Yi Sun-shin`, or `yisunshin`. "
            "Name matching ignores spaces/symbols and is case-insensitive (e.g., `Luo Yi` to `luoyi`)."
        ),
    ),
]

PageSize = Annotated[int, Query(title="Page Size", description="Number of items per page.", ge=1)]

PageIndex = Annotated[int, Query(title="Page Index", description="Page index for pagination.", ge=1)]

Lang = Annotated[LanguageEnum, Query(title="Language", description="Language code for localized content.")]

Rank = Annotated[RankEnum, Query(title="Rank", description="Rank filter for hero statistics.")]

StatsDays = Annotated[
    Literal["1", "3", "7", "15", "30"],
    Query(title="Past Days", description="Past day window for rank statistics."),
]
