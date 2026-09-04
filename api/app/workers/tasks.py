"""Background task placeholders (Phase 23)."""

from __future__ import annotations

import asyncio


async def ping_task() -> str:
    """A trivial async task used as a smoke test."""
    await asyncio.sleep(0)
    return "pong"


async def enqueue_demo_seed() -> str:
    """Stub task – a real implementation will load the synthetic dataset."""
    return "queued"


__all__ = ["ping_task", "enqueue_demo_seed"]
