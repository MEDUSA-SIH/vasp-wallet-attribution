"""Graph store tests."""

from __future__ import annotations

from datetime import UTC, datetime

import networkx as nx

from app.graph.algorithms import pagerank_centrality, temporal_shortest_path, time_window_bfs
from app.graph.models import EdgeKind, GraphEdge, GraphNode, NodeKind
from app.graph.store import GraphStore


def test_add_node_and_edge() -> None:
    store = GraphStore()
    store.add_node(GraphNode(id="wallet:1", kind=NodeKind.WALLET, chain="bitcoin"))
    store.add_node(GraphNode(id="wallet:2", kind=NodeKind.WALLET, chain="bitcoin"))
    store.add_edge(
        GraphEdge(source="wallet:1", target="wallet:2", kind=EdgeKind.TRANSFER, weight=1.0)
    )
    assert store.node_count() == 2
    assert store.edge_count() == 1


def test_get_outgoing() -> None:
    store = GraphStore()
    store.add_node(GraphNode(id="a", kind=NodeKind.WALLET))
    store.add_node(GraphNode(id="b", kind=NodeKind.WALLET))
    store.add_edge(GraphEdge(source="a", target="b", kind=EdgeKind.TRANSFER))
    out = store.get_outgoing("a")
    assert len(out) == 1
    assert out[0][0] == "b"


def test_time_window_bfs_filters_by_timestamp() -> None:
    g = nx.DiGraph()
    g.add_edge("a", "b", timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    g.add_edge("b", "c", timestamp=datetime(2024, 6, 1, tzinfo=UTC))
    g.add_edge("a", "d", timestamp=datetime(2020, 1, 1, tzinfo=UTC))
    # No filter -> all 4 nodes
    assert set(time_window_bfs(g, "a", max_depth=2)) == {"a", "b", "c", "d"}
    # Window excludes old edge a->d
    result = time_window_bfs(g, "a", max_depth=2, start_time=datetime(2024, 1, 1, tzinfo=UTC))
    assert "d" not in result
    assert "b" in result


def test_time_window_bfs_missing_source() -> None:
    g = nx.DiGraph()
    assert time_window_bfs(g, "missing") == []


def test_pagerank_centrality_basic() -> None:
    g = nx.DiGraph()
    # hub a points to many leaves -> leaves have inbound, hub high out-degree
    for i in range(5):
        g.add_edge("hub", f"leaf_{i}", weight=1.0)
    scores = pagerank_centrality(g)
    assert abs(sum(scores.values()) - 1.0) < 1e-6
    # hub should have non-zero, leaves roughly equal
    assert "hub" in scores
    assert all(s > 0 for s in scores.values())


def test_pagerank_missing_node_graph() -> None:
    g = nx.DiGraph()
    g.add_node("solo")
    scores = pagerank_centrality(g)
    assert scores["solo"] == 1.0


def test_pagerank_empty_graph() -> None:
    g = nx.DiGraph()
    assert pagerank_centrality(g) == {}


def test_temporal_shortest_path_enforces_time_order() -> None:
    g = nx.DiGraph()
    # a->b at t=10, b->c at t=5 (goes back in time) -> invalid
    g.add_edge("a", "b", weight=1.0, timestamp=datetime(2024, 1, 10, tzinfo=UTC))
    g.add_edge("b", "c", weight=1.0, timestamp=datetime(2024, 1, 5, tzinfo=UTC))
    g.add_edge("a", "c", weight=5.0, timestamp=datetime(2024, 1, 11, tzinfo=UTC))
    # temporal path should pick a->c direct (5.0) over invalid a->b->c
    path = temporal_shortest_path(g, "a", "c")
    assert path == ["a", "c"]


def test_temporal_shortest_path_no_path() -> None:
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=1.0)
    assert temporal_shortest_path(g, "a", "missing") is None
    assert temporal_shortest_path(g, "missing", "b") is None
