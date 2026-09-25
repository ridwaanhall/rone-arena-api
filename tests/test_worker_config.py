"""The Cloudflare Worker config must keep matching the repository layout."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _wrangler() -> dict:
    return json.loads((_ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))


def test_worker_entry_point_and_assets_exist() -> None:
    config = _wrangler()
    assert (_ROOT / config["main"]).is_file()
    assets = _ROOT / config["assets"]["directory"]
    assert (assets / "static" / "css" / "arena.css").is_file()
    assert (assets / "images" / "blog").is_dir()


def test_worker_requires_the_secrets_the_app_reads() -> None:
    config_source = (_ROOT / "src" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    required = set(_wrangler()["secrets"]["required"])
    assert required == {"SECRET_KEY", "RONE_DEV_ACCESS_KEY", "RONE_DEV_ACCESS_KEY_V2"}
    for name in required:
        assert f'env_str("{name}")' in config_source


def test_worker_vars_keep_the_service_fully_available() -> None:
    variables = _wrangler()["vars"]
    assert variables["IS_MAINTENANCE"] == "false"
    assert variables["IS_HIGH_TRAFFIC"] == "false"
    assert variables["DEBUG"] == "false"
