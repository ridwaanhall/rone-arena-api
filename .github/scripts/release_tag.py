"""Decide whether a push to main should create a release tag.

Used by .github/workflows/release-tag.yml. A tag named after the project version
(`1.2.1`, no `v`) is created when the version in pyproject.toml is higher than it was
before the push and no tag of that name exists yet. The old `4.x` tags from before the
rename are never compared, only the version before and after this push.

Prints the decision and, when run by GitHub Actions, writes `tag=<version>` (empty for
no tag) to $GITHUB_OUTPUT.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_NO_COMMIT = "0" * 40


def parse(version: str) -> tuple[int, int, int] | None:
    found = _SEMVER.match(version)
    return (int(found[1]), int(found[2]), int(found[3])) if found else None


def decide(old: str | None, new: str, tag_exists: bool) -> tuple[bool, str]:
    """Whether to tag ``new`` and why (or why not)."""
    new_key = parse(new)
    if new_key is None:
        return False, f"Version {new!r} is not X.Y.Z, so no tag is made."
    if old is None:
        return False, "No earlier version to compare with (first push, or the previous commit is gone), so no tag is made."
    old_key = parse(old)
    if old_key is None:
        return False, f"The earlier version {old!r} is not X.Y.Z, so no tag is made."
    if new_key <= old_key:
        return False, f"Version {new} is not higher than {old}, so no tag is made."
    if tag_exists:
        return False, f"Tag {new} already exists, so no tag is made."
    return True, f"Version went from {old} to {new} and tag {new} does not exist: creating it."


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def _version_of(pyproject: str) -> str:
    return str(tomllib.loads(pyproject)["project"]["version"])


def previous_version(before: str) -> str | None:
    """The version in pyproject.toml at the commit before the push, if that commit is available."""
    if not before or before == _NO_COMMIT:
        return None
    try:
        return _version_of(_git("show", f"{before}:pyproject.toml"))
    except (subprocess.CalledProcessError, KeyError, tomllib.TOMLDecodeError):
        return None


def tag_exists(name: str) -> bool:
    return subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{name}"], capture_output=True).returncode == 0


def main() -> int:
    with open("pyproject.toml", encoding="utf-8") as handle:
        new = _version_of(handle.read())
    create, reason = decide(previous_version(os.environ.get("BEFORE", "")), new, tag_exists(new))
    print(reason)
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"tag={new if create else ''}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
