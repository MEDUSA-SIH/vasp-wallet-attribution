"""Canonical transaction schema (Phase 9).

All providers normalise their chain-specific transaction shape into the
:class:`CanonicalTransaction` before downstream code touches it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(slots=True, frozen=True)
class CanonicalTransaction:
    """A chain-agnostic transaction record (Phase 9)."""

    chain: str
    tx_hash: str
    block_height: int | None
    block_timestamp: datetime | None
    from_address: str | None
    to_address: str | None
    asset_symbol: str
    amount: Decimal
    fee: Decimal
    success: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


__all__ = ["CanonicalTransaction"]
