"""Graph algorithm stubs (Phase 6 + Phase 11).

Implementations are minimal placeholders; the contract (signatures,
return types) is final so the engine can be wired without API churn.
"""
from __future__ import annotations

from collections.abc import Iterable

import networkx as nx


def bfs(graph: nx.DiGraph, source: str, max_depth: int = 5) -> list[str]:
    """Return nodes reachable from ``source`` via BFS up to ``max_depth``."""
    if source not in graph:
        return []
    lengths = nx.single_source_shortest_path_length(graph, source, cutoff=max_depth)
    return list(lengths.keys())


def weighted_shortest_path(
    graph: nx.DiGraph,
    source: str,
    target: str,
) -> list[str] | None:
    """Return the lowest-cost path from ``source`` to ``target`` or ``None``."""
    try:
        return nx.dijkstra_path(graph, source, target, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def detect_clusters(graph: nx.DiGraph, *, min_size: int = 2) -> Iterable[set[str]]:
    """Yield connected components of size >= ``min_size``."""
    for component in nx.weakly_connected_components(graph):
        if len(component) >= min_size:
            yield component


__all__ = ["bfs", "weighted_shortest_path", "detect_clusters"]