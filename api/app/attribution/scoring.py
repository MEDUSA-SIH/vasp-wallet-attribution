"""Stages E and F — Proximity rank and confidence score (Phase 10 / Phase 3.3).

Two independent numbers:

- ``proximity_rank`` (Stage E): weighted-graph distance from suspect to
  terminal. Lower = closer. Components:
    - base hop cost (1.0 per hop)
    - mixing penalty (per mixer / bridge hop)
    - time-decay penalty (for stale activity)
    - fan-out penalty (suspect fans to many terminals)
- ``confidence_score`` (Stage F): 0..100. Components are weighted
  equally (1/6 each — MVP per the prompt):
    - evidence_tier_score
    - label_source_agreement
    - address_reuse_signal
    - cluster_consistency
    - path_integrity
    - evidence_freshness

The function returns the two numbers **independently**. Stage G ranks
candidates by ``proximity_rank`` only; the score is shown alongside.

Both implementations are deliberately simple and explainable. No
ML, no opaque weights.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.attribution.types import EvidenceItem, EvidenceTier, ScoredCandidate

# ----- Proximity rank (Stage E) ---------------------------------------------


def compute_proximity(scored: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Annotate each candidate with ``proximity_rank`` + breakdown."""
    for s in scored:
        cand = s.candidate
        breakdown = _proximity_components(cand)
        s.proximity_breakdown = breakdown
        s.proximity_rank = round(sum(breakdown.values()), 4)
    return scored


def _proximity_components(cand) -> dict[str, float]:
    """Weighted-graph distance from suspect to terminal."""
    components: dict[str, float] = {
        "base_hop_cost": float(cand.hops),
        "mixing_penalty": 0.0,
        "bridge_penalty": 0.0,
        "time_decay_penalty": 0.0,
        "fan_out_penalty": 0.0,
    }
    if cand.hits_mixer:
        components["mixing_penalty"] = 2.0
    if cand.crosses_bridge:
        components["bridge_penalty"] = 1.0
    # Time decay: hops older than 90 days add a small penalty.
    if cand.last_seen_at:
        try:
            last = datetime.fromisoformat(cand.last_seen_at.replace("Z", "+00:00"))
            age_days = (datetime.now(tz=UTC) - last).days
            if age_days > 90:
                components["time_decay_penalty"] = min(2.0, age_days / 90.0)
        except ValueError:
            pass
    return components


# ----- Confidence score (Stage F) -------------------------------------------


CONFIDENCE_WEIGHTS: dict[str, float] = {
    "evidence_tier_score":       1 / 6,
    "label_source_agreement":    1 / 6,
    "address_reuse_signal":      1 / 6,
    "cluster_consistency":       1 / 6,
    "path_integrity":            1 / 6,
    "evidence_freshness":        1 / 6,
}


