"""Stages E & F – proximity + confidence scoring (Phase 10)."""
from __future__ import annotations

from typing import Any


def compute_proximity(nodes: list[Any], seed_addresses: list[str]) -> list[Any]:
    """Score each node by how directly it connects to a seed wallet."""
    return nodes


def compute_confidence(proximity: list[Any], evidence: list[Any]) -> list[Any]:
    """Combine the weighted proximity/typology/temporal/behavioral scores.

    Weights come from :class:`app.config.Settings`.  A later stage will
    use ``app.config.Settings.confidence_weight_*`` to compute the final
    ``[0, 1]`` confidence value.
    """
    return proximity


__all__ = ["compute_proximity", "compute_confidence"]