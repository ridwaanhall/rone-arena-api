from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import app

client = TestClient(app)
SRC = Path(__file__).parent.parent / "src"


def test_app_starts_without_the_two_access_keys() -> None:
    # A pull request preview only has SECRET_KEY; importing the app must not fail without the others.
    env = {key: value for key, value in os.environ.items() if not key.startswith("RONE_DEV_ACCESS_KEY")}
    env["SECRET_KEY"] = os.environ.get("SECRET_KEY", "x")
    code = (
        "import dotenv; dotenv.load_dotenv = lambda *a, **k: False\n"
        "import sys; sys.path.insert(0, %r)\n"
        "from app import main; from app.core import config\n"
        "print(repr(config.RONE_DEV_ACCESS_KEY), repr(config.RONE_DEV_ACCESS_KEY_V2))"
    ) % str(SRC)
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)

    assert done.returncode == 0, done.stderr[-800:]
    assert done.stdout.strip() == "'' ''"


def test_secret_key_is_still_required() -> None:
    env = {key: value for key, value in os.environ.items() if key != "SECRET_KEY" and not key.startswith("RONE_DEV_ACCESS_KEY")}
    code = "import dotenv; dotenv.load_dotenv = lambda *a, **k: False\nimport sys; sys.path.insert(0, %r)\nfrom app import main" % str(SRC)
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)

    assert done.returncode != 0
    assert "SECRET_KEY" in done.stderr


@pytest.mark.parametrize(
    ("path", "name", "attribute"),
    [
        ("/api/heroes/rank", "RONE_DEV_ACCESS_KEY", "RONE_DEV_ACCESS_KEY"),
        ("/api/academy/roles", "RONE_DEV_ACCESS_KEY", "RONE_DEV_ACCESS_KEY"),
        ("/api/academy/heroes/ratings", "RONE_DEV_ACCESS_KEY_V2", "RONE_DEV_ACCESS_KEY_V2"),
    ],
)
def test_endpoints_say_which_key_is_missing(monkeypatch, path: str, name: str, attribute: str) -> None:
    monkeypatch.setattr(config, attribute, "")

    response = client.get(path)
    body = response.json()

    assert response.status_code == 503
    assert body["code"] == "NOT_CONFIGURED"
    assert name in body["message"]


def test_a_configured_key_is_returned_unchanged() -> None:
    assert config.require_access_key("https://upstream.test/", "RONE_DEV_ACCESS_KEY") == "https://upstream.test/"
