"""Attribution engine (Phase 10).

Eight-stage pipeline (see :mod:`app.attribution.engine`):

    A  discovery.py        Forward BFS over the chain graph
    B  traversal.py        Path reconstruction
    C  filtering.py        Noise / dust / hub filtering
    D  evidence.py         Evidence consolidation
    E  scoring.py          Proximity rank (weighted graph distance)
    F  scoring.py          Confidence score (equal-weight components)
    G  ranking.py          Sort by proximity_rank; pick outcome
    H  explainability.py   Plain-language narrative per candidate

Public surface (locked in :doc:`docs/contracts.md`):

    :class:`app.attribution.engine.AttributionEngine` — orchestrator.
    :class:`app.attribution.engine.AttributionResult` — output DTO.

Sub-modules (discovery, traversal, …) are NOT public. Consumers must
go through :class:`AttributionEngine`.
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
