"""Coverage for the two service-restriction flags.

app.core.config reads the environment once at import, so each state has to be
exercised in a fresh interpreter rather than by monkeypatching the constants
(the routers and middleware capture them at import time too).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_PROBE = """
import json, sys
sys.path.insert(0, %r)
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
home = client.get("/")
api = client.get("/api/heroes")
try:
    body = api.json()
except ValueError:
    body = {}

print(json.dumps({
    "home_status": home.status_code,
    "maintenance_panel": "Under Maintenance" in home.text,
    "high_traffic_panel": "503 Service Unavailable" in home.text,
    "api_status": api.status_code,
    "message": body.get("message", ""),
    "alternative": (body.get("details") or {}).get("alternative_endpoint"),
}))
""" % str(_REPO_ROOT)


def _probe(*, maintenance: bool, high_traffic: bool) -> dict:
    env = dict(os.environ)
    env["IS_MAINTENANCE"] = str(maintenance)
    env["IS_HIGH_TRAFFIC"] = str(high_traffic)
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_maintenance_shows_maintenance_page_and_offers_no_alternative() -> None:
    state = _probe(maintenance=True, high_traffic=False)

    assert state["home_status"] == 503
    assert state["maintenance_panel"] is True
    assert state["api_status"] == 503
    assert "under maintenance" in state["message"].lower()
    # There is nowhere to fail over to while the service itself is down.
    assert state["alternative"] is None


def test_high_traffic_points_callers_at_the_alternative_host() -> None:
    state = _probe(maintenance=False, high_traffic=True)

    assert state["home_status"] == 503
    assert state["high_traffic_panel"] is True
    assert state["maintenance_panel"] is False
    assert state["api_status"] == 503
    assert "high traffic" in state["message"].lower()
    assert state["alternative"]


def test_maintenance_takes_precedence_over_high_traffic() -> None:
    state = _probe(maintenance=True, high_traffic=True)

    assert state["maintenance_panel"] is True
    assert "under maintenance" in state["message"].lower()
    assert state["alternative"] is None


def test_service_is_fully_operational_when_neither_flag_is_set() -> None:
    state = _probe(maintenance=False, high_traffic=False)

    assert state["home_status"] == 200
    assert state["maintenance_panel"] is False
    assert state["high_traffic_panel"] is False
    assert state["api_status"] == 200
