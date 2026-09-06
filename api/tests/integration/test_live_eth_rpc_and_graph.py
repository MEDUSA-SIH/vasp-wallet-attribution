"""Live ETH RPC (Tatum) + Phase A graph integration.

CI-visible: these tests run on every `pytest -v` (no extra flag).
- ETH RPC tests hit https://ethereum-mainnet.gateway.tatum.io via JSON-RPC
  and skip gracefully if the gateway is unreachable (CI network flaky).
- Phase A tests exercise WP-19 `time_window_bfs`, `pagerank_centrality`,
  `temporal_shortest_path`, and `PagerankLookup` against a deterministic
  in-memory graph — they always run (no network) and guard the
  prod-grade code shipped in Tasks 1-4.

Env override: set ETH_RPC_URL to test a different endpoint.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import httpx
import networkx as nx
import pytest

from app.attribution.filtering import HUB_PAGERANK_THRESHOLD, PagerankLookup, apply_filters
from app.attribution.types import ScoredCandidate
from app.graph.algorithms import pagerank_centrality, temporal_shortest_path, time_window_bfs
from app.graph.models import EdgeKind, GraphEdge, GraphNode, NodeKind
from app.graph.store import GraphStore

# ---------------------------------------------------------------------------
# ETH RPC live — Tatum gateway
# ---------------------------------------------------------------------------

_TATUM_URL = os.getenv("ETH_RPC_URL", "https://ethereum-mainnet.gateway.tatum.io")
_VITALIK = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
_TIMEOUT = 8.0


def test_live_tatum_eth_block_number_returns_hex() -> None:  # noqa: N802
    """Live: Tatum gateway returns a hex block number."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}
    try:
        r = httpx.post(_TATUM_URL, json=payload, timeout=_TIMEOUT)
    except httpx.RequestError as exc:
        pytest.skip(f"Tatum gateway unreachable: {exc}")
    if r.status_code != 200:
        pytest.skip(f"Tatum gateway HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    result = data.get("result")
    assert isinstance(result, str), f"expected hex string, got {data!r}"
    assert result.startswith("0x"), f"expected 0x hex, got {result!r}"
    # Must be parseable and > 18M (mainnet height Sep 2026 ~19-20M)
    height = int(result, 16)
    assert height > 18_000_000, f"implausibly low height {height:#x}"


def test_live_tatum_eth_get_balance_vitalik() -> None:  # noqa: N802
    """Live: eth_getBalance for a known address returns hex balance."""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "eth_getBalance",
        "params": [_VITALIK, "latest"],
    }
    try:
        r = httpx.post(_TATUM_URL, json=payload, timeout=_TIMEOUT)
    except httpx.RequestError as exc:
        pytest.skip(f"Tatum gateway unreachable: {exc}")
    if r.status_code != 200:
        pytest.skip(f"Tatum gateway HTTP {r.status_code}: {r.text[:200]}")
    data = r.json()
    result = data.get("result")
    assert isinstance(result, str) and result.startswith("0x"), f"bad balance {data!r}"
    # Just prove parsing works — balance may be 0-100s ETH
    balance_wei = int(result, 16)
    assert balance_wei >= 0


def test_live_tatum_eth_chain_id_is_mainnet() -> None:  # noqa: N802
    """Live: eth_chainId must be 0x1 for mainnet."""
    payload = {"jsonrpc": "2.0", "id": 3, "method": "eth_chainId", "params": []}
    try:
        r = httpx.post(_TATUM_URL, json=payload, timeout=_TIMEOUT)
    except httpx.RequestError as exc:
        pytest.skip(f"Tatum gateway unreachable: {exc}")
    if r.status_code != 200:
        pytest.skip(f"Tatum gateway HTTP {r.status_code}")
    data = r.json()
    assert data.get("result") == "0x1", f"expected mainnet 0x1, got {data!r}"


# ---------------------------------------------------------------------------
# Phase A live — deterministic, no network, always runs
# ---------------------------------------------------------------------------


def _build_star_graph() -> tuple[GraphStore, str]:
    """Helper: star graph center hub -> 6 leaves (used by pagerank tests)."""
    store = GraphStore()
    store.add_node(GraphNode(id="hub", kind=NodeKind.WALLET))
    for i in range(6):
        leaf = f"leaf_{i}"
        store.add_node(GraphNode(id=leaf, kind=NodeKind.WALLET))
        store.add_edge(GraphEdge(source="hub", target=leaf, kind=EdgeKind.TRANSFER, weight=1.0))
    return store, "hub"


def test_live_phase_a_time_window_bfs_filters_old_edges() -> None:
    """Phase A: time_window_bfs excludes edges outside window."""
    g = nx.DiGraph()
    now = datetime.now(tz=UTC)
    old = now - timedelta(days=400)
    recent = now - timedelta(days=10)
    g.add_edge("a", "b", timestamp=recent, weight=1.0)
    g.add_edge("b", "c", timestamp=recent, weight=1.0)
    g.add_edge("a", "d", timestamp=old, weight=1.0)
    assert set(time_window_bfs(g, "a", max_depth=2)) == {"a", "b", "c", "d"}
    filtered = set(time_window_bfs(g, "a", max_depth=2, start_time=now - timedelta(days=90)))
    assert "d" not in filtered
    assert "b" in filtered
    # GraphStore wrapper mirrors the same
    store = GraphStore()
    store.add_node(GraphNode(id="a", kind=NodeKind.WALLET))
    store.add_node(GraphNode(id="b", kind=NodeKind.WALLET))
    store.add_node(GraphNode(id="d", kind=NodeKind.WALLET))
    store._graph.add_edge("a", "b", timestamp=recent, weight=1.0)
    store._graph.add_edge("a", "d", timestamp=old, weight=1.0)
    assert "d" not in store.neighbors_within("a", 1, start_time=now - timedelta(days=90))


