from __future__ import annotations

from pathlib import Path


def _find_public_dir() -> Path | None:
    """The web assets folder (`public/`) when it is on disk, else None.

    Locally and on FastAPI Cloud the app serves `public/` itself. On Cloudflare Workers
    the folder is uploaded as Static Assets and served before the app runs, so it is
    not part of the Python bundle and this returns None.
    """
    candidate = Path(__file__).resolve().parents[3] / "public"
    return candidate if candidate.is_dir() else None


PUBLIC_DIR = _find_public_dir()
