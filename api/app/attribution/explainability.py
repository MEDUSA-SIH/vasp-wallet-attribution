"""Stage H – explainability (Phase 10 Stage H)."""
from __future__ import annotations

from typing import Any


def explain(rankings: list[Any]) -> dict[str, Any]:
    """Produce a per-wallet rationale that the report will render."""
    return {"format": "stub", "items": list(rankings)}


__all__ = ["explain"]