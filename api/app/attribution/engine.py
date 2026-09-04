"""Attribution engine orchestrator (Phase 10).

This module wires together the eight stages (Discovery → Explainability).
It is intentionally a thin orchestration layer – real logic arrives once each
stage module ships.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.attribution.discovery import run_discovery
from app.attribution.evidence import collect_evidence
from app.attribution.explainability import explain
from app.attribution.filtering import apply_filters
from app.attribution.ranking import rank
from app.attribution.scoring import compute_confidence, compute_proximity
from app.attribution.traversal import traverse


@dataclass(slots=True)
class AttributionResult:
    """Final output of an attribution run (Phase 10)."""

    case_id: UUID
    rankings: list[Any]
    explanations: dict[str, Any]


class AttributionEngine:
    """Drives the eight-stage attribution pipeline (Phase 10)."""

    def __init__(self, *, max_hops: int = 5, per_chain_budget: int = 3) -> None:
        self.max_hops = max_hops
        self.per_chain_budget = per_chain_budget

    async def run(self, case_id: UUID, seed_addresses: list[str]) -> AttributionResult:
        """Execute stages A→H and return a structured result."""
        seed_nodes = await run_discovery(case_id, seed_addresses)
        traversed = await traverse(seed_nodes, max_hops=self.max_hops)
        filtered = await apply_filters(traversed)
        evidence = await collect_evidence(filtered)
        proximity = compute_proximity(filtered, seed_addresses)
        confidence = compute_confidence(proximity, evidence)
        rankings = rank(confidence)
        explanations = explain(rankings)
        return AttributionResult(
            case_id=case_id,
            rankings=rankings,
            explanations=explanations,
        )


async def run_attribution(
    case_id: UUID,
    seed_addresses: list[str],
    *,
    max_hops: int = 5,
) -> AttributionResult:
    """Convenience function (Phase 10)."""
    engine = AttributionEngine(max_hops=max_hops)
    return await engine.run(case_id, seed_addresses)


__all__ = ["AttributionEngine", "AttributionResult", "run_attribution"]