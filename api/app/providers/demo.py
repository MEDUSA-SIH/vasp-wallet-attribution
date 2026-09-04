"""Offline demo provider (Phase 21/22).

Returns empty data and clearly marked stubs. A later stage will plug in a
synthetic dataset (see ``scripts/seed_demo_data.py``).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from app.core.exceptions import ProviderError
from app.providers.base import BlockchainProvider
from app.providers.canonical import CanonicalTransaction


class DemoBlockchainProvider(BlockchainProvider):
    """Returns empty results. Real implementations will load synthetic data."""

    chain_code = "demo"

    def __init__(self) -> None:
        self._loaded: list[CanonicalTransaction] = []

    async def get_balance(self, address: str) -> Decimal:
        return Decimal("0")

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        # Until synthetic seed data is wired up we return the in-memory list.
        return list(self._loaded)[:limit]

    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
    ) -> AsyncIterator[CanonicalTransaction]:
        for tx in self._loaded:
            yield tx

    async def get_block_height(self) -> int:
        return 0

    async def healthcheck(self) -> bool:
        return True

    def load_synthetic(self, transactions: list[CanonicalTransaction]) -> None:
        """Inject a synthetic dataset (Phase 21/22)."""
        self._loaded = list(transactions)


__all__ = ["DemoBlockchainProvider"]


def raise_not_implemented(provider: str) -> ProviderError:
    """Helper kept here to avoid importing ProviderError in every provider."""
    return ProviderError(f"Provider '{provider}' is not implemented yet (Stage 0).")