"""Provider factory — builds the chain provider registry.

When ``DEMO_MODE`` is on, this creates a registry with a demo provider
for every supported chain (uses the local synthetic dataset, no API keys).
When ``DEMO_MODE`` is off, it registers placeholder providers that raise
an error until real chain integrations are added.

This is the single place the app uses to pick a provider at runtime.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.providers.base import BlockchainProvider, ProviderRegistry
from app.providers.bitcoin import BitcoinProvider
from app.providers.bnb import BnbProvider
from app.providers.demo import DemoBlockchainProvider
from app.providers.ethereum import EthereumProvider
from app.providers.polygon import PolygonProvider
from app.providers.solana import SolanaProvider
from app.providers.tron import TronProvider

# Single source of truth for the chain codes the registry knows about.
SUPPORTED_CHAIN_CODES: tuple[str, ...] = (
    "bitcoin",
    "ethereum",
    "tron",
    "bnb",
    "solana",
    "polygon",
)


def build_default_provider_registry(settings: Settings | None = None) -> ProviderRegistry:
    """Return the active :class:`ProviderRegistry`.

    Honours ``settings.demo_mode``:
      - ``True``  → register one ``DemoBlockchainProvider`` per chain.
      - ``False`` → register the per-chain stubs (raise on use).

    The function is pure: calling it twice returns two distinct
    registries, but the underlying demo dataset is shared (singleton).
    """
    settings = settings or get_settings()
    registry = ProviderRegistry()

    if settings.demo_mode:
        for code in SUPPORTED_CHAIN_CODES:
            registry.register(DemoBlockchainProvider(chain_code=code))
    else:
        # Per-chain stubs – one per supported chain code.
        _stub_map: dict[str, type[BlockchainProvider]] = {
            "bitcoin": BitcoinProvider,
            "ethereum": EthereumProvider,
            "tron": TronProvider,
            "bnb": BnbProvider,
            "solana": SolanaProvider,
            "polygon": PolygonProvider,
        }
        for _code, cls in _stub_map.items():
            registry.register(cls())

    return registry


__all__ = [
    "SUPPORTED_CHAIN_CODES",
    "build_default_provider_registry",
]
