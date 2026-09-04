"""Stage A – seed discovery (Phase 10 Stage A)."""
from __future__ import annotations

from typing import Any
from uuid import UUID


async def run_discovery(case_id: UUID, seed_addresses: list[str]) -> list[Any]:
    """Resolve the seed addresses to graph nodes.

    Currently a no-op that returns an empty list. A later stage will:
      - check the relational store (app.db.models.Wallet),
      - match against known cluster seeds,
      - return a list of GraphNode seeds.
    """
    return []


__all__ = ["run_discovery"]