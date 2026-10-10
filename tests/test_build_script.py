from __future__ import annotations

import tomllib
from pathlib import Path

from app import build


def test_build_script_is_registered_and_does_nothing(capsys) -> None:
    # The Workers Builds job for pull request branches runs `uv run build`; it must exist and succeed.
    scripts = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]

    assert scripts["build"] == "app.build:main"
    assert build.main() is None
    assert "Nothing to build" in capsys.readouterr().out
