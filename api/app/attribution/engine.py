"""Attribution engine — runs the full investigation pipeline.

This runs 8 simple steps in order:

    A  discovery        Find candidate wallets by walking the transaction graph
    B  traversal        Rebuild the full path for each candidate
    C  filtering        Remove noise (dust, duplicates, high-degree hubs)
    D  evidence         Gather supporting evidence for each candidate
    E  scoring          Compute proximity (how close the candidate is)
    F  scoring          Compute confidence (how trustworthy the match is)
    G  ranking          Sort by proximity and pick the outcome
    H  explainability   Write a plain-English explanation for each result

Use :class:`AttributionEngine` — it is the only public entry point.
The individual stage modules are internal details.
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
    """Final result of an attribution run."""

    case_id: UUID | None
    suspect_address: str
    chain: str
    outcome: str
    insufficient_evidence: bool
    candidates: list[ScoredCandidate]
    explanations: dict[str, str] = field(default_factory=dict)


class AttributionEngine:
    """Runs the 8-step attribution pipeline and returns a ranked result."""

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
        """Run all 8 stages and return the final result."""
        # Step A — search the graph for candidate wallets.
        raw_candidates = await run_discovery(
            suspect_address,
            registry=registry,
            chain=chain,
            max_hops=self.max_hops,
            max_candidates=self.max_candidates,
            degree_lookup=degree_lookup,
        )
        # Step B — rebuild the full path for each candidate.
        scored = reconstruct(raw_candidates)
        # Step C — filter out noise (dust, duplicates, hubs).
        scored = apply_filters(scored, degree_lookup=degree_lookup)
        # Step D — collect supporting evidence.
        scored = collect_evidence(scored)
        # Step E — score how close each candidate is.
        scored = compute_proximity(scored)
        # Step F — score how confident we are in each candidate.
        scored = compute_confidence(scored)
        # Step G — sort by proximity and decide the outcome.
        ranked = rank(scored)
        outcome, insufficient = classify_outcome(ranked)
        # Step H — write a plain-English explanation.
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
