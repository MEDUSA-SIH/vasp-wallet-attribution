"""Shared attribution types (Phase 10 + Phase 3.3).

These dataclasses flow through Stages A→H. They are intentionally
**plain dataclasses** (not Pydantic models) — internal to the engine.
The FastAPI layer translates them into Pydantic schemas.

Phase 3.3 invariant: ``proximity_rank`` and ``confidence_score`` are
two independent numbers. The engine NEVER blends them into a single
"final score" for ranking (Stage G sorts by ``proximity_rank`` and
exposes ``confidence_score`` alongside).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class EvidenceTier(IntEnum):
    """Phase 5 evidence tiers (1 = strongest, 4 = weakest)."""

    TIER_1_DEPOSIT_LABEL = 1       # Direct VASP deposit tag from exchange
    TIER_2_HOT_WALLET_LABEL = 2    # Tagged hot-wallet cluster
    TIER_3_BEHAVIORAL = 3          # Consolidation pattern, no exchange label
    TIER_4_TOPOLOGICAL = 4         # Heuristic only (multi-hop proximity)
    TIER_NONE = 99                 # No credible evidence (insufficient_evidence)


@dataclass(slots=True, frozen=True)
class HopEdge:
    """A single hop along a candidate path."""

    tx_hash: str
    chain: str
    from_address: str
    to_address: str
    timestamp: str | None  # ISO 8601
    amount: float
    asset_symbol: str


@dataclass(slots=True, frozen=True)
class EvidenceItem:
    """A single piece of evidence supporting (or weakening) a candidate."""

    code: str            # e.g. "vasp_label", "mixer_stop", "bridge_hop"
    weight: float        # 0.0–1.0 contribution
    detail: str          # plain-language note


@dataclass(slots=True)
class Candidate:
    """A candidate path from the suspect to a terminal address.

    Stage A produces one of these per terminal reached by the BFS.
    """

    suspect_address: str
    terminal_address: str
    terminal_role: str  # "vasp" | "mixer" | "bridge" | "hub" | "dead_end" | "intermediary"
    terminal_label: str | None = None
    chain: str = "ethereum"
    hops: int = 0
    path: list[str] = field(default_factory=list)
    edges: list[HopEdge] = field(default_factory=list)
    crosses_bridge: bool = False
    bridge_id: str | None = None
    hits_mixer: bool = False
    mixer_id: str | None = None
    vasp_id: str | None = None
    total_amount: float = 0.0
    first_seen_at: str | None = None
    last_seen_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "suspect_address": self.suspect_address,
            "terminal_address": self.terminal_address,
            "terminal_role": self.terminal_role,
            "terminal_label": self.terminal_label,
            "chain": self.chain,
            "hops": self.hops,
            "path": list(self.path),
            "edges": [
                {
                    "tx_hash": e.tx_hash,
                    "chain": e.chain,
                    "from_address": e.from_address,
                    "to_address": e.to_address,
                    "timestamp": e.timestamp,
                    "amount": e.amount,
                    "asset_symbol": e.asset_symbol,
                }
                for e in self.edges
            ],
            "crosses_bridge": self.crosses_bridge,
            "bridge_id": self.bridge_id,
            "hits_mixer": self.hits_mixer,
            "mixer_id": self.mixer_id,
            "vasp_id": self.vasp_id,
            "total_amount": self.total_amount,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
        }


@dataclass(slots=True)
class ScoredCandidate:
    """A candidate with both proximity and confidence scored (Phase 3.3).

    ``proximity_rank`` is a weighted-graph distance score (lower = closer).
    ``confidence_score`` is a 0..100 banded confidence.
    They are exposed independently and never blended.
    """

    candidate: Candidate
    evidence: list[EvidenceItem] = field(default_factory=list)
    proximity_rank: float = 0.0
    proximity_breakdown: dict[str, float] = field(default_factory=dict)
    confidence_score: float = 0.0
    confidence_band: str = "low"      # "low" | "medium" | "high"
    evidence_tier: EvidenceTier = EvidenceTier.TIER_NONE
    explanation: str = ""            # Stage H narrative

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.as_dict(),
            "evidence": [
                {"code": e.code, "weight": e.weight, "detail": e.detail}
                for e in self.evidence
            ],
            "proximity_rank": self.proximity_rank,
            "proximity_breakdown": self.proximity_breakdown,
            "confidence_score": self.confidence_score,
            "confidence_band": self.confidence_band,
            "evidence_tier": int(self.evidence_tier),
            "evidence_tier_label": _tier_label(self.evidence_tier),
            "explanation": self.explanation,
        }


def _tier_label(tier: EvidenceTier) -> str:
    return {
        EvidenceTier.TIER_1_DEPOSIT_LABEL:   "Tier 1 — Direct VASP deposit label",
        EvidenceTier.TIER_2_HOT_WALLET_LABEL: "Tier 2 — Tagged hot-wallet cluster",
        EvidenceTier.TIER_3_BEHAVIORAL:       "Tier 3 — Behavioral / consolidation only",
        EvidenceTier.TIER_4_TOPOLOGICAL:      "Tier 4 — Heuristic / topological only",
        EvidenceTier.TIER_NONE:               "Insufficient evidence",
    }.get(tier, "Unknown")


__all__ = [
    "EvidenceTier",
    "HopEdge",
    "EvidenceItem",
    "Candidate",
    "ScoredCandidate",
]