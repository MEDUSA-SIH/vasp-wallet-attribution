"""Stage H — Explainability (Phase 10).

Produce a human-readable narrative per candidate. The narrative
follows a fixed template so investigators see consistent phrasing,
while remaining specific to each candidate's evidence.

The narrative NEVER uses the words "guaranteed", "definitely", or any
absolute phrasing — language is calibrated to the evidence tier and
the confidence band.
"""

from __future__ import annotations

from app.attribution.types import EvidenceTier, ScoredCandidate


def explain(scored: list[ScoredCandidate]) -> dict[str, str]:
    """Return a dict ``{candidate_key: narrative}`` keyed by run id + terminal."""
    return {s.candidate.terminal_address: _narrative(s) for s in scored}


def _narrative(s: ScoredCandidate) -> str:
    cand = s.candidate
    tier = s.evidence_tier
    band = s.confidence_band

    # Lead with the role of the terminal.
    if cand.hits_mixer:
        lead = (
            f"Funds reached a known mixer ({cand.mixer_id}); attribution "
            "stops here per Phase 14 hard rule."
        )
    elif cand.terminal_role == "vasp" and cand.vasp_id:
        lead = (
            f"Terminal wallet is tagged as a deposit of '{cand.vasp_id}' "
            f"({cand.terminal_label or 'no label'})."
        )
    elif cand.terminal_role == "hub":
        lead = (
            "Terminal is a high-degree intermediary with no VASP tag — "
            "insufficient signal to attribute."
        )
    elif cand.terminal_role == "dead_end":
        lead = "Funds reach a single dead-end wallet with no further hops."
    else:
        lead = f"Terminal role is '{cand.terminal_role}'; no VASP label found."

    # Bridge statement.
    bridge = ""
    if cand.crosses_bridge:
        bridge = (
            f" The path crosses the '{cand.bridge_id}' bridge — confidence "
            "has been degraded accordingly."
        )

    # Path summary.
    path = (
        f" Path traverses {cand.hops} hop(s) over chain '{cand.chain}' "
        f"with {len(cand.edges)} backing transaction(s) totalling "
        f"{cand.total_amount:.4f} units."
    )

    # Tier + band.
    tier_label = {
        EvidenceTier.TIER_1_DEPOSIT_LABEL: "Tier 1 (Direct VASP deposit label)",
        EvidenceTier.TIER_2_HOT_WALLET_LABEL: "Tier 2 (Tagged hot-wallet cluster)",
        EvidenceTier.TIER_3_BEHAVIORAL: "Tier 3 (Behavioral / consolidation only)",
        EvidenceTier.TIER_4_TOPOLOGICAL: "Tier 4 (Heuristic / topological only)",
        EvidenceTier.TIER_NONE: "Insufficient evidence",
    }.get(tier, "Unknown")
    tier_line = (
        f" Evidence tier: {tier_label}. Confidence band: {band} "
        f"(score {s.confidence_score:.1f}/100)."
    )

    # Proximity rank breakdown (compact).
    bd = s.proximity_breakdown
    proximity_line = (
        f" Proximity rank = {s.proximity_rank:.2f} "
        f"(hops={bd.get('base_hop_cost', 0):.0f}, "
        f"mix={bd.get('mixing_penalty', 0):.1f}, "
        f"bridge={bd.get('bridge_penalty', 0):.1f}, "
        f"stale={bd.get('time_decay_penalty', 0):.2f}, "
        f"fan-out={bd.get('fan_out_penalty', 0):.1f})."
    )

    return lead + path + bridge + tier_line + proximity_line


__all__ = ["explain"]
