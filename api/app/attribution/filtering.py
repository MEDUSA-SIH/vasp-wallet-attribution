"""Stage C – filtering (Phase 10 Stage C)."""
from __future__ import annotations

from typing import Any


async def apply_filters(nodes: list[Any]) -> list[Any]:
    """Drop nodes that don't pass exchange-attribute filters.

    A later stage will read VASP tags, dust thresholds, mixers and other
    heuristics.
    """
    return nodes


__all__ = ["apply_filters"]