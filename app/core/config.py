from __future__ import annotations

import os
from typing import Callable, TypeVar

from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T")


def _env_cast(key: str, caster: Callable[[str], T], default: T | None = None) -> T:
    value = os.getenv(key)
    if value is None:
        if default is None:
            raise RuntimeError(f"Missing required environment variable: {key}")
        return default
    try:
        return caster(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid value for environment variable {key}: {value!r}") from exc


def _to_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("Expected boolean string")


def env_str(key: str, default: str | None = None) -> str:
    return _env_cast(key, str, default)


def env_bool(key: str, default: bool) -> bool:
    return _env_cast(key, _to_bool, default)


def env_int(key: str, default: int) -> int:
    return _env_cast(key, int, default)


# =========================
# Debugging
# =========================
DEBUG: bool = env_bool("DEBUG", default=False)

# =========================
# Availability Settings
# =========================
PROJECT_VERSION: str = env_str("PROJECT_VERSION", default="1.0.0")

# Two independent reasons the service may be restricted.
#   IS_MAINTENANCE  - the service is being worked on; no alternative host to
#                     send callers to, and the home page explains the outage.
#   IS_HIGH_TRAFFIC - this host is shedding load; callers are pointed at the
#                     high-volume host instead.
# Maintenance wins when both are set, since it is the more fundamental state.
IS_MAINTENANCE: bool = env_bool("IS_MAINTENANCE", default=True)
IS_HIGH_TRAFFIC: bool = env_bool("IS_HIGH_TRAFFIC", default=False)

# Derived: the service only serves normally when neither restriction applies.
IS_AVAILABLE: bool = not (IS_MAINTENANCE or IS_HIGH_TRAFFIC)

# Which entry of API_STATUS_MESSAGES / SUPPORT_STATUS_MESSAGES applies.
SERVICE_STATUS_KEY: str = (
    "maintenance" if IS_MAINTENANCE else "limited" if IS_HIGH_TRAFFIC else "available"
)

DATE_AVAILABLE: str = env_str("DATE_AVAILABLE", default="Jul 30, 2026")
ALTERNATIVE_ENDPOINT_URL: str = env_str(
    "ALTERNATIVE_ENDPOINT_URL",
    default="https://arena-hv.fastapicloud.dev",
)

# =========================
# Support & Donation Details
# =========================
SUPPORT_DETAILS: dict[str, str] = {
    "support_message": "You can support us by donating from $5 USD (target: $500 USD) to help enhance API performance and handle high request volumes.",
    "github_sponsors": "https://github.com/sponsors/ridwaanhall",
    "buymeacoffee": "https://www.buymeacoffee.com/ridwaanhall",
    "donation_link": "https://github.com/sponsors/ridwaanhall",
    "id_zone_ori": "original server: 688700997 (8742)",
    "id_zone_adv": "advanced server: 1149309666 (57060)",
}

DONATION_MIN: int = env_int("DONATION_MIN", default=5)
DONATION_NOW: int = env_int("DONATION_NOW", default=12)
DONATION_TARGET: int = env_int("DONATION_TARGET", default=500)
DONATION_CURRENCY: str = env_str("DONATION_CURRENCY", default="USD")

# =========================
# API Status Messages
# =========================
API_STATUS_MESSAGES: dict[str, dict[str, str | list[str]]] = {
    "maintenance": {
        "status": "maintenance",
        "message": (
            "Service is temporarily unavailable while the API is under maintenance. "
            "Endpoints will return once the work is complete."
        ),
        "available_endpoints": ["/"],
    },
    "limited": {
        "status": "limited",
        "message": "Service is temporarily unavailable due to high traffic. Please use the alternative endpoint.",
        "available_endpoints": ["/"],
        "alternative_endpoint": ALTERNATIVE_ENDPOINT_URL,
    },
    "available": {
        "status": "available",
        "message": "All API endpoints are fully operational.",
        "available_endpoints": ["All endpoints"],
    },
}

SUPPORT_STATUS_MESSAGES: dict[str, str] = {
    "maintenance": env_str(
        "SUPPORT_MESSAGE_MAINTENANCE",
        default="API is under maintenance. Donations help cover hosting and ongoing development.",
    ),
    "limited": env_str(
        "SUPPORT_MESSAGE_LIMITED",
        default="API is currently in maintenance mode. Donations help cover hosting and performance scaling.",
    ),
    "available": env_str(
        "SUPPORT_MESSAGE_AVAILABLE",
        default="All API endpoints are fully operational. Donations help cover hosting and performance scaling.",
    ),
}

MAINTENANCE_INFO_URL: str = env_str(
    "MAINTENANCE_INFO_URL",
    default="https://ridwaanhall.com/blog/how-usage-monitoring-sustains-mlbb-stats-and-api-pddikti/",
)

# =========================
# URLs & Endpoints & SEO
# =========================
BASE_URL: str = env_str("BASE_URL", default="https://arena.rone.dev/")

API_BASE_URL: str = env_str("API_BASE_URL", default=f"{BASE_URL}api/")
DOCS_BASE_URL: str = env_str("DOCS_BASE_URL", default=f"{BASE_URL}docs")

# Production URLs for different request volumes
PROD_URL_STANDARD: str = (
    "http://127.0.0.1:8000/api/"
    if DEBUG
    else env_str("PROD_URL_STANDARD", default="https://arena.rone.dev/api/")
)

PROD_URL_HIGH_VOLUME: str = (
    "http://127.0.0.1:8000/api/"
    if DEBUG
    else env_str("PROD_URL_HIGH_VOLUME", default="https://arena-hv.fastapicloud.dev/api/")
)

# Backward compatibility
PROD_URL: str = PROD_URL_STANDARD

# Host that serves the high-volume deployment; analytics is only enabled there.
# Empty in DEBUG so local runs never emit analytics hits.
ANALYTICS_HOST: str = env_str("ANALYTICS_HOST", default="" if DEBUG else "arena-hv.fastapicloud.dev")

LIVECHAT_LINK: str = env_str("LIVECHAT_LINK", default="https://ridwaanhall.com/guestbook/")
CONTACT_FORM_LINK: str = env_str("CONTACT_FORM_LINK", default="https://ridwaanhall.com/contact/")

# =========================
# Security & Access Keys
# =========================
SECRET_KEY: str = env_str("SECRET_KEY")
RONE_DEV_ACCESS_KEY: str = env_str("RONE_DEV_ACCESS_KEY")
RONE_DEV_ACCESS_KEY_V2: str = env_str("RONE_DEV_ACCESS_KEY_V2")
