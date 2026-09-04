"""Graph store tests."""

from __future__ import annotations

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
