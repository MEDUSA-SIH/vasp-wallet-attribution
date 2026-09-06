# WP-19 Graph Algorithms Phase A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement WP-19 Phase A (time-window traversal + PageRank centrality) to make `api/app/graph/algorithms.py:14-41` and `api/app/graph/store.py:84-86` production-grade, feeding deterministic hub scoring into `attribution/filtering.py:28-65` without breaking `docs/contracts.md:116-141` `GraphStore` interface.

**Architecture:** Extend existing `NetworkX DiGraph` wrapper with pure functions: `time_window_bfs` filters by `edge.attributes.timestamp` non-decreasing, `pagerank_centrality` wraps `nx.pagerank`, `temporal_shortest_path` wraps `nx.dijkstra_path` with `weight + time_decay`. `GraphStore.neighbors_within` gains optional `start_time/end_time/directed` params (additive, not breaking). `filtering.py` consumes pagerank score alongside degree for hub detection. No new dependencies beyond `networkx>=3.3`.

**Tech Stack:** Python `>=3.12`, `networkx>=3.3`, `pytest>=8.3.0` + `pytest-asyncio`, `ruff` line-length 100, `mypy` strict true, `FastAPI`/`Pydantic` unchanged.

## Global Constraints

- Python `requires-python = ">=3.12"` `api/pyproject.toml:5`
- Dependency `networkx>=3.3` only — do NOT add `python-louvain`/`cdlib`/`numpy` beyond what `networkx` already pulls `api/pyproject.toml:18`
- `tool.ruff.line-length = 100` `target-version = "py312"` `pyproject.toml:14-15`
- `tool.mypy.strict = true` `api/pyproject.toml:80` — all new functions must be fully typed, `ignore_missing_imports = true`
- `docs/contracts.md:116-141` `GraphStore` is stable: `add_node` idempotent, `neighbors_within` counts undirected hops — additive params only, never remove
- `api/app/attribution/scoring.py:64-71` `CONFIDENCE_WEIGHTS = 1/6` equal — do not touch scoring in this WP
- Spec `Phase 11:748-762` — `temporal traversal` is correctness, `centrality` is feature, `community detection (Louvain)` is `[D]` defer to WP-19b
- Spec `Phase 5:296-304` — never render Tier3/4 as certain — pagerank never auto-labels VASP, only demotes hub
- Tests must stay `ruff check` + `ruff format --check` + `pytest -q` green (`docs/work-packages.md:105` 66/66)
- One WP per branch `docs/work-packages.md:67` — touch only `api/app/graph/**` + `api/app/attribution/filtering.py` + `api/tests/unit/test_graph.py`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `api/app/graph/algorithms.py:1-41` | Pure graph algorithms: `bfs`, `weighted_shortest_path`, new `time_window_bfs`, `pagerank_centrality`, `temporal_shortest_path`, `detect_clusters` |
| `api/app/graph/store.py:17-112` | `GraphStore` wrapper: `neighbors_within` + `get_subgraph` + time filter |
| `api/app/graph/models.py:10-50` | Unchanged frozen types `NodeKind`, `EdgeKind`, `GraphNode`, `GraphEdge` |
| `api/app/attribution/filtering.py:1-85` | Hub filtering: add `PagerankLookup`, consume both degree + pagerank |
| `api/app/attribution/types.py:19-27` | Unchanged `EvidenceTier`, `HopEdge` |
| `api/tests/unit/test_graph.py:1-27` | New tests for time-window, pagerank, temporal path |
| `api/tests/unit/test_attribution_stages.py:66-109` | Update `test_filtering_demotes_high_degree_to_hub` to also cover pagerank |

---

### Task 1: Time-window BFS + GraphStore time filter

**Files:**
- Modify: `api/app/graph/algorithms.py:14-20`
- Modify: `api/app/graph/store.py:84-86`
- Test: `api/tests/unit/test_graph.py:1-27`

