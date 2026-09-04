"""End-to-end attribution smoke tests (WP-11).

These tests exercise the offline attribution path against all 8
synthetic cases. They mirror the curl recipes documented in
``data/synthetic/README.md``.
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


def test_case1_direct_vasp_deposit() -> None:
    with _client() as c:
        result = _run(c, 1)
    assert result["outcome"] == "single_candidate"
    assert result["insufficient_evidence"] is False
    assert len(result["candidates"]) == 1
    cand = result["candidates"][0]
    assert cand["endpoint_role"] == "vasp"
    assert cand["vasp_id"] == "vasp_alpha"


def test_case2_one_intermediary() -> None:
    with _client() as c:
        result = _run(c, 2)
    assert result["outcome"] == "single_candidate"
    cand = result["candidates"][0]
    assert cand["vasp_id"] == "vasp_bravo"
    assert cand["hops"] == 2


def test_case3_multiple_intermediaries() -> None:
    with _client() as c:
        result = _run(c, 3)
    assert result["outcome"] == "single_candidate"
    cand = result["candidates"][0]
    assert cand["vasp_id"] == "vasp_charlie"
    assert cand["hops"] == 4
    # Confidence decays with hops (placeholder scoring).
    assert cand["confidence"] < result["candidates"][0]["confidence"] or cand["confidence"] < 0.5


def test_case4_multiple_vasps_ranked() -> None:
    with _client() as c:
        result = _run(c, 4)
    assert result["outcome"] == "ranked_multi_candidate"
    vasp_ids = {c["vasp_id"] for c in result["candidates"]}
    assert {"vasp_delta", "vasp_echo", "vasp_foxtrot"}.issubset(vasp_ids)


def test_case5_mixer_returns_insufficient_evidence() -> None:
    with _client() as c:
        result = _run(c, 5)
    assert result["outcome"] == "insufficient_evidence"
    assert result["insufficient_evidence"] is True
    mixer_candidates = [c for c in result["candidates"] if c["endpoint_role"] == "mixer"]
    assert mixer_candidates, "the mixer endpoint must appear as a candidate"
    assert mixer_candidates[0]["mixer_id"] == "mixer_demo_a"


def test_case6_bridge_to_btc_vasp() -> None:
    with _client() as c:
        result = _run(c, 6)
    assert result["outcome"] == "single_candidate"
    cand = result["candidates"][0]
    assert cand["vasp_id"] == "vasp_foxtrot"
    assert cand["bridge_id"] == "bridge_eth_btc"


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