"""A `build` command that does nothing, so `uv run build` succeeds.

The Cloudflare Workers Builds job for non-production branches (pull requests) runs
`uv run build` before it uploads a preview. There is nothing to build here: the Worker is
packaged by `uv run pywrangler deploy`, and `public/` is uploaded as it is. Without a
`build` command that step fails with "Failed to spawn: build" and the PR check goes red.
"""
from __future__ import annotations


def main() -> None:
    print("Nothing to build: the Worker is packaged by pywrangler at deploy time.")
