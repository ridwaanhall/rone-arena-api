from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, ConfigDict


class AcademyCollectionData(BaseModel):
    model_config = ConfigDict(extra="allow")

    records: list[dict[str, Any]] | None = None
    total: int | None = None


class AcademyCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    message: str | None = None
    data: AcademyCollectionData | dict[str, Any] | None = None
    traceID: str | None = None


class AcademyRatingsSubjectData(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    title: str | None = None
    desc: str | None = None


class AcademyRatingsItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    subject: int | None = None
    title: str | None = None
    desc: str | None = None
    comment_count: int | None = None
    ranking: list[dict[str, Any]] | None = None


class AcademyRatingsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    total: int | None = None
    list: List[Any] | None = None
    has_more: bool | None = None
    subject: AcademyRatingsSubjectData | None = None


class AcademyRatingsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    message: str | None = None
    traceID: str | None = None
    data: AcademyRatingsData | dict[str, Any] | None = None