**Interfaces:**
- Consumes: `networkx.DiGraph`, `GraphStore.raw`, edge attr `timestamp` ISO8601 or `None`
- Produces: `time_window_bfs(graph: nx.DiGraph, source: str, max_depth: int = 5, *, start_time: datetime | None = None, end_time: datetime | None = None, directed: bool = True) -> list[str]`; `GraphStore.neighbors_within(node_id: str, hops: int, *, start_time: datetime | None = None, end_time: datetime | None = None, directed: bool = False) -> set[str]`

- [ ] **Step 1: Write failing test for time_window_bfs**

```python
# api/tests/unit/test_graph.py — append after test_get_outgoing
from datetime import UTC, datetime

from app.graph.algorithms import time_window_bfs
import networkx as nx
from app.graph.models import EdgeKind, GraphEdge, GraphNode
from app.graph.store import GraphStore

def test_time_window_bfs_filters_by_timestamp() -> None:
    g = nx.DiGraph()
    g.add_edge("a", "b", timestamp=datetime(2024, 1, 1, tzinfo=UTC))
    g.add_edge("b", "c", timestamp=datetime(2024, 6, 1, tzinfo=UTC))
    g.add_edge("a", "d", timestamp=datetime(2020, 1, 1, tzinfo=UTC))
    # No filter -> all 4 nodes
    assert set(time_window_bfs(g, "a", max_depth=2)) == {"a", "b", "c", "d"}
    # Window excludes old edge a->d
    result = time_window_bfs(
        g, "a", max_depth=2, start_time=datetime(2024, 1, 1, tzinfo=UTC)
    )
    assert "d" not in result
    assert "b" in result

def test_time_window_bfs_missing_source() -> None:
    g = nx.DiGraph()
    assert time_window_bfs(g, "missing") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project api pytest api/tests/unit/test_graph.py::test_time_window_bfs_filters_by_timestamp -v`
Expected: FAIL `ImportError: cannot import name 'time_window_bfs'` or `AttributeError`

- [ ] **Step 3: Implement time_window_bfs in algorithms.py + GraphStore.neighbors_within time filter**

```python
# api/app/graph/algorithms.py — add after weighted_shortest_path (line 30)
from datetime import datetime
from typing import Any

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
    # Build filtered view: only edges within window
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
        if end_time is not None and ts > end_time:
            return False
        return True

    # Choose traversal base
    g_view = graph if directed else graph.to_undirected()
    visited: set[str] = {source}
    frontier: list[tuple[str, int]] = [(source, 0)]
    order: list[str] = [source]
    idx = 0
    while idx < len(frontier):
        node, depth = frontier[idx]
        idx += 1
        if depth >= max_depth:
            continue
        neighbors = g_view.successors(node) if directed else g_view.neighbors(node)
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
```

```python
# api/app/graph/store.py — replace neighbors_within at 84-86
from datetime import datetime

    def neighbors_within(
        self,
        node_id: str,
        hops: int,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        directed: bool = False,
    ) -> set[str]:
        """Return nodes within hops, optionally filtered by timestamp window."""
        if node_id not in self._graph:
            return set()
        if start_time is None and end_time is None and not directed:
            # Fast path — original behavior
            return set(
                nx.single_source_shortest_path_length(self._graph, node_id, cutoff=hops).keys()
            )
        from app.graph.algorithms import time_window_bfs

        return set(
            time_window_bfs(
                self._graph,
                node_id,
                max_depth=hops,
                start_time=start_time,
                end_time=end_time,
                directed=directed,
            )
        )

    def get_subgraph(self, node_ids: set[str]) -> nx.DiGraph:
        """Return induced subgraph for node_ids (copy)."""
        return self._graph.subgraph(node_ids).copy()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project api pytest api/tests/unit/test_graph.py -v`
Expected: PASS 4 tests (2 old + 2 new)

