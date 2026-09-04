"""Blockchain providers (Phase 20).

Each provider implements the :class:`BlockchainProvider` protocol so the
attribution engine and orchestrators can treat them uniformly.  For now
all upstream providers raise ``NotImplementedError``; the
:class:`DemoBlockchainProvider` will gain a synthetic data backend later.
"""
from app.providers.base import BlockchainProvider, CanonicalTransaction, ProviderRegistry
from app.providers.bitcoin import BitcoinProvider
from app.providers.bnb import BnbProvider
from app.providers.canonical import CanonicalTransaction as CanonicalTransactionAlias
from app.providers.demo import DemoBlockchainProvider
from app.providers.ethereum import EthereumProvider
from app.providers.polygon import PolygonProvider
from app.providers.solana import SolanaProvider
from app.providers.tron import TronProvider

__all__ = [
    "BlockchainProvider",
    "CanonicalTransaction",
    "ProviderRegistry",
    "CanonicalTransactionAlias",
    "DemoBlockchainProvider",
    "BitcoinProvider",
    "EthereumProvider",
    "TronProvider",
    "BnbProvider",
    "SolanaProvider",
    "PolygonProvider",
]