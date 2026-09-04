"""Tron provider stub."""

from __future__ import annotations

from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from app.providers.base import BlockchainProvider
from app.providers.canonical import CanonicalTransaction
from app.providers.demo import raise_not_implemented


class TronProvider(BlockchainProvider):
    """Tron provider stub."""

    chain_code = "tron"

    async def get_balance(self, address: str) -> Decimal:
        raise raise_not_implemented(self.chain_code)

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        raise raise_not_implemented(self.chain_code)

    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
    ) -> AsyncIterator[CanonicalTransaction]:
        raise raise_not_implemented(self.chain_code)
        yield  # pragma: no cover

    async def get_block_height(self) -> int:
        raise raise_not_implemented(self.chain_code)

    async def healthcheck(self) -> bool:
        return False


__all__ = ["TronProvider"]
