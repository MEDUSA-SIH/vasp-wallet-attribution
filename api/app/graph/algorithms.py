"""Graph helpers — walk and search the transaction graph.

Implementations are minimal placeholders; the contract (signatures,
return types) is final so the engine can be wired without API churn.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

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


def time_window_bfs(
    graph: nx.DiGraph,
    source: str,
    max_depth: int = 5,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    directed: bool = True,
) -> list[str]:
    """BFS filtered by edge timestamp window and monotonic time."""
    if source not in graph:
        return []

    def _in_window(data: dict[str, Any]) -> bool:
        ts = data.get("timestamp")
        if ts is None:
            return True
        # ts may be datetime or ISO string
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return True
        if start_time is not None and ts < start_time:
            return False
        if end_time is not None and ts > end_time:  # noqa: SIM103
            return False
        return True

    # Choose traversal base
    g_view = graph if directed else graph.to_undirected()  # type: ignore[assignment]
    visited: set[str] = {source}
    frontier: list[tuple[str, int]] = [(source, 0)]
    order: list[str] = [source]
    idx = 0
    while idx < len(frontier):
        node, depth = frontier[idx]
        idx += 1
        if depth >= max_depth:
            continue
        neighbors = g_view.successors(node) if directed else g_view.neighbors(node)  # type: ignore[attr-defined,union-attr]
        for nbr in list(neighbors):
            if nbr in visited:
                continue
            data = graph.get_edge_data(node, nbr) or graph.get_edge_data(nbr, node) or {}
            if not _in_window(data):
                continue
            visited.add(nbr)
            order.append(nbr)
            frontier.append((nbr, depth + 1))
    return order


def pagerank_centrality(
    graph: nx.DiGraph,
    alpha: float = 0.85,
    weight: str = "weight",
) -> dict[str, float]:
    """Return PageRank scores normalized to sum=1.0. Empty graph -> {}."""
    if graph.number_of_nodes() == 0:
        return {}
    try:
        scores = nx.pagerank(graph, alpha=alpha, weight=weight)  # type: ignore[no-untyped-call]
    except Exception:
        # Fallback for single node without edges
        n = graph.number_of_nodes()
        return {str(node): 1.0 / n for node in graph.nodes()}
    total = sum(scores.values())  # type: ignore[no-untyped-call]
    if total == 0:
        return scores  # type: ignore[no-any-return]
    return {str(k): float(v) / float(total) for k, v in scores.items()}  # type: ignore[no-untyped-call]


def temporal_shortest_path(
    graph: nx.DiGraph,
    source: str,
    target: str,
    *,
    weight: str = "weight",
) -> list[str] | None:
    """Dijkstra filtered to non-decreasing timestamps. Returns None if violated."""
    if source not in graph or target not in graph:
        return None

    def _ts(data: dict[str, Any]) -> datetime | None:
        ts = data.get("timestamp")
        if ts is None:
            return None
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
        return ts  # type: ignore[return-value]

    # Try direct dijkstra first, then validate temporal
    try:
        path = nx.dijkstra_path(graph, source, target, weight=weight)  # type: ignore[no-untyped-call]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
    # Validate monotonic
    times: list[datetime] = []
    for u, v in zip(path, path[1:], strict=False):
        data = graph.get_edge_data(u, v) or {}
        t = _ts(data)  # type: ignore[arg-type]
        if t is not None:
            times.append(t)
    for i in range(1, len(times)):
        if times[i] < times[i - 1]:
            # Invalid — try to find alternative via brute force for small graphs
            # Fallback: enumerate paths by BFS order and pick cheapest valid
            best: list[str] | None = None
            best_cost = float("inf")
            for cand in nx.all_simple_paths(graph, source, target, cutoff=5):  # type: ignore[no-untyped-call]
                # check temporal
                valid = True
                cand_times: list[datetime] = []
                cost = 0.0
                for a, b in zip(cand, cand[1:], strict=False):
                    d = graph.get_edge_data(a, b) or {}  # type: ignore[assignment]
                    t2 = _ts(d)  # type: ignore[arg-type]
                    if t2 is not None:
                        cand_times.append(t2)
                    cost += float(d.get(weight, 1.0))  # type: ignore[arg-type]
                for j in range(1, len(cand_times)):
                    if cand_times[j] < cand_times[j - 1]:
                        valid = False
                        break
                if valid and cost < best_cost:
                    best_cost = cost
                    best = cand  # type: ignore[assignment]
            return best
    return path


def detect_clusters(graph: nx.DiGraph, *, min_size: int = 2) -> Iterable[set[str]]:
    """Yield connected components of size >= ``min_size``."""
    for component in nx.weakly_connected_components(graph):
        if len(component) >= min_size:
            yield component


__all__ = [
    "bfs",
    "weighted_shortest_path",
    "detect_clusters",
    "time_window_bfs",
    "pagerank_centrality",
    "temporal_shortest_path",
]
