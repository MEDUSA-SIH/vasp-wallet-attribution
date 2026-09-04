"""Unit tests for the attribution engine stages (Phase 10)."""
from __future__ import annotations

from app.attribution.engine import AttributionEngine, AttributionResult
from app.attribution.explainability import explain
from app.attribution.filtering import DegreeLookup, apply_filters
from app.attribution.ranking import classify_outcome, rank
from app.attribution.scoring import CONFIDENCE_WEIGHTS, compute_confidence, compute_proximity
from app.attribution.traversal import hop_sequence, key_tx_hashes, path_integrity, reconstruct
from app.attribution.types import Candidate, EvidenceItem, EvidenceTier, HopEdge, ScoredCandidate
from app.providers.factory import build_default_provider_registry


def _scored_with(role: str, hops: int = 1, **kwargs) -> ScoredCandidate:
    cand = Candidate(
        suspect_address="suspect",
        terminal_address=f"terminal_{role}",
        terminal_role=role,
        terminal_label=kwargs.get("label"),
        chain=kwargs.get("chain", "ethereum"),
        hops=hops,
        path=["suspect"] + [f"hop{i}" for i in range(hops)] + [f"terminal_{role}"],
        edges=[
            HopEdge(
                tx_hash=f"tx_{i}",
                chain=kwargs.get("chain", "ethereum"),
                from_address=f"hop{i-1}" if i else "suspect",
                to_address=f"hop{i}",
                timestamp="2024-01-01T10:00:00Z",
                amount=1.0,
                asset_symbol="ETH",
            )
            for i in range(hops)
        ],
        vasp_id=kwargs.get("vasp_id"),
        mixer_id=kwargs.get("mixer_id"),
        bridge_id=kwargs.get("bridge_id"),
        crosses_bridge=kwargs.get("crosses_bridge", False),
        hits_mixer=role == "mixer",
        total_amount=kwargs.get("total_amount", 1.0),
        first_seen_at="2024-01-01T10:00:00Z",
        last_seen_at="2024-01-01T10:00:00Z",
    )
    return ScoredCandidate(candidate=cand)


# --- Stage B -----------------------------------------------------------------


def test_traversal_reconstruct_wraps_candidates() -> None:
    cand = _scored_with("vasp").candidate
    out = reconstruct([cand])
    assert len(out) == 1
    assert isinstance(out[0], ScoredCandidate)


def test_traversal_helpers() -> None:
    cand = _scored_with("vasp", hops=2).candidate
    seq = hop_sequence(cand)
    assert [s["address"] for s in seq] == cand.path
    assert key_tx_hashes(cand) == ["tx_0", "tx_1"]
    assert path_integrity(cand) == 1.0


# --- Stage C -----------------------------------------------------------------


def test_filtering_drops_zero_hop() -> None:
    empty = Candidate(suspect_address="s", terminal_address="s", terminal_role="vasp")
    out = apply_filters([ScoredCandidate(candidate=empty)])
    assert out == []


def test_filtering_keeps_mixer_terminal_as_evidence() -> None:
    """Mixer stays in the candidate list (Stage G demotes it)."""
    s = _scored_with("mixer", mixer_id="mixer_x", hops=2)
    out = apply_filters([s])
    assert len(out) == 1
    assert out[0].candidate.hits_mixer


def test_filtering_demotes_high_degree_to_hub() -> None:
    class FakeDataset:
        def __init__(self, n: int) -> None:
            from app.providers.canonical import CanonicalTransaction
            self.tx_by_address = {
                ("terminal_intermediary", "ethereum"): [
                    CanonicalTransaction(
                        chain="ethereum",
                        tx_hash=f"h{i}",
                        block_height=1,
                        block_timestamp=None,
                        from_address="terminal_intermediary",
                        to_address=f"other_{i}",
                        asset_symbol="ETH",
                        amount=1,
                        fee=0,
                    )
                    for i in range(n)
                ]
            }

    s = _scored_with("intermediary", hops=2)
    out = apply_filters([s], degree_lookup=DegreeLookup(FakeDataset(10)))
    assert len(out) == 1
    assert out[0].candidate.terminal_role == "hub"


