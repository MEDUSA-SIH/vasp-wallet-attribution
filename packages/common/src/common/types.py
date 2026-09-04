"""Cross-cutting types used by both the API and other monorepo packages."""
from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple


class ChainCode(StrEnum):
    """Supported chain codes (Phase 20)."""

    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    TRON = "tron"
    BNB = "bnb"
    SOLANA = "solana"
    POLYGON = "polygon"
    DEMO = "demo"


class ConfidenceWeights(NamedTuple):
    """Default confidence weights (Phase 10)."""

    proximity: float = 0.30
    typology: float = 0.20
    temporal: float = 0.15
    behavioral: float = 0.20
    clustering: float = 0.15


class InvestigationSeed(NamedTuple):
    """A seed wallet for an investigation."""

    address: str
    chain: ChainCode
    label: str | None = None


__all__ = ["ChainCode", "ConfidenceWeights", "InvestigationSeed"]