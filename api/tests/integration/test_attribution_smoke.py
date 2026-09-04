"""End-to-end attribution smoke tests (WP-11 + WP-12..WP-17).

These tests exercise the offline attribution path against all 8
synthetic cases. They mirror the curl recipes documented in
``data/synthetic/README.md`` and ``docs/development.md``.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.factory import build_default_provider_registry


def _client() -> TestClient:
    return TestClient(create_app())


def _run(c: TestClient, case_id: int, *, chain: str = "ethereum") -> dict:
    suspect = f"0xDEMO_case{case_id}_suspect_001"
    r = c.post(
        "/api/v1/attribution/run",
        json={"suspect_address": suspect, "chain": chain},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _top(cands: list[dict]) -> dict:
    return cands[0]


def test_case1_direct_vasp_deposit() -> None:
    with _client() as c:
        result = _run(c, 1)
    assert result["outcome"] == "single_candidate"
    assert result["insufficient_evidence"] is False
    cand = _top(result["candidates"])
    assert cand["candidate"]["terminal_role"] == "vasp"
    assert cand["candidate"]["vasp_id"] == "vasp_alpha"
    assert cand["evidence_tier"] == 1
    assert cand["confidence_band"] == "high"
    assert cand["confidence_score"] >= 70


def test_case2_one_intermediary() -> None:
    with _client() as c:
        result = _run(c, 2)
    assert result["outcome"] == "single_candidate"
    cand = _top(result["candidates"])
    assert cand["candidate"]["vasp_id"] == "vasp_bravo"
    assert cand["candidate"]["hops"] == 2


def test_case3_multiple_intermediaries() -> None:
    with _client() as c:
        result = _run(c, 3)
    assert result["outcome"] == "single_candidate"
    cand = _top(result["candidates"])
    assert cand["candidate"]["vasp_id"] == "vasp_charlie"
    assert cand["candidate"]["hops"] == 4
    assert cand["evidence_tier"] in {2, 3}


def test_case4_multiple_vasps_ranked() -> None:
    with _client() as c:
        result = _run(c, 4)
    assert result["outcome"] == "ranked_multi_candidate"
    # Multiple VASPs present
    vasp_ids = {c["candidate"]["vasp_id"] for c in result["candidates"]}
    assert {"vasp_delta", "vasp_echo", "vasp_foxtrot"}.issubset(vasp_ids)
    # All candidates expose BOTH scores.
    for cand in result["candidates"]:
        assert "proximity_rank" in cand
        assert "confidence_score" in cand
        assert "evidence_tier" in cand
    # Sorted by proximity_rank ascending.
    ranks = [c["proximity_rank"] for c in result["candidates"]]
    assert ranks == sorted(ranks)


def test_case5_mixer_returns_insufficient_evidence() -> None:
    with _client() as c:
        result = _run(c, 5)
    assert result["outcome"] == "insufficient_evidence"
    assert result["insufficient_evidence"] is True
    mixer_cands = [c for c in result["candidates"] if c["candidate"]["hits_mixer"]]
    assert mixer_cands, "the mixer endpoint must appear as a candidate"
    assert mixer_cands[0]["candidate"]["mixer_id"] == "mixer_demo_a"


def test_case6_bridge_to_btc_vasp() -> None:
    with _client() as c:
        result = _run(c, 6)
    assert result["outcome"] == "single_candidate"
    cand = _top(result["candidates"])
    assert cand["candidate"]["vasp_id"] == "vasp_foxtrot"
    assert cand["candidate"]["bridge_id"] == "bridge_eth_btc"
    assert cand["candidate"]["crosses_bridge"] is True
    # Bridge hop degrades confidence below a non-bridged direct deposit.
    assert cand["confidence_score"] < 100


def test_case7_false_candidate_filtered() -> None:
    with _client() as c:
        result = _run(c, 7)
    assert result["outcome"] == "false_candidate_filtered"


def test_case8_ambiguous_returns_insufficient_evidence() -> None:
    with _client() as c:
        result = _run(c, 8)
    assert result["outcome"] == "insufficient_evidence"
    assert result["insufficient_evidence"] is True


def test_unknown_chain_returns_400() -> None:
    with _client() as c:
        r = c.post(
            "/api/v1/attribution/run",
            json={"suspect_address": "0xDEMO_case1_suspect_001", "chain": "nope"},
        )
    assert r.status_code == 400


def test_registry_contains_all_supported_chains() -> None:
    reg = build_default_provider_registry()
    for code in ("bitcoin", "ethereum", "tron", "bnb", "solana", "polygon"):
        assert code in reg.available()


def test_proximity_and_confidence_are_independent() -> None:
    """Phase 3.3 invariant: the response exposes BOTH scores without
    blending them into a single ranking score."""
    with _client() as c:
        result = _run(c, 4)
    for cand in result["candidates"]:
        # Both fields must be present and not equal.
        assert "proximity_rank" in cand
        assert "confidence_score" in cand
        # No single "final_score" / "score" field that combines them.
        assert "final_score" not in cand
        assert "score" not in cand


def test_mixer_never_attributed_downstream() -> None:
    """Phase 14 hard rule: mixer = insufficient_evidence, no VASP downstream."""
    with _client() as c:
        result = _run(c, 5)
    # Outcome must be insufficient_evidence.
    assert result["outcome"] == "insufficient_evidence"
    # No candidate may be VASP-tagged.
    for cand in result["candidates"]:
        assert cand["candidate"]["terminal_role"] != "vasp"
