"""In-memory graph store — holds wallets and transactions.

The MVP relies on an in-process DiGraph. In later stages the same interface
will be backed by Neo4j (see ``docs/phases-mapping.md``).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import networkx as nx

from app.graph.models import EdgeKind, GraphEdge, GraphNode, NodeKind


class GraphStore:
    """Thin wrapper around a :class:`networkx.DiGraph`.

    Methods intentionally mirror what the attribution engine needs.
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------ helpers
    @property
    def raw(self) -> nx.DiGraph:
        """Expose the underlying NetworkX graph."""
        return self._graph

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def clear(self) -> None:
        """Drop all nodes and edges."""
        self._graph.clear()

    # ------------------------------------------------------------------- writes
    def add_node(self, node: GraphNode) -> None:
        self._graph.add_node(
            node.id,
            kind=node.kind,
            chain=node.chain,
            **node.attributes,
        )

    def add_nodes(self, nodes: Iterable[GraphNode]) -> None:
        for n in nodes:
            self.add_node(n)

    def add_edge(self, edge: GraphEdge) -> None:
        self._graph.add_edge(
            edge.source,
            edge.target,
            kind=edge.kind,
            weight=edge.weight,
            **edge.attributes,
        )

    def add_edges(self, edges: Iterable[GraphEdge]) -> None:
        for e in edges:
            self.add_edge(e)

    # ------------------------------------------------------------------- reads
    def get_node(self, node_id: str) -> dict[str, Any] | None:
        if node_id not in self._graph:
            return None
        return dict(self._graph.nodes[node_id])

    def get_outgoing(self, node_id: str) -> list[tuple[str, dict[str, Any]]]:
        if node_id not in self._graph:
            return []
        return [(nbr, dict(data)) for nbr, data in self._graph.succ[node_id].items()]

    def get_incoming(self, node_id: str) -> list[tuple[str, dict[str, Any]]]:
        if node_id not in self._graph:
            return []
        return [(pred, dict(data)) for pred, data in self._graph.pred[node_id].items()]

    def neighbors_within(self, node_id: str, hops: int) -> set[str]:
        """Return all nodes reachable within ``hops`` undirected hops."""
        return set(nx.single_source_shortest_path_length(self._graph, node_id, cutoff=hops).keys())


_store_singleton: GraphStore | None = None


def get_graph_store() -> GraphStore:
    """Return the process-wide graph store singleton."""
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = GraphStore()
    return _store_singleton


def reset_graph_store() -> None:
    """Drop the singleton (used by tests)."""
    global _store_singleton
    _store_singleton = None


__all__ = [
    "GraphStore",
    "get_graph_store",
    "reset_graph_store",
    "NodeKind",
    "EdgeKind",
]
