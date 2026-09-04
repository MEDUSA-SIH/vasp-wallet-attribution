"""Attribution orchestration service (Phase 10 + Phase 11).

Public surface:

    ``AttributionService.run_demo_attribution(suspect, chain, case_id, registry)``

    Returns a structured :class:`AttributionRunResult` that powers the
    smoke endpoint ``POST /api/v1/attribution/run`` described in
    ``docs/work-packages.md`` WP-11.

The service:

1. Pulls transactions touching ``suspect`` from the chain-specific
   provider in the supplied :class:`ProviderRegistry`.
2. Performs a bounded BFS through the multi-hop wallet graph (one
   ``DemoBlockchainProvider`` per chain, mirroring the real-world
   provider split).
3. Classifies each candidate wallet:
     - ``vasp`` – belongs to a known VASP (via :class:`DemoDataset`).
     - ``mixer`` – mixer-tagged; hops stop here.
     - ``bridge`` – bridge-tagged; we follow the bridge tx to the
       target chain.
     - ``hub`` – high-degree intermediary (Case 7).
     - ``dead_end`` – no outgoing hops.
     - ``intermediary`` – otherwise.
4. Computes a **placeholder** confidence score (1 / (1 + hops)) so the
   ranking is monotonic in distance; real scoring formulas are out of
   scope (see WP-14, WP-15).
5. Returns the rankings + a high-level ``outcome`` field
   (``single_candidate``, ``ranked_multi_candidate``, etc.) so callers
   can assert expected behaviour in tests.

The method is the **smoke path** that WP-11 promises. It must remain
deterministic and fast.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.attribution.engine import AttributionEngine
from app.providers.base import BlockchainProvider, ProviderRegistry
from app.providers.canonical import CanonicalTransaction

DEFAULT_MAX_HOPS = 5


@dataclass(slots=True)
class CandidatePath:
    """One candidate path from the suspect to a downstream wallet."""

    hops: int
    nodes: list[str]
    transactions: list[str]  # tx_hashes
    endpoint_role: str  # "vasp" | "mixer" | "bridge" | "hub" | "dead_end" | "intermediary"
    endpoint_address: str
    endpoint_label: str | None = None
    vasp_id: str | None = None
    bridge_id: str | None = None
    mixer_id: str | None = None
    amount_total: float = 0.0
    confidence: float = 0.0
    evidence_tier: str = "tier_0_demo"  # WP-25 will replace with real tiers

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AttributionRunResult:
    """Outcome of ``AttributionService.run_demo_attribution``."""

    run_id: UUID
    case_id: UUID | None
    suspect_address: str
    chain: str
    outcome: str
    demo_mode: bool
    candidates: list[CandidatePath] = field(default_factory=list)
    hops_used: int = 0
    insufficient_evidence: bool = False
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["run_id"] = str(self.run_id)
        if self.case_id is not None:
            d["case_id"] = str(self.case_id)
        d["started_at"] = self.started_at.isoformat()
        d["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        d["candidates"] = [c.as_dict() for c in self.candidates]
        return d


class AttributionService:
    """Glue between the API, the providers and the :class:`AttributionEngine`."""

    def __init__(self, engine: AttributionEngine | None = None) -> None:
        self.engine = engine or AttributionEngine()

    async def run(self, case_id: UUID, seeds: list[str]) -> Any:
        """Thin wrapper around the engine. See :class:`AttributionEngine`."""
        return await self.engine.run(case_id, seeds)

    async def run_demo_attribution(
        self,
        suspect_address: str,
        *,
        chain: str = "ethereum",
        case_id: UUID | None = None,
        registry: ProviderRegistry,
        max_hops: int = DEFAULT_MAX_HOPS,
    ) -> AttributionRunResult:
        """Bounded BFS over the demo provider graph.

        Honours the public contracts in ``docs/contracts.md`` (Phase 10):
        - calls ``provider.get_transactions(address)``,
        - respects ``Settings.attribution_max_hops``,
        - returns a structured :class:`AttributionRunResult`.

        The method is the smoke path for WP-11. It does NOT implement
        real scoring (WP-14) or ranking (WP-15) – both are stubs.
        """
        provider = registry.get(chain)
        run_id = uuid4()
        result = AttributionRunResult(
            run_id=run_id,
            case_id=case_id,
            suspect_address=suspect_address,
            chain=chain,
            outcome="insufficient_evidence",
            demo_mode=getattr(provider, "_dataset", None) is not None
            or provider.__class__.__name__ == "DemoBlockchainProvider",
            insufficient_evidence=False,
        )

        visited: set[tuple[str, str]] = {(suspect_address, chain)}
        frontier: list[tuple[str, str, int, list[str], list[str], float]] = [
            (suspect_address, chain, 0, [suspect_address], [], 0.0)
        ]
        candidates: list[CandidatePath] = []
        end_time = datetime.utcnow()

        while frontier:
            addr, c, hops, path, tx_path, amount = frontier.pop(0)
            if hops >= max_hops:
                continue

            txs = await provider.get_transactions(addr)
            outgoing = [t for t in txs if t.from_address == addr]

            if not outgoing and hops > 0:
                # No outgoing hops → dead-end candidate.
                cand = CandidatePath(
                    hops=hops,
                    nodes=list(path),
                    transactions=list(tx_path),
                    endpoint_role="dead_end",
                    endpoint_address=addr,
                    amount_total=amount,
                    confidence=1.0 / (1 + hops),
                )
                candidates.append(cand)
                continue

            for tx in outgoing:
                if tx.to_address is None:
                    continue
                next_addr = tx.to_address
                next_chain = _target_chain_for_bridge_tx(provider, tx, c)
                key = (next_addr, next_chain)
                if key in visited:
                    continue
                visited.add(key)
                next_amount = amount + float(tx.amount)
                classification = _classify_address(provider, next_addr)

                if classification["router"] == "mixer":
                    cand = CandidatePath(
                        hops=hops + 1,
                        nodes=list(path) + [next_addr],
                        transactions=list(tx_path) + [tx.tx_hash],
                        endpoint_role="mixer",
                        endpoint_address=next_addr,
                        endpoint_label=classification.get("label"),
                        mixer_id=classification.get("mixer_id"),
                        amount_total=next_amount,
                        confidence=1.0 / (1 + hops + 1),
                        evidence_tier="tier_1_mixer_stop",
                    )
                    candidates.append(cand)
                    continue

                if classification["router"] == "vasp":
                    cand = CandidatePath(
                        hops=hops + 1,
                        nodes=list(path) + [next_addr],
                        transactions=list(tx_path) + [tx.tx_hash],
                        endpoint_role="vasp",
                        endpoint_address=next_addr,
                        endpoint_label=classification.get("label"),
                        vasp_id=classification.get("vasp_id"),
                        amount_total=next_amount,
                        confidence=_demo_confidence(hops + 1),
                        evidence_tier="tier_2_demo_vasp",
                    )
                    candidates.append(cand)
                    continue

                if classification["router"] == "bridge":
                    # Record the bridge as a candidate and follow it on
                    # the target chain when possible.
                    bridge_id = classification.get("bridge_id")
                    follow = _follow_bridge(registry, provider, tx, next_chain)
                    if follow is not None:
                        bridge_provider, _bridge_chain = follow
                        bridge_txs = await bridge_provider.get_transactions(next_addr)
                        for btx in bridge_txs:
                            if btx.to_address is None or btx.to_address in {n for n, _ in visited}:
                                continue
                            visited.add((btx.to_address, bridge_provider.chain_code))
                            target_class = _classify_address(bridge_provider, btx.to_address)
                            if target_class["router"] == "vasp":
                                cand = CandidatePath(
                                    hops=hops + 2,
                                    nodes=list(path) + [next_addr, btx.to_address],
                                    transactions=list(tx_path) + [tx.tx_hash, btx.tx_hash],
                                    endpoint_role="vasp",
                                    endpoint_address=btx.to_address,
                                    endpoint_label=target_class.get("label"),
                                    vasp_id=target_class.get("vasp_id"),
                                    bridge_id=bridge_id,
                                    amount_total=float(btx.amount),
                                    confidence=_demo_confidence(hops + 2, decay_for_bridge=True),
                                    evidence_tier="tier_3_demo_bridge",
                                )
                                candidates.append(cand)
                    continue

                # Hub detection: very common in Case 7 – if degree > 4
                # and no VASP tag, mark as a hub and stop expanding.
                if _is_high_degree(provider, next_addr, threshold=4):
                    cand = CandidatePath(
                        hops=hops + 1,
                        nodes=list(path) + [next_addr],
                        transactions=list(tx_path) + [tx.tx_hash],
                        endpoint_role="hub",
                        endpoint_address=next_addr,
                        endpoint_label=classification.get("label"),
                        amount_total=next_amount,
                        confidence=_demo_confidence(hops + 1, decay_for_hub=True),
                        evidence_tier="tier_0_demo",
                    )
                    candidates.append(cand)
                    continue

                # Otherwise keep expanding.
                frontier.append(
                    (next_addr, next_chain, hops + 1, list(path) + [next_addr],
                     list(tx_path) + [tx.tx_hash], next_amount)
                )

        result.candidates = _rank_candidates(candidates)
        result.hops_used = max((c.hops for c in candidates), default=0)
        result.outcome = _classify_outcome(result.candidates)
        if result.outcome == "insufficient_evidence":
            result.insufficient_evidence = True
        result.notes.append(
            "Scoring is a placeholder (1/(1+hops)). Real formulas land in WP-14/15."
        )
        result.finished_at = datetime.utcnow()
        _ = end_time  # silence linters; reserved for future latency tracking
        return result


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _classify_address(provider: BlockchainProvider, address: str) -> dict[str, Any]:
    """Inspect the demo dataset for tags attached to ``address``."""
    # Demo provider exposes these helpers explicitly.
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


def _is_high_degree(provider: BlockchainProvider, address: str, *, threshold: int = 4) -> bool:
    """Crude hub detector: more than ``threshold`` distinct txs touch ``address``.

    The :class:`DemoDataset` indexes each tx under both (from, chain) and
    (to, chain), so we de-duplicate by ``tx_hash`` before counting.
    """
    if not hasattr(provider, "_dataset"):
        return False
    dataset = provider._dataset  # type: ignore[attr-defined]
    seen: set[str] = set()
    for txs in dataset.tx_by_address.values():
        for tx in txs:
            if tx.from_address == address or tx.to_address == address:
                seen.add(tx.tx_hash)
    return len(seen) > threshold


def _target_chain_for_bridge_tx(
    provider: BlockchainProvider, tx: CanonicalTransaction, current_chain: str,
) -> str:
    """Return the target chain for ``tx`` if it is a bridge hop, else current."""
    raw = tx.raw or {}
    target = raw.get("bridge_target_chain")
    if isinstance(target, str):
        return target
    return current_chain


def _follow_bridge(
    registry: ProviderRegistry,
    source_provider: BlockchainProvider,
    tx: CanonicalTransaction,
    target_chain: str,
) -> tuple[BlockchainProvider, str] | None:
    """Return a provider for ``target_chain`` if registered."""
    try:
        return registry.get(target_chain), target_chain
    except KeyError:
        return None


def _demo_confidence(hops: int, *, decay_for_bridge: bool = False, decay_for_hub: bool = False) -> float:
    """Placeholder confidence: monotonic in hops, with extra decay for riskier paths."""
    base = 1.0 / (1 + hops)
    if decay_for_bridge:
        base *= 0.85
    if decay_for_hub:
        base *= 0.5
    return round(base, 4)


def _rank_candidates(candidates: Iterable[CandidatePath]) -> list[CandidatePath]:
    """Stable sort: VASPs first, then by confidence desc, then by hops asc."""
    priority = {"vasp": 0, "intermediary": 1, "dead_end": 2, "hub": 3, "mixer": 4, "bridge": 5}
    return sorted(
        candidates,
        key=lambda c: (
            priority.get(c.endpoint_role, 99),
            -c.confidence,
            c.hops,
            c.endpoint_address,
        ),
    )


def _classify_outcome(candidates: list[CandidatePath]) -> str:
    vasp_candidates = [c for c in candidates if c.endpoint_role == "vasp"]
    if vasp_candidates:
        if len(vasp_candidates) == 1:
            return "single_candidate"
        return "ranked_multi_candidate"
    if any(c.endpoint_role == "mixer" for c in candidates):
        return "insufficient_evidence"
    if any(c.endpoint_role == "hub" for c in candidates):
        return "false_candidate_filtered"
    if any(c.endpoint_role == "dead_end" for c in candidates):
        return "insufficient_evidence"
    return "insufficient_evidence"


__all__ = [
    "AttributionService",
    "AttributionRunResult",
    "CandidatePath",
]