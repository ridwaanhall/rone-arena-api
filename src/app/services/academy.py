from __future__ import annotations

from typing import Any

from app.core.config import RONE_DEV_ACCESS_KEY_V2
from app.core.http import UpstreamHeaderBuilder, request_json
from app.core.security import BasePathProvider
from app.services.source import post_source
from app.utils.client_ip import get_bound_client_ip

# Upstream source IDs under the academy base path.
ACADEMY_POSTS = "2718124"  # form items: patch notes and community recommendations
ACADEMY_HEROES = "2766683"
ACADEMY_ROLES = "2740642"
ACADEMY_EQUIPMENT = "2775075"
ACADEMY_EQUIPMENT_EXPANDED = "2713995"
ACADEMY_SPELLS = "2718122"
ACADEMY_EMBLEMS = "2718121"
ACADEMY_RANKS = "3210596"
ACADEMY_HERO_STATS = "2755183"
ACADEMY_WIN_RATE_TIMELINE = "2777027"
ACADEMY_BUILDS = "2776688"
ACADEMY_MATCHUPS = "2777391"  # counters (camp_type 0) and teammates (camp_type 1)
ACADEMY_TRENDS_BY_DAYS = {"7": "2755185", "15": "2755186", "30": "2755187"}

# Form and object IDs that scope ACADEMY_POSTS queries.
RECOMMENDED_FORM_ID = 2737553
PATCH_NOTES_FORM_ID = 2777742
POSTS_OBJECT_ID = 2675413


def fetch_academy_post(source_id: str, payload: dict[str, Any], lang: str) -> Any:
    return post_source(BasePathProvider.get_base_path_academy(), source_id, payload, lang)


def fetch_ratings(lang: str, subject: str | None = None) -> Any:
    """All hero ratings, or one rating subject when ``subject`` is given."""
    base_path = BasePathProvider.get_base_path_ratings()
    suffix = f"/{subject}" if subject is not None else "?offset=0"
    url = f"{RONE_DEV_ACCESS_KEY_V2}{base_path}{suffix}"
    headers = UpstreamHeaderBuilder.get_academy_header(lang, client_ip=get_bound_client_ip())
    return request_json(method="GET", url=url, headers=headers)
