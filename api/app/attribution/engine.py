"""Attribution engine orchestrator (Phase 10).

Eight-stage pipeline:

    A  discovery.py        Forward BFS over the chain graph
    B  traversal.py        Path reconstruction
    C  filtering.py        Noise / dust / hub filtering
    D  evidence.py         Evidence consolidation
    E  scoring.py          Proximity rank (weighted graph distance)
    F  scoring.py          Confidence score (equal-weight components)
    G  ranking.py          Sort by proximity_rank; pick outcome
    H  explainability.py   Plain-language narrative per candidate

The :class:`AttributionEngine` is the only public entry point. Sub-modules
are NOT considered public — consumers must use the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.attribution.discovery import run_discovery
from app.attribution.evidence import collect_evidence
from app.attribution.explainability import explain
from app.attribution.filtering import DegreeLookup, apply_filters
from app.attribution.ranking import classify_outcome, rank
from app.attribution.scoring import compute_confidence, compute_proximity
from app.attribution.traversal import reconstruct
from app.attribution.types import ScoredCandidate
from app.providers.base import ProviderRegistry


@dataclass(slots=True)
class AttributionResult:
    """Final output of an attribution run (Phase 10)."""

    case_id: UUID | None
    suspect_address: str
    chain: str
    outcome: str
    insufficient_evidence: bool
    candidates: list[ScoredCandidate]
    explanations: dict[str, str] = field(default_factory=dict)


class AttributionEngine:
    """Drives the eight-stage attribution pipeline (Phase 10)."""

    def __init__(
        self,
        *,
        max_hops: int = 5,
        max_candidates: int = 64,
    ) -> None:
        self.max_hops = max_hops
        self.max_candidates = max_candidates

    async def run(
        self,
        suspect_address: str,
        *,
        chain: str,
        registry: ProviderRegistry,
        case_id: UUID | None = None,
        degree_lookup: DegreeLookup | None = None,
    ) -> AttributionResult:
        """Execute stages A→H and return a structured result."""
        # Stage A — discovery.
        raw_candidates = await run_discovery(
            suspect_address,
            registry=registry,
            chain=chain,
            max_hops=self.max_hops,
            max_candidates=self.max_candidates,
            degree_lookup=degree_lookup,
        )
        # Stage B — path reconstruction.
        scored = reconstruct(raw_candidates)
        # Stage C — filtering.
        scored = apply_filters(scored, degree_lookup=degree_lookup)
        # Stage D — evidence collection.
        scored = collect_evidence(scored)
        # Stage E — proximity rank.
        scored = compute_proximity(scored)
        # Stage F — confidence score.
        scored = compute_confidence(scored)
        # Stage G — ranking + outcome.
        ranked = rank(scored)
        outcome, insufficient = classify_outcome(ranked)
        # Stage H — explainability.
        explanations = explain(ranked)
        return AttributionResult(
            case_id=case_id,
            suspect_address=suspect_address,
            chain=chain,
            outcome=outcome,
            insufficient_evidence=insufficient,
            candidates=ranked,
            explanations=explanations,
        )


__all__ = ["AttributionEngine", "AttributionResult"]
