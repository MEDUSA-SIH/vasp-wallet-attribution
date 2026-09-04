"""Seed the offline demo dataset (Phase 21/22).

A real implementation will:
    1. read CSVs from data/synthetic/,
    2. normalise them into CanonicalTransaction rows,
    3. push them into the demo provider,
    4. persist chains/wallets/tx in the DB.

Stage 0 ships a no-op so the make-target exists.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make `app` importable when run as `python -m scripts.seed_demo_data`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402


async def main() -> None:
    settings = get_settings()
    configure_logging()
    log = get_logger("seed_demo_data")
    log.info("seed_demo_data.start", demo_mode=settings.demo_mode)
    if not settings.demo_mode:
        log.warning("seed_demo_mode_disabled")
    # Real seeding logic arrives in a later stage.
    log.info("seed_demo_data.done")


if __name__ == "__main__":
    asyncio.run(main())