def test_live_phase_a_pagerank_centrality_normalized() -> None:
    """Phase A: pagerank sums to 1.0 and hub has non-zero score."""
    store, hub = _build_star_graph()
    scores = pagerank_centrality(store.raw)
    assert abs(sum(scores.values()) - 1.0) < 1e-6
    assert hub in scores
    assert all(v > 0 for v in scores.values())
    # Solo + empty edge cases
    solo_g = nx.DiGraph()
    solo_g.add_node("solo")
    assert pagerank_centrality(solo_g)["solo"] == 1.0
    assert pagerank_centrality(nx.DiGraph()) == {}


def test_live_phase_a_temporal_shortest_path_monotonic() -> None:
    """Phase A: temporal_shortest_path picks monotonic cheapest path."""
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0, timestamp=datetime(2024, 1, 10, tzinfo=UTC))
    g.add_edge("b", "c", weight=1.0, timestamp=datetime(2024, 1, 5, tzinfo=UTC))  # goes back
    g.add_edge("a", "c", weight=5.0, timestamp=datetime(2024, 1, 11, tzinfo=UTC))
    assert temporal_shortest_path(g, "a", "c") == ["a", "c"]
    assert temporal_shortest_path(g, "a", "missing") is None
    # Valid monotone chain should be returned
    g2 = nx.DiGraph()
    g2.add_edge("x", "y", weight=1.0, timestamp=datetime(2024, 2, 1, tzinfo=UTC))
    g2.add_edge("y", "z", weight=1.0, timestamp=datetime(2024, 2, 2, tzinfo=UTC))
    assert temporal_shortest_path(g2, "x", "z") == ["x", "y", "z"]


def test_live_phase_a_pagerank_lookup_hub_demotes() -> None:
    """Phase A: PagerankLookup flags hub via threshold (OR with degree)."""

    def _scored_with(role: str, addr: str) -> ScoredCandidate:
        from app.attribution.types import Candidate

        cand = Candidate(
            suspect_address="suspect",
            terminal_address=addr,
            terminal_role=role,
            hops=2,
            path=["suspect", "hop", addr],
            edges=[
                # type hints: HopEdge
            ],
        )
        # Need at least one HopEdge to pass apply_filters edge check
        from app.attribution.types import HopEdge

        cand.edges = [
            HopEdge(
                tx_hash="h1",
                chain="ethereum",
                from_address="suspect",
                to_address="hop",
                timestamp="2024-01-01T00:00:00Z",
                amount=1.0,
                asset_symbol="ETH",
            ),
            HopEdge(
                tx_hash="h2",
                chain="ethereum",
                from_address="hop",
                to_address=addr,
                timestamp="2024-01-02T00:00:00Z",
                amount=1.0,
                asset_symbol="ETH",
            ),
        ]
        cand.hops = 2
        return ScoredCandidate(candidate=cand)

    store, hub = _build_star_graph()
    plookup = PagerankLookup(store.raw)
    # Low threshold should flag hub (uniform ~0.142, so 0.1 flags)
    s = _scored_with("intermediary", hub)
    out = apply_filters([s], pagerank_lookup=plookup, pagerank_threshold=0.1)
    assert out[0].candidate.terminal_role == "hub"
    # VASP never demoted even if high pagerank
    s_vasp = _scored_with("vasp", hub)
    s_vasp.candidate.vasp_id = "v1"
    out2 = apply_filters([s_vasp], pagerank_lookup=plookup, pagerank_threshold=0.0)
    assert out2[0].candidate.terminal_role == "vasp"
    # Mixer also never demoted
    s_mixer = _scored_with("mixer", hub)
    s_mixer.candidate.hits_mixer = True
    s_mixer.candidate.mixer_id = "m1"
    out3 = apply_filters([s_mixer], pagerank_lookup=plookup, pagerank_threshold=0.0)
    assert out3[0].candidate.terminal_role == "mixer"


def test_live_phase_a_graphstore_get_subgraph() -> None:
    """Phase A: GraphStore.get_subgraph returns induced copy."""
    store = GraphStore()
    store.add_node(GraphNode(id="a", kind=NodeKind.WALLET))
    store.add_node(GraphNode(id="b", kind=NodeKind.WALLET))
    store.add_node(GraphNode(id="c", kind=NodeKind.WALLET))
    store.add_edge(GraphEdge(source="a", target="b", kind=EdgeKind.TRANSFER))
    store.add_edge(GraphEdge(source="b", target="c", kind=EdgeKind.TRANSFER))
    sub = store.get_subgraph({"a", "b"})
    assert set(sub.nodes()) == {"a", "b"}
    assert sub.has_edge("a", "b")
    assert not sub.has_edge("b", "c")
    # Mutating subgraph must not affect store
    sub.remove_node("a")
    assert store.node_count() == 3