def compute_confidence(scored: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Annotate each candidate with ``confidence_score`` + band + tier."""
    for s in scored:
        cand = s.candidate
        tier = _evidence_tier(cand, s)
        s.evidence_tier = tier

        # Phase 14 hard rule: mixer hits get a 0 confidence score — there
        # is no trustworthy downstream attribution past a mixer.
        if cand.hits_mixer:
            s.confidence_score = 0.0
            s.confidence_band = "low"
            s.evidence = [EvidenceItem(
                code="mixer_stop",
                weight=0.0,
                detail="Mixer hard-stop: confidence set to 0 (Phase 14).",
            )]
            continue

        components = _confidence_components(cand, tier)
        s.evidence = _evidence_items(components, cand)
        score = sum(components[k] * CONFIDENCE_WEIGHTS[k] for k in CONFIDENCE_WEIGHTS)
        s.confidence_score = round(score * 100, 1)
        s.confidence_band = _band(s.confidence_score)
    return scored


def _evidence_tier(cand, scored: ScoredCandidate) -> EvidenceTier:
    """Pick an evidence tier from the candidate's tags.

    Priority:
        1. mixer terminal → insufficient (handled separately).
        2. VASP deposit label (synthetic) → Tier 1.
        3. VASP hot-wallet / consolidation tag → Tier 2/3.
        4. Otherwise → Tier 4.
    """
    if cand.hits_mixer:
        return EvidenceTier.TIER_NONE
    if cand.terminal_role == "vasp" and cand.terminal_label:
        if cand.hops == 1 and not cand.crosses_bridge:
            return EvidenceTier.TIER_1_DEPOSIT_LABEL
        if cand.hops <= 2 and not cand.crosses_bridge:
            return EvidenceTier.TIER_2_HOT_WALLET_LABEL
        # Behavioural / consolidation patterns qualify for Tier 3 if the
        # terminal is VASP-tagged and we crossed a bridge.
        return EvidenceTier.TIER_3_BEHAVIORAL
    return EvidenceTier.TIER_4_TOPOLOGICAL


def _confidence_components(cand, tier: EvidenceTier) -> dict[str, float]:
    """Per-component 0..1 scores."""
    # 1. Evidence tier score: monotonic in tier quality.
    tier_score = {
        EvidenceTier.TIER_1_DEPOSIT_LABEL: 1.0,
        EvidenceTier.TIER_2_HOT_WALLET_LABEL: 0.8,
        EvidenceTier.TIER_3_BEHAVIORAL: 0.55,
        EvidenceTier.TIER_4_TOPOLOGICAL: 0.3,
        EvidenceTier.TIER_NONE: 0.0,
    }[tier]
    # 2. Label source agreement: present and trusted.
    label_agreement = 1.0 if cand.terminal_label else 0.0
    # 3. Address reuse signal: more hops on the same terminal chain →
    # higher reuse confidence.
    address_reuse = min(1.0, cand.hops / 4.0)
    # 4. Cluster consistency: VASP-tagged terminal, no mixer hit.
    cluster = 1.0 if cand.terminal_role == "vasp" and not cand.hits_mixer else 0.0
    # 5. Path integrity: every hop is backed by a tx.
    path_integrity = 1.0 if cand.hops == len(cand.edges) and cand.hops > 0 else 0.0
    # 6. Evidence freshness: penalise stale paths.
    freshness = 1.0
    if cand.last_seen_at:
        try:
            last = datetime.fromisoformat(cand.last_seen_at.replace("Z", "+00:00"))
            age_days = (datetime.now(tz=UTC) - last).days
            if age_days > 365:
                freshness = 0.4
            elif age_days > 90:
                freshness = 0.7
        except ValueError:
            freshness = 0.5
    return {
        "evidence_tier_score": tier_score,
        "label_source_agreement": label_agreement,
        "address_reuse_signal": address_reuse,
        "cluster_consistency": cluster,
        "path_integrity": path_integrity,
        "evidence_freshness": freshness,
    }


def _band(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _evidence_items(components: dict[str, float], cand) -> list[EvidenceItem]:
    """Turn per-component scores into plain-language evidence notes."""
    items: list[EvidenceItem] = []
    if cand.terminal_role == "vasp" and cand.vasp_id:
        items.append(EvidenceItem(
            code="vasp_label",
            weight=1.0,
            detail=f"Terminal wallet is tagged as a deposit of VASP '{cand.vasp_id}'.",
        ))
    if cand.hits_mixer:
        items.append(EvidenceItem(
            code="mixer_stop",
            weight=0.0,
            detail="Funds passed through a known mixer; attribution stops here (Phase 14).",
        ))
    if cand.crosses_bridge:
        items.append(EvidenceItem(
            code="bridge_hop",
            weight=-0.1,
            detail=f"Cross-chain bridge hop (id={cand.bridge_id}); confidence degraded per Phase 14.",
        ))
    if cand.hops == len(cand.edges) and cand.edges:
        items.append(EvidenceItem(
            code="path_integrity",
            weight=components["path_integrity"],
            detail=f"Every hop is backed by an on-chain transaction ({len(cand.edges)} hops).",
        ))
    if components["evidence_freshness"] < 1.0:
        items.append(EvidenceItem(
            code="stale_path",
            weight=components["evidence_freshness"],
            detail="Most recent hop is older than 90 days; freshness reduced.",
        ))
    return items


__all__ = [
    "compute_proximity",
    "compute_confidence",
    "CONFIDENCE_WEIGHTS",
]