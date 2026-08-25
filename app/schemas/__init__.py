"""Schemas for the app."""

from app.schemas.academy import AcademyCollectionResponse, AcademyRatingsResponse
from app.schemas.addon import AddonIpResponse, AddonWinRateResponse
from app.schemas.heroes import HeroCollectionResponse
from app.schemas.user import UserAuthSimpleResponse, UserLoginResponse

__all__ = [
    "AcademyCollectionResponse",
    "AcademyRatingsResponse",
    "AddonIpResponse",
    "AddonWinRateResponse",
    "HeroCollectionResponse",
    "UserAuthSimpleResponse",
    "UserLoginResponse",
]
