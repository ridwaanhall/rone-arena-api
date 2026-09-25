from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AddonWinRateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    match_now: int | None = None
    wr_now: float | None = None
    wr_future: float | None = None
    required_no_lose_matches: int | None = None
    message: str | None = None


class AddonIpData(BaseModel):
    model_config = ConfigDict(extra="allow")

    city: str | None = None
    state: str | None = None
    country: str | None = None
    lang: str | None = None
    client_ip: str | None = None


class AddonIpResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    msg: str | None = None
    data: AddonIpData | dict[str, str | None] | None = None