# --- Stage E -----------------------------------------------------------------


def test_proximity_rank_components() -> None:
    s = _scored_with("vasp", hops=3, crosses_bridge=True, bridge_id="bridge_x")
    # Use a fresh candidate with no `last_seen_at` so time_decay doesn't
    # kick in (the helper fixture sets it to 2024-01-01 which is >90 days
    # old relative to "now").
    s.candidate.last_seen_at = None
    compute_proximity([s])
    bd = s.proximity_breakdown
    assert bd["base_hop_cost"] == 3.0
    assert bd["bridge_penalty"] == 1.0
    assert s.proximity_rank == round(3.0 + 1.0 + 0.0 + 0.0, 4)


def test_proximity_rank_mixer_penalty() -> None:
    s = _scored_with("mixer", hops=2, mixer_id="m1")
    s.candidate.last_seen_at = None
    compute_proximity([s])
    assert s.proximity_breakdown["mixing_penalty"] == 2.0


# --- Stage F -----------------------------------------------------------------


def test_confidence_band_thresholds() -> None:
    # Score >= 70 -> high; 40..69 -> medium; < 40 -> low
    s_high = _scored_with("vasp", hops=1)
    s_high.candidate.terminal_label = "VASP Alpha"
    compute_confidence([s_high])
    assert s_high.confidence_band == "high"
    assert s_high.confidence_score >= 70


def test_confidence_weights_equal() -> None:
    """MVP invariant: equal weights (1/6 each)."""
    assert len(CONFIDENCE_WEIGHTS) == 6
    for w in CONFIDENCE_WEIGHTS.values():
        assert abs(w - 1 / 6) < 1e-9
    assert abs(sum(CONFIDENCE_WEIGHTS.values()) - 1.0) < 1e-9


def test_confidence_mixer_is_zero() -> None:
    s = _scored_with("mixer", hops=2, mixer_id="m1")
    compute_confidence([s])
    assert s.confidence_score == 0.0
    assert s.confidence_band == "low"
    assert s.evidence_tier == EvidenceTier.TIER_NONE


def test_confidence_evidence_tier_assignment() -> None:
    # 1-hop direct VASP = Tier 1
    s1 = _scored_with("vasp", hops=1, vasp_id="v1")
    s1.candidate.terminal_label = "X"
    compute_confidence([s1])
    assert s1.evidence_tier == EvidenceTier.TIER_1_DEPOSIT_LABEL

    # Multi-hop VASP = Tier 2 or 3
    s3 = _scored_with("vasp", hops=3, vasp_id="v3")
    s3.candidate.terminal_label = "X"
    compute_confidence([s3])
    assert s3.evidence_tier in {
        EvidenceTier.TIER_2_HOT_WALLET_LABEL,
        EvidenceTier.TIER_3_BEHAVIORAL,
    }

    # Bridge path = Tier 3
    bridge_s = _scored_with("vasp", hops=2, vasp_id="vB", crosses_bridge=True, bridge_id="b1")
    bridge_s.candidate.terminal_label = "X"
    compute_confidence([bridge_s])
    assert bridge_s.evidence_tier == EvidenceTier.TIER_3_BEHAVIORAL


# --- Stage G -----------------------------------------------------------------


def test_ranking_sorts_by_proximity_rank() -> None:
    candidates = [
        _scored_with("vasp", hops=4, vasp_id="far"),
        _scored_with("vasp", hops=1, vasp_id="near"),
    ]
    candidates[0].proximity_rank = 5.0
    candidates[1].proximity_rank = 1.0
    out = rank(candidates)
    assert out[0].candidate.vasp_id == "near"
    assert out[1].candidate.vasp_id == "far"


