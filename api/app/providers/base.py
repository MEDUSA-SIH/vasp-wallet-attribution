"""Provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.providers.canonical import CanonicalTransaction


@dataclass(slots=True, frozen=True)
class TxQuery:
    """A bounded query for transaction history."""

    address: str
    start_time: Any = None  # datetime | None – kept loose to avoid circular imports
    end_time: Any = None
    limit: int = 100


class BlockchainProvider(ABC):
    """Abstract base class for every chain-specific provider."""

    chain_code: str  # e.g. "bitcoin", "ethereum"

    # -- required methods -----------------------------------------------------
    @abstractmethod
    async def get_balance(self, address: str) -> Decimal:
        """Return the native-asset balance of ``address``."""
        raise NotImplementedError

    @abstractmethod
    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        """Return canonical transactions touching ``address``."""
        raise NotImplementedError

    @abstractmethod
    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
    ) -> AsyncIterator[CanonicalTransaction]:
        """Yield canonical transactions for ``address`` as they are observed."""
        raise NotImplementedError  # pragma: no cover – async stub

    @abstractmethod
    async def get_block_height(self) -> int:
        """Return the current canonical block height of the chain."""
        raise NotImplementedError

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Return ``True`` if the provider can reach its upstream API."""
        raise NotImplementedError


class ProviderRegistry:
    """Holds active providers keyed by chain code."""

    def __init__(self) -> None:
        self._providers: dict[str, BlockchainProvider] = {}

    def register(self, provider: BlockchainProvider) -> None:
        self._providers[provider.chain_code] = provider

    def get(self, chain_code: str) -> BlockchainProvider:
        try:
            return self._providers[chain_code]
        except KeyError as exc:  # pragma: no cover – depends on runtime config
            raise KeyError(f"No provider registered for chain '{chain_code}'") from exc

    def available(self) -> list[str]:
        return sorted(self._providers.keys())


__all__ = [
    "BlockchainProvider",
    "ProviderRegistry",
    "TxQuery",
]
