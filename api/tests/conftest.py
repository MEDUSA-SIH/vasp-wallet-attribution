"""Shared pytest fixtures (Phase 14)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make the `app` package importable when tests run from any cwd.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Default test env so Settings() can be built without a real .env file.
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("REDIS_HOST", "localhost")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