def test_classify_outcome_single_vasp() -> None:
    candidates = [_scored_with("vasp", hops=1, vasp_id="v1")]
    candidates[0].candidate.terminal_label = "X"
    compute_confidence(candidates)
    outcome, insufficient = classify_outcome(candidates)
    assert outcome == "single_candidate"
    assert insufficient is False


def test_classify_outcome_multi_vasp() -> None:
    candidates = [
        _scored_with("vasp", hops=1, vasp_id="a"),
        _scored_with("vasp", hops=2, vasp_id="b"),
    ]
    for c in candidates:
        c.candidate.terminal_label = "X"
    compute_confidence(candidates)
    outcome, _ = classify_outcome(candidates)
    assert outcome == "ranked_multi_candidate"


def test_classify_outcome_mixer_is_insufficient() -> None:
    candidates = [_scored_with("mixer", hops=2, mixer_id="m1")]
    outcome, insufficient = classify_outcome(candidates)
    assert outcome == "insufficient_evidence"
    assert insufficient is True


def test_classify_outcome_hub_is_false_candidate_filtered() -> None:
    candidates = [_scored_with("hub", hops=1)]
    outcome, _ = classify_outcome(candidates)
    assert outcome == "false_candidate_filtered"


def test_classify_outcome_dead_end_is_insufficient() -> None:
    candidates = [_scored_with("dead_end", hops=1)]
    outcome, insufficient = classify_outcome(candidates)
    assert outcome == "insufficient_evidence"
    assert insufficient is True


def test_classify_outcome_empty() -> None:
    outcome, insufficient = classify_outcome([])
    assert outcome == "insufficient_evidence"
    assert insufficient is True


# --- Stage H -----------------------------------------------------------------


def test_explain_returns_narrative_per_candidate() -> None:
    candidates = [_scored_with("vasp", hops=1, vasp_id="alpha")]
    candidates[0].candidate.terminal_label = "VASP Alpha deposit"
    compute_confidence(candidates)
    out = explain(candidates)
    # The narrative wraps the vasp_id in single quotes.
    assert "'alpha'" in out["terminal_vasp"]
    assert "VASP Alpha deposit" in out["terminal_vasp"]
    assert "Tier 1" in out["terminal_vasp"]


def test_explain_includes_bridge_note() -> None:
    s = _scored_with("vasp", hops=2, vasp_id="v1", crosses_bridge=True, bridge_id="bridge_x")
    s.candidate.terminal_label = "X"
    compute_confidence([s])
    out = explain([s])
    assert "bridge" in out["terminal_vasp"].lower()
    assert "confidence" in out["terminal_vasp"].lower()


def test_explain_uses_mixer_phrasing() -> None:
    s = _scored_with("mixer", hops=2, mixer_id="m1")
    compute_confidence([s])
    out = explain([s])
    assert "mixer" in out["terminal_mixer"].lower()
    assert "Phase 14" in out["terminal_mixer"]


# --- Engine (A→H) ------------------------------------------------------------


def test_engine_result_has_independent_scores() -> None:
    """Phase 3.3 invariant enforced end-to-end."""
    reg = build_default_provider_registry()
    engine = AttributionEngine(max_hops=4)
    import asyncio
    result: AttributionResult = asyncio.run(
        engine.run("0xDEMO_case4_suspect_001", chain="ethereum", registry=reg)
    )
    for scored in result.candidates:
        assert "proximity_rank" in scored.proximity_breakdown or scored.proximity_rank is not None
        assert scored.confidence_score is not None


def test_engine_synthesises_evidence_items() -> None:
    reg = build_default_provider_registry()
    engine = AttributionEngine(max_hops=4)
    import asyncio
    result = asyncio.run(
        engine.run("0xDEMO_case1_suspect_001", chain="ethereum", registry=reg)
    )
    assert result.candidates, "expected at least one candidate"
    top = result.candidates[0]
    codes = {e.code for e in top.evidence}
    assert "vasp_label" in codes or "path_integrity" in codes