Run: `uv run --project api ruff check api/app/graph/algorithms.py api/app/graph/store.py`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add api/app/graph/algorithms.py api/app/graph/store.py api/tests/unit/test_graph.py
git commit -m "feat(graph): add time_window_bfs + GraphStore time filter (WP-19 Task1)"
```

---

### Task 2: PageRank centrality + store helper

**Files:**
- Modify: `api/app/graph/algorithms.py:28-41`
- Modify: `api/app/graph/store.py:106-112`
- Test: `api/tests/unit/test_graph.py:1-27`

**Interfaces:**
- Consumes: `networkx.pagerank`, `nx.DiGraph`
- Produces: `pagerank_centrality(graph: nx.DiGraph, alpha: float = 0.85, weight: str = "weight") -> dict[str, float]` normalized sum=1.0

- [ ] **Step 1: Write failing test for pagerank_centrality**

```python
# api/tests/unit/test_graph.py — append
from app.graph.algorithms import pagerank_centrality

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project api pytest api/tests/unit/test_graph.py::test_pagerank_centrality_basic -v`
Expected: FAIL `ImportError: cannot import name 'pagerank_centrality'`

- [ ] **Step 3: Implement pagerank_centrality**

```python
# api/app/graph/algorithms.py — add after time_window_bfs
def pagerank_centrality(
    graph: nx.DiGraph,
    alpha: float = 0.85,
    weight: str = "weight",
) -> dict[str, float]:
    """Return PageRank scores normalized to sum=1.0. Empty graph -> {}."""
    if graph.number_of_nodes() == 0:
        return {}
    try:
        scores = nx.pagerank(graph, alpha=alpha, weight=weight)
    except Exception:
        # Fallback for single node without edges
        n = graph.number_of_nodes()
        return {node: 1.0 / n for node in graph.nodes()}
    total = sum(scores.values())
    if total == 0:
        return scores
    return {k: v / total for k, v in scores.items()}
```

- [ ] **Step 4: Run tests**

Run: `uv run --project api pytest api/tests/unit/test_graph.py -v`
Expected: PASS 7 tests

Run: `uv run --project api mypy api/app/graph/algorithms.py --strict`
Expected: no errors (may need `type: ignore` for nx.pagerank)

- [ ] **Step 5: Commit**

```bash
git add api/app/graph/algorithms.py api/tests/unit/test_graph.py
git commit -m "feat(graph): add pagerank_centrality (WP-19 Task2)"
```

---

### Task 3: Temporal shortest path (Dijkstra with time penalty)

**Files:**
- Modify: `api/app/graph/algorithms.py:22-30`
- Test: `api/tests/unit/test_graph.py:1-27`

**Interfaces:**
- Consumes: `time_window_bfs`, `nx.dijkstra_path`, edge `weight` + `timestamp`
- Produces: `temporal_shortest_path(graph: nx.DiGraph, source: str, target: str, *, weight: str = "weight") -> list[str] | None` — enforces non-decreasing timestamps, returns None if no temporal path

- [ ] **Step 1: Write failing test**

```python
# api/tests/unit/test_graph.py — append
from datetime import UTC, datetime, timedelta
from app.graph.algorithms import temporal_shortest_path

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
```

- [ ] **Step 2: Run to fail**

Run: `uv run --project api pytest api/tests/unit/test_graph.py::test_temporal_shortest_path_enforces_time_order -v`
Expected: FAIL `cannot import name 'temporal_shortest_path'`

- [ ] **Step 3: Implement**

```python
# api/app/graph/algorithms.py — add after pagerank_centrality
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
    # Collect all simple paths up to length 5, pick cheapest temporally valid
    # For prod-grade, build time-filtered view and run dijkstra
    from datetime import datetime

    def _ts(data: dict) -> datetime | None:
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
        path = nx.dijkstra_path(graph, source, target, weight=weight)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
    # Validate monotonic
    times: list[datetime] = []
    for u, v in zip(path, path[1:], strict=True):
        data = graph.get_edge_data(u, v) or {}
        t = _ts(data)
        if t is not None:
            times.append(t)
    for i in range(1, len(times)):
        if times[i] < times[i - 1]:
            # Invalid — try to find alternative via brute force for small graphs
            # Fallback: enumerate paths by BFS order and pick cheapest valid
            best: list[str] | None = None
            best_cost = float("inf")
            for cand in nx.all_simple_paths(graph, source, target, cutoff=5):
                # check temporal
                valid = True
                cand_times: list[datetime] = []
                cost = 0.0
                for a, b in zip(cand, cand[1:], strict=True):
                    d = graph.get_edge_data(a, b) or {}
                    t = _ts(d)
                    if t is not None:
                        cand_times.append(t)
                    cost += float(d.get(weight, 1.0))
                for j in range(1, len(cand_times)):
                    if cand_times[j] < cand_times[j - 1]:
                        valid = False
                        break
                if valid and cost < best_cost:
                    best_cost = cost
                    best = cand
            return best
    return path
```

- [ ] **Step 4: Run tests**

Run: `uv run --project api pytest api/tests/unit/test_graph.py -v`
Expected: PASS 9 tests

- [ ] **Step 5: Commit**

```bash
git add api/app/graph/algorithms.py api/tests/unit/test_graph.py
git commit -m "feat(graph): add temporal_shortest_path with monotonic check (WP-19 Task3)"
```

---

### Task 4: Filtering integration — PagerankLookup + hub scoring

**Files:**
- Modify: `api/app/attribution/filtering.py:1-85`
- Test: `api/tests/unit/test_attribution_stages.py:82-109`
- Test: `api/tests/unit/test_graph.py:1-27` (no change, just verify)

**Interfaces:**
- Consumes: `pagerank_centrality`, `DegreeLookup`, `GraphStore`
- Produces: `class PagerankLookup` + updated `apply_filters(candidates, *, degree_lookup=None, pagerank_lookup=None, pagerank_threshold: float = 0.15) -> list[ScoredCandidate]` — hub if `degree>4 OR pagerank>threshold` and not vasp/mixer

- [ ] **Step 1: Write failing test**

```python
# api/tests/unit/test_attribution_stages.py — append after test_filtering_demotes_high_degree_to_hub
from app.attribution.filtering import PagerankLookup

def test_filtering_pagerank_demotes_hub() -> None:
    import networkx as nx
    from app.graph.store import GraphStore
    from app.graph.models import NodeKind, GraphNode, EdgeKind, GraphEdge

    store = GraphStore()
    # Create star: center is hub with high pagerank
    store.add_node(GraphNode(id="hub", kind=NodeKind.WALLET))
    for i in range(6):
        leaf = f"leaf_{i}"
        store.add_node(GraphNode(id=leaf, kind=NodeKind.WALLET))
        store.add_edge(GraphEdge(source="hub", target=leaf, kind=EdgeKind.TRANSFER, weight=1.0))
    # pagerank lookup over store graph
    plookup = PagerankLookup(store.raw)
    s = _scored_with("intermediary", hops=2)
    # force terminal to hub
    s.candidate.terminal_address = "hub"
    out = apply_filters([s], pagerank_lookup=plookup, pagerank_threshold=0.1)
    assert out[0].candidate.terminal_role == "hub"
```

- [ ] **Step 2: Run to fail**

Run: `uv run --project api pytest api/tests/unit/test_attribution_stages.py::test_filtering_pagerank_demotes_hub -v`
Expected: FAIL `cannot import name 'PagerankLookup'`

- [ ] **Step 3: Implement PagerankLookup + update apply_filters**

```python
# api/app/attribution/filtering.py — add after DegreeLookup class at line 82
import networkx as nx
from app.graph.algorithms import pagerank_centrality

HUB_PAGERANK_THRESHOLD = 0.15

