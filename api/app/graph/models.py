"""Graph node/edge type definitions (Phase 6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class NodeKind(StrEnum):
    """Types of nodes stored in the transaction graph."""

    WALLET = "wallet"
    VASP = "vasp"
    TRANSACTION = "transaction"
    ADDRESS = "address"  # cross-chain alias
    CLUSTER = "cluster"


class EdgeKind(StrEnum):
    """Types of edges stored in the transaction graph."""

    TRANSFER = "transfer"  # wallet → wallet transfer
    CONTROL = "control"  # cluster → wallet membership
    ATTRIBUTION = "attribution"  # wallet → vasp attribution
    BRIDGE = "bridge"  # cross-chain bridge hop
    ALIAS = "alias"  # same owner across chains


@dataclass(slots=True, frozen=True)
class GraphNode:
    """A node in the multi-chain transaction graph."""

    id: str
    kind: NodeKind
    chain: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class GraphEdge:
    """A directed edge between two nodes."""

    source: str
    target: str
    kind: EdgeKind
    weight: float = 1.0
    attributes: dict[str, Any] = field(default_factory=dict)


__all__ = ["NodeKind", "EdgeKind", "GraphNode", "GraphEdge"]
