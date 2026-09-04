"""Bridge detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BridgeDetector:
    """Static catalog of known bridges."""

    name: str
    source_chains: tuple[str, ...]
    target_chains: tuple[str, ...]


_KNOWN_BRIDGES: tuple[BridgeDetector, ...] = (
    BridgeDetector(
        "wormhole",
        ("solana", "ethereum", "bnb", "polygon"),
        ("solana", "ethereum", "bnb", "polygon"),
    ),
    BridgeDetector("axelar", ("ethereum", "polygon", "bnb"), ("ethereum", "polygon", "bnb")),
    BridgeDetector(
        "layerzero",
        ("ethereum", "bnb", "polygon", "solana"),
        ("ethereum", "bnb", "polygon", "solana"),
    ),
)


def known_bridges() -> tuple[BridgeDetector, ...]:
    return _KNOWN_BRIDGES


def detect_bridge_hops(source_chain: str, target_chain: str) -> list[BridgeDetector]:
    """Return bridges that connect ``source_chain`` to ``target_chain``."""
    return [
        b
        for b in _KNOWN_BRIDGES
        if source_chain in b.source_chains and target_chain in b.target_chains
    ]


__all__ = ["BridgeDetector", "known_bridges", "detect_bridge_hops"]