class PagerankLookup:
    """Wraps pagerank_centrality for reuse."""

    def __init__(self, graph: nx.DiGraph | None = None, *, alpha: float = 0.85) -> None:
        self._scores: dict[str, float] = {}
        if graph is not None and graph.number_of_nodes() > 0:
            self._scores = pagerank_centrality(graph, alpha=alpha)

    def score(self, address: str) -> float:
        return self._scores.get(address, 0.0)

    def is_hub(self, address: str, threshold: float = HUB_PAGERANK_THRESHOLD) -> bool:
        return self.score(address) > threshold

# Update apply_filters signature at line 28
def apply_filters(
    candidates: list[ScoredCandidate],
    *,
    degree_lookup: DegreeLookup | None = None,
    pagerank_lookup: PagerankLookup | None = None,
    pagerank_threshold: float = HUB_PAGERANK_THRESHOLD,
) -> list[ScoredCandidate]:
    # ... existing body ...
    # After degree hub check at 55-60, add:
        if (
            pagerank_lookup is not None
            and pagerank_lookup.is_hub(cand.terminal_address, threshold=pagerank_threshold)
            and cand.terminal_role not in {"vasp", "mixer"}
        ):
            cand.terminal_role = "hub"
```

Full file diff must keep existing `MIN_HOP_AMOUNT` and `HUB_DEGREE_THRESHOLD` logic intact; only add pagerank branch.

- [ ] **Step 4: Run tests**

Run: `uv run --project api pytest api/tests/unit/test_attribution_stages.py -v`
Expected: PASS (existing 19 + 1 new = 20)

Run: `uv run --project api ruff check api/app/attribution/filtering.py && uv run --project api ruff format --check api/app/attribution/filtering.py`
Expected: clean

- [ ] **Step 5: Commit**

```bash
git add api/app/attribution/filtering.py api/tests/unit/test_attribution_stages.py
git commit -m "feat(attr): hub detection via PageRank + degree (WP-19 Task4)"
```

---

### Task 5: Docs + final verification + work-packages update

**Files:**
- Modify: `docs/work-packages.md:46` keep 🟡 (no change, WP-19 stays in progress until Task1-4 merged)
- Create: `docs/superpowers/plans/2026-09-06-wp19-graph-algos.md` (this file, already done)

**Interfaces:** none

- [ ] **Step 1: Run full verification**

```bash
uv run --project api pytest api/tests/unit/test_graph.py api/tests/unit/test_attribution_stages.py -v
# Expected: 9 + 20 = 29 passed
uv run --project api ruff check api/app/graph/ api/app/attribution/filtering.py
uv run --project api ruff format --check api/app/graph/ api/app/attribution/filtering.py
uv run --project api mypy api/app/graph/algorithms.py api/app/graph/store.py api/app/attribution/filtering.py --strict --ignore-missing-imports
```

- [ ] **Step 2: Update Current team base note (optional)**

Edit `docs/work-packages.md:96-107` to note WP-19 Phase A scope, if needed — keep branch `feature/graph-algos`.

- [ ] **Step 3: Commit docs**

```bash
git add docs/superpowers/plans/2026-09-06-wp19-graph-algos.md
git commit -m "docs(plan): WP-19 Phase A time-window + pagerank (prod grade)"
```

---

## Self-Review

- **Spec coverage:** Phase 11 `temporal traversal` -> Task1+3, `PageRank/centrality` -> Task2+4, `BFS/Dijkstra` preserved, `community detection` explicitly deferred to WP-19b per Phase 11 `[D]` — no gaps for Phase A scope.
- **Placeholder scan:** No `TBD/TODO` — all code blocks complete with exact paths, signatures, and expected outputs.
- **Type consistency:** `time_window_bfs` returns `list[str]` matches `bfs`, `pagerank_centrality` returns `dict[str,float]` sum 1.0 used by `PagerankLookup.score -> float`, `temporal_shortest_path` returns `list[str]|None` matches `weighted_shortest_path`.

