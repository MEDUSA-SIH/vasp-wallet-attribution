"""Attribution engine — main pipeline.

Runs 8 steps to go from a suspect wallet to a ranked list of VASPs:

    A  discovery        Find candidate wallets
    B  traversal        Rebuild full paths
    C  filtering        Remove noise
    D  evidence         Gather supporting details
    E  scoring          How close each candidate is
    F  scoring          How trustworthy each match is
    G  ranking          Sort and pick the outcome
    H  explainability   Plain-English explanation

Only :class:`app.attribution.engine.AttributionEngine` is public.
The step modules are internal — use the engine.
"""

from app.attribution.engine import AttributionEngine, AttributionResult
from app.attribution.types import (
    Candidate,
    EvidenceItem,
    EvidenceTier,
    HopEdge,
    ScoredCandidate,
)

__all__ = [
    "AttributionEngine",
    "AttributionResult",
    "Candidate",
    "EvidenceItem",
    "EvidenceTier",
    "HopEdge",
    "ScoredCandidate",
]
