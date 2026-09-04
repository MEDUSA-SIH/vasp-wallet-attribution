"""Stage D – evidence collection (Phase 10 Stage D)."""
from __future__ import annotations

from typing import Any


async def collect_evidence(nodes: list[Any]) -> list[Any]:
    """Collect evidence snippets (timestamps, amounts, counterparty tags).

    A later stage will assemble the evidence package that feeds the scoring
    modules and the final report.
    """
    return nodes


__all__ = ["collect_evidence"]