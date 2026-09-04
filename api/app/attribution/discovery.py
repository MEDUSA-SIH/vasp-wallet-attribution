"""Stage A — Candidate discovery (Phase 10 / Phase 22).

Bounded forward BFS from the suspect address. Stops at the configured
hop budget OR when a node has already been visited. Returns a list of
:class:`Candidate` objects, each carrying the full path of addresses
and edges, plus tag annotations for VASP / mixer / bridge.

The stage is **chain-aware**: when a hop carries a
``bridge_target_chain`` marker, the BFS follows the bridge to the
target chain via the appropriate provider.

The stage honours the Phase 14 hard rule on mixers: as soon as a mixer
is hit the BFS stops expanding past it (see :func:`_is_mixer`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.attribution.types import Candidate, HopEdge
from app.providers.base import ProviderRegistry
from app.providers.canonical import CanonicalTransaction

if TYPE_CHECKING:
    from app.attribution.filtering import DegreeLookup

HUB_DEGREE_THRESHOLD = 4  # > 4 distinct txs = hub (mirrors filtering.py)


async def run_discovery(
    suspect_address: str,
    *,
    registry: ProviderRegistry,
    chain: str = "ethereum",
    max_hops: int = 5,
    max_candidates: int = 64,
    degree_lookup: DegreeLookup | None = None,
) -> list[Candidate]:
    """Forward BFS, returning every terminal :class:`Candidate`.

    A *terminal* is a node that:
      - is tagged as a VASP / mixer / bridge,
      - is a hub (high-degree, no VASP tag),
      - has no outgoing hops within the budget,
      - or has been visited already (cycle detection).
    """
    if max_hops < 1:
        return []
    provider = registry.get(chain)
    visited: set[tuple[str, str]] = {(suspect_address, chain)}
    frontier: list[_Node] = [
        _Node(addr=suspect_address, chain=chain, hops=0, path=[suspect_address], edges=[])
    ]
    candidates: list[Candidate] = []

    while frontier and len(candidates) < max_candidates:
        node = frontier.pop(0)
        txs = await provider.get_transactions(node.addr)
        outgoing = [t for t in txs if t.from_address == node.addr]

        if not outgoing and node.hops > 0:
            candidates.append(
                _candidate_for_dead_end(node, chain)
            )
            continue

        for tx in outgoing:
            if tx.to_address is None:
                continue
            next_addr = tx.to_address
            next_chain = _target_chain_for_bridge_tx(tx, node.chain)
            key = (next_addr, next_chain)
            if key in visited:
                continue
            visited.add(key)

            tag = _classify(provider, next_addr)
            new_node = _Node(
                addr=next_addr,
                chain=next_chain,
                hops=node.hops + 1,
                path=node.path + [next_addr],
                edges=node.edges + [_edge_for(tx)],
            )

            if tag["router"] == "mixer":
                candidates.append(
                    _candidate_for_terminal(
                        new_node,
                        role="mixer",
                        label=tag.get("label"),
                        vasp_id=None,
                        mixer_id=tag.get("mixer_id"),
                        bridge_id=None,
                    )
                )
                continue

            if tag["router"] == "vasp":
                candidates.append(
                    _candidate_for_terminal(
                        new_node,
                        role="vasp",
                        label=tag.get("label"),
                        vasp_id=tag.get("vasp_id"),
                        mixer_id=None,
                        bridge_id=None,
                    )
                )
                continue

            if tag["router"] == "bridge":
                # Materialise the bridge hop, then try to follow it on the
                # target chain. The downstream path lives on the target
                # chain's provider.
                follow = _follow_bridge(registry, next_chain, next_addr)
                if follow is not None:
                    bridge_provider, bridge_chain = follow
                    downstream_txs = await bridge_provider.get_transactions(next_addr)
                    downstream_outgoing = [
                        t for t in downstream_txs if t.from_address == next_addr
                    ]
                    for dtx in downstream_outgoing:
                        if dtx.to_address is None:
                            continue
                        if (dtx.to_address, bridge_chain) in visited:
                            continue
                        visited.add((dtx.to_address, bridge_chain))
                        dtag = _classify(bridge_provider, dtx.to_address)
                        cand_node = _Node(
                            addr=dtx.to_address,
                            chain=bridge_chain,
                            hops=new_node.hops + 1,
                            path=new_node.path + [dtx.to_address],
                            edges=new_node.edges + [_edge_for(dtx)],
                        )
                        if dtag["router"] == "vasp":
                            candidates.append(
                                _candidate_for_terminal(
                                    cand_node,
                                    role="vasp",
                                    label=dtag.get("label"),
                                    vasp_id=dtag.get("vasp_id"),
                                    mixer_id=None,
                                    bridge_id=tag.get("bridge_id"),
                                    crosses_bridge=True,
                                )
                            )
                            continue
                        if dtag["router"] == "mixer":
                            candidates.append(
                                _candidate_for_terminal(
                                    cand_node,
                                    role="mixer",
                                    label=dtag.get("label"),
                                    vasp_id=None,
                                    mixer_id=dtag.get("mixer_id"),
                                    bridge_id=tag.get("bridge_id"),
                                    crosses_bridge=True,
                                )
                            )
                            continue
                        # Otherwise treat as a non-terminal hop on the
                        # target chain. The frontier loop continues to
                        # walk it on the bridge provider.
                        if cand_node.hops < max_hops:
                            frontier.append(cand_node)
                # Bridge node itself is not a candidate — we already walked
                # across it. Continue.
                continue

            # Intermediary / hub / dead_end.
            # Hub detection: if the address has very high degree and no
            # VASP tag, stop expanding (Stage C applies the formal filter).
            if (
                degree_lookup is not None
                and degree_lookup.degree(next_addr) > HUB_DEGREE_THRESHOLD
            ):
                candidates.append(
                    _candidate_for_terminal(
                        new_node,
                        role="hub",
                        label=tag.get("label"),
                        vasp_id=None,
                        mixer_id=None,
                        bridge_id=None,
                    )
                )
                continue

            if new_node.hops < max_hops:
                frontier.append(new_node)

    return candidates


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class _Node:
    addr: str
    chain: str
    hops: int
    path: list[str]
    edges: list[HopEdge]


def _classify(provider: Any, address: str) -> dict[str, Any]:
    """Return a tag dict for ``address`` (uses demo helpers when present)."""
    if hasattr(provider, "get_vasp_id"):
        vasp_id = provider.get_vasp_id(address)
        if vasp_id:
            return {
                "router": "vasp",
                "vasp_id": vasp_id,
                "label": (provider.get_address_labels(address) or [None])[0],
            }
    if hasattr(provider, "get_mixer_id"):
        mixer_id = provider.get_mixer_id(address)
        if mixer_id:
            return {
                "router": "mixer",
                "mixer_id": mixer_id,
                "label": (provider.get_address_labels(address) or [None])[0],
            }
    if hasattr(provider, "get_bridge_id"):
        bridge_id = provider.get_bridge_id(address)
        if bridge_id:
            return {
                "router": "bridge",
                "bridge_id": bridge_id,
                "label": (provider.get_address_labels(address) or [None])[0],
            }
    labels = provider.get_address_labels(address) if hasattr(provider, "get_address_labels") else []
    return {"router": "intermediary", "label": (labels or [None])[0]}


def _target_chain_for_bridge_tx(tx: CanonicalTransaction, current_chain: str) -> str:
    raw = tx.raw or {}
    target = raw.get("bridge_target_chain")
    if isinstance(target, str):
        return target
    return current_chain


def _follow_bridge(
    registry: ProviderRegistry, target_chain: str, _: str,
) -> tuple[Any, str] | None:
    try:
        return registry.get(target_chain), target_chain
    except KeyError:
        return None


def _edge_for(tx: CanonicalTransaction) -> HopEdge:
    return HopEdge(
        tx_hash=tx.tx_hash,
        chain=tx.chain,
        from_address=tx.from_address or "",
        to_address=tx.to_address or "",
        timestamp=tx.block_timestamp.isoformat() if tx.block_timestamp else None,
        amount=float(tx.amount),
        asset_symbol=tx.asset_symbol,
    )


def _candidate_for_dead_end(node: _Node, chain: str) -> Candidate:
    first_seen, last_seen = _first_last(node)
    return Candidate(
        suspect_address=node.path[0],
        terminal_address=node.addr,
        terminal_role="dead_end",
        chain=chain,
        hops=node.hops,
        path=list(node.path),
        edges=list(node.edges),
        total_amount=sum(e.amount for e in node.edges),
        first_seen_at=first_seen,
        last_seen_at=last_seen,
    )


def _candidate_for_terminal(
    node: _Node,
    *,
    role: str,
    label: str | None,
    vasp_id: str | None,
    mixer_id: str | None,
    bridge_id: str | None,
    crosses_bridge: bool = False,
) -> Candidate:
    first_seen, last_seen = _first_last(node)
    return Candidate(
        suspect_address=node.path[0],
        terminal_address=node.addr,
        terminal_role=role,
        terminal_label=label,
        chain=node.chain,
        hops=node.hops,
        path=list(node.path),
        edges=list(node.edges),
        crosses_bridge=crosses_bridge or bool(bridge_id),
        bridge_id=bridge_id,
        hits_mixer=role == "mixer",
        mixer_id=mixer_id,
        vasp_id=vasp_id,
        total_amount=sum(e.amount for e in node.edges),
        first_seen_at=first_seen,
        last_seen_at=last_seen,
    )


def _first_last(node: _Node) -> tuple[str | None, str | None]:
    ts = [e.timestamp for e in node.edges if e.timestamp]
    if not ts:
        return None, None
    return ts[0], ts[-1]


def _is_mixer(provider: Any, address: str) -> bool:
    return bool(getattr(provider, "get_mixer_id", lambda a: None)(address))


__all__ = ["run_discovery"]