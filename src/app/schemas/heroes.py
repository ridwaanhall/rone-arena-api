from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class HeroCollectionData(BaseModel):
    model_config = ConfigDict(extra="allow")

    records: list[dict[str, Any]] | None = None
    total: int | None = None


class HeroCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    message: str | None = None
    data: HeroCollectionData | dict[str, Any] | None = None
    traceID: str | None = None
