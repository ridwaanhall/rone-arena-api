from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / ".github" / "scripts" / "release_tag.py"
WORKFLOW = ROOT / ".github" / "workflows" / "release-tag.yml"

_spec = importlib.util.spec_from_file_location("release_tag", SCRIPT)
assert _spec is not None and _spec.loader is not None
release_tag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release_tag)


@pytest.mark.parametrize(
    ("old", "new", "exists", "create"),
    [
        ("1.2.0", "1.2.1", False, True),
        ("1.2.9", "1.3.0", False, True),
        ("1.9.9", "2.0.0", False, True),
        ("1.2.9", "1.2.10", False, True),  # numeric, not alphabetical: 10 > 9
        ("1.2.1", "1.2.1", False, False),  # unchanged
        ("1.2.1", "1.2.0", False, False),  # lowered
        ("1.2.0", "1.2.1", True, False),  # tag already there
        (None, "1.2.1", False, False),  # nothing to compare with
        ("1.2.0", "1.2.1rc1", False, False),  # not X.Y.Z
        ("weird", "1.2.1", False, False),
    ],
)
def test_decide(old: str | None, new: str, exists: bool, create: bool) -> None:
    decided, reason = release_tag.decide(old, new, exists)

    assert decided is create
    assert reason


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def _commit_version(repo: Path, version: str) -> str:
    (repo / "pyproject.toml").write_text(f'[project]\nname = "demo"\nversion = "{version}"\n', encoding="utf-8")
    _git(repo, "add", "pyproject.toml")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", f"v{version}")
    return _git(repo, "rev-parse", "HEAD")


def _run(repo: Path, before: str, tmp_path: Path) -> str:
    """Run the script as the workflow does and return the `tag=` output."""
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    env = {**os.environ, "BEFORE": before, "GITHUB_OUTPUT": str(output)}
    subprocess.run([sys.executable, str(SCRIPT)], cwd=repo, env=env, check=True, capture_output=True)
    return output.read_text(encoding="utf-8").strip()


def test_script_tags_only_a_version_raised_by_the_push(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    first = _commit_version(repo, "1.2.0")

    assert _run(repo, first, tmp_path) == "tag="  # same version before and after
    assert _run(repo, "0" * 40, tmp_path) == "tag="  # first push: nothing to compare with
    assert _run(repo, "f" * 40, tmp_path) == "tag="  # previous commit not available

    _commit_version(repo, "1.2.1")
    assert _run(repo, first, tmp_path) == "tag=1.2.1"

    _git(repo, "tag", "1.2.1")
    assert _run(repo, first, tmp_path) == "tag="  # tag already exists

    second = _git(repo, "rev-parse", "HEAD")  # a later push that raises the version again
    _commit_version(repo, "1.3.0")
    assert _run(repo, second, tmp_path) == "tag=1.3.0"


def test_workflow_runs_only_for_pushes_to_main() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "branches: [main]" in text
    assert "if: github.ref == 'refs/heads/main'" in text
    assert "pull_request" not in text
    assert "workflow_dispatch" not in text
    assert "contents: write" in text
    assert "release_tag.py" in text and SCRIPT.exists()
