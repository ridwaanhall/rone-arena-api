from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserAuthBaseResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    msg: str | None = None


class UserRequestBase(BaseModel):
    """Base model containing common fields for user requests (role_id and zone_id)."""

    model_config = ConfigDict(
        extra="forbid",
    )

    role_id: int = Field(
        title="Role ID",
        description="The unique role ID of the player's account. (Game ID)",
        examples=[1234567890],
    )
    zone_id: int = Field(
        title="Zone ID",
        description="The zone ID associated with the player's server region. (Server ID)",
        examples=[1234],
    )


class UserSendVcRequest(UserRequestBase):
    """Request model for sending a verification code."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "role_id": 1234567890,
                "zone_id": 1234,
            }
        },
    )


class UserLoginRequest(UserRequestBase):
    """Request model for user login with verification code."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "role_id": 1234567890,
                "zone_id": 1234,
                "vc": 1234,
            }
        },
    )

    vc: int = Field(
        title="Verification Code",
        description=(
            "The 4-digit verification code, obtained through in-game mail "
            "via the send-vc endpoint, remains valid for 5 minutes."
        ),
        examples=[1234],
    )


class UserAuthSimpleResponse(UserAuthBaseResponse):
    data: str | dict[str, Any] | None = None


class UserLoginData(BaseModel):
    model_config = ConfigDict(extra="allow")

    jwt: str | None = None
    token: str | None = None
    roleid: int | None = None
    zoneid: int | None = None
    time: int | None = None


class UserLoginResponse(UserAuthBaseResponse):
    data: UserLoginData | dict[str, Any] | None = None


class UserDataBaseResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: int
    data: Any
    msg: str | None = None
    message: str | None = None
    traceID: str | None = None


class UserInfoData(BaseModel):
    model_config = ConfigDict(extra="allow")

    avatar: str | None = None
    name: str | None = None
    level: int | None = None
    rank_level: int | None = None
    history_rank_level: int | None = None
    reg_country: str | None = None
    roleId: int | None = None
    zoneId: int | None = None


class UserInfoResponse(UserDataBaseResponse):
    data: UserInfoData | dict[str, Any] | str | None = None


class UserEntity(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    n: str | None = None
    ix: str | None = None
    i2x: str | None = None


class UserStatHighlight(BaseModel):
    model_config = ConfigDict(extra="allow")

    v: int | float | None = None
    ts: int | None = None
    hid: int | None = None
    bid: int | None = None
    sid: int | None = None
    hid_e: UserEntity | None = None
    bid_s: str | None = None


class UserStatsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    wc: int | None = None
    tc: int | None = None
    as_score: float | None = Field(default=None, alias="as")
    gt: float | None = None
    mvpc: int | None = None
    wsc: int | None = None
    mo: UserStatHighlight | None = None
    hk: UserStatHighlight | None = None
    ma: UserStatHighlight | None = None
    ms: UserStatHighlight | None = None
    mdt: UserStatHighlight | None = None
    mg: UserStatHighlight | None = None
    mtd: UserStatHighlight | None = None
    sids: list[int] = Field(default_factory=list)


class UserStatsResponse(UserDataBaseResponse):
    data: UserStatsData | dict[str, Any] | None = None


class UserSeasonData(BaseModel):
    model_config = ConfigDict(extra="allow")

    sids: list[int] = Field(default_factory=list)


class UserSeasonResponse(UserDataBaseResponse):
    data: UserSeasonData | dict[str, Any] | None = None


class UserPageInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    nextCursor: str | int | None = None
    hasNext: bool | None = None
    count: int | None = None


class UserMatchSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    sid: int | None = None
    bid: int | None = None
    hid: int | None = None
    k: int | None = None
    d: int | None = None
    a: int | None = None
    lid: int | None = None
    s: int | None = None
    mvp: int | None = None
    res: int | None = None
    ts: int | None = None
    hid_e: UserEntity | None = None
    bid_s: str | None = None


class UserMatchesData(BaseModel):
    model_config = ConfigDict(extra="allow")

    pageInfo: UserPageInfo | None = None
    result: list[UserMatchSummary] = Field(default_factory=list)


class UserMatchesResponse(UserDataBaseResponse):
    data: UserMatchesData | dict[str, Any] | None = None


class UserMatchesByHeroHeroInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    hid: int | None = None
    tc: int | None = None
    wc: int | None = None
    bs: float | None = None
    mr: int | None = None
    mrp: float | None = None
    hid_e: UserEntity | None = None
    p: int | None = None


class UserMatchesByHeroData(BaseModel):
    """Data payload for matches filtered by a specific hero."""

    model_config = ConfigDict(extra="allow")

    pageInfo: UserPageInfo | None = None
    hi: UserMatchesByHeroHeroInfo | None = None
    result: list[UserMatchSummary] = Field(default_factory=list)


class UserMatchesByHeroResponse(UserDataBaseResponse):
    """Response model for user matches filtered by hero."""

    model_config = ConfigDict(
        extra="allow",
    )

    data: UserMatchesByHeroData | None = None


class UserItemEntity(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    n: str | None = None
    ix: str | None = None
    i2x: str | None = None


class UserMatchDetailEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    f: int | None = None
    hid: int | None = None
    rid: int | None = None
    zid: int | None = None
    k: int | None = None
    d: int | None = None
    a: int | None = None
    tfr: float | None = None
    o: int | None = None
    op: float | None = None
    s: int | None = None
    mvp: int | None = None
    its: list[int] = Field(default_factory=list)
    eq: int | None = None
    ts: int | None = None
    bd: int | None = None
    fk: int | None = None
    fw: int | None = None
    hid_e: UserEntity | None = None
    its_e: list[UserItemEntity | None] = Field(default_factory=list)
    hlvl: int | None = None
    rname: str | None = None


class UserMatchDetailsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    result: list[UserMatchDetailEntry] = Field(default_factory=list)


class UserMatchDetailsResponse(UserDataBaseResponse):
    data: UserMatchDetailsData | dict[str, Any] | None = None


class UserFrequentHeroEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    hid: int | None = None
    tc: int | None = None
    wc: int | None = None
    bs: float | None = None
    mr: int | None = None
    mrp: float | None = None
    hid_e: UserEntity | None = None
    p: int | None = None


class UserFrequentHeroesData(BaseModel):
    model_config = ConfigDict(extra="allow")

    pageInfo: UserPageInfo | None = None
    result: list[UserFrequentHeroEntry] = Field(default_factory=list)


class UserFrequentHeroesResponse(UserDataBaseResponse):
    data: UserFrequentHeroesData | dict[str, Any] | None = None


class UserFriendProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    rid: int | None = None
    zid: int | None = None
    n: str | None = None
    ax: str | None = None
    pri: bool | None = None


class UserFriendEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    f: UserFriendProfile | None = None
    frid: int | None = None
    fzid: int | None = None
    cl: int | None = None
    l: int | None = None
    tbc: int | None = None
    twc: int | None = None


class UserFriendsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    bfs: Any | None = None
    wfs: list[Any] = Field(default_factory=list)
    fs: list[UserFriendEntry] = Field(default_factory=list)


class UserFriendsResponse(UserDataBaseResponse):
    data: UserFriendsData | dict[str, Any] | None = None


class UserPrivacySettingsData(BaseModel):
    model_config = ConfigDict(extra="allow")

    popup_shown: bool | None = None
    privacy: bool | None = None


class UserPrivacySettingsResponse(UserDataBaseResponse):
    data: UserPrivacySettingsData | dict[str, Any] | None = None
