"""Test environment setup.

app.core.config reads the environment at import time, so these must be set
before any test module imports the app. pytest imports conftest first, and
load_dotenv() does not override values already present in os.environ.

Without this the suite depends on the caller exporting the right flags, and
every request 503s when they forget.
"""

from __future__ import annotations

import os

# Exercise the fully-operational path unless a test overrides it.
os.environ.setdefault("IS_MAINTENANCE", "False")
os.environ.setdefault("IS_HIGH_TRAFFIC", "False")
