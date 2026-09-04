"""Offline demo provider (Phase 21 / Phase 22).

This provider is the entry-point for the **entire** offline development
path. It loads the synthetic JSON fixtures under ``data/synthetic/``,
builds in-memory indexes and serves queries via the public
:class:`app.providers.base.BlockchainProvider` ABC.

Activation rule:
    ``Settings.demo_mode is True`` ⇒ :func:`build_default_provider_registry`
    registers this provider under every supported ``chain_code`` (BTC,
    ETH, TRON, BNB, SOL, POLYGON). It is what :mod:`app.providers.factory`
    hands back when DEMO_MODE is on.

Public surface (extends the locked ABC):
    ``get_balance``               – returns 0 (no real balances in demo)
    ``get_transactions``          – queries the in-memory tx index
    ``stream_transactions``       – same index, async iterator
    ``get_block_height``          – max(block_height) for the chain
    ``healthcheck``               – True if the in-memory dataset loaded

Demo-only extra methods (NOT part of the locked contract — see
``docs/contracts.md``):
    ``get_address_labels``        – {address: [label, …]}
    ``get_token_transfers``       – same shape as get_transactions for
                                    token movements (MVP: returns native
                                    transfers only)
    ``get_block``                 – block metadata for a height

The provider is **deterministic** – no I/O, no RNG. Re-running it with
the same JSON files produces identical results.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.core.exceptions import ProviderError
from app.providers.base import BlockchainProvider
from app.providers.canonical import CanonicalTransaction

DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"


# ---------------------------------------------------------------------------
# In-memory data structures
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class _DemoAddress:
    address: str
    chain: str
    case: str
    role: str
    label: str
    vasp_id: str | None = None
    mixer_id: str | None = None
    bridge_id: str | None = None


@dataclass(slots=True, frozen=True)
class _DemoBlock:
    chain: str
    height: int
    timestamp: datetime
    tx_count: int


@dataclass(slots=True)
class DemoDataset:
    """In-memory representation of the synthetic dataset."""

    cases: list[dict[str, Any]]
    addresses: dict[str, _DemoAddress]
    transactions: list[CanonicalTransaction]
    vasps: dict[str, dict[str, Any]]
    bridges: dict[str, dict[str, Any]]
    mixers: dict[str, dict[str, Any]]

    # -- indexes -------------------------------------------------------------
    tx_by_address: dict[tuple[str, str], list[CanonicalTransaction]]
    blocks: dict[tuple[str, int], _DemoBlock]
    height_by_chain: dict[str, int]

    # ----------------------------------------------------------------------- factory
    @classmethod
    def load(cls, dataset_dir: Path | None = None) -> DemoDataset:
        """Load and index every fixture in ``dataset_dir``.

        Raises :class:`app.core.exceptions.ProviderError` if a required
        file is missing or malformed.
        """
        dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
        if not dataset_dir.exists():
            raise ProviderError(f"Synthetic dataset directory not found: {dataset_dir}")

        def _read(name: str) -> dict[str, Any]:
            with (dataset_dir / name).open() as fh:
                return json.load(fh)

        try:
            cases_doc = _read("cases.json")
            addresses_doc = _read("addresses.json")
            transactions_doc = _read("transactions.json")
            vasps_doc = _read("vasps.json")
            bridges_doc = _read("bridges.json")
            mixers_doc = _read("mixers.json")
        except FileNotFoundError as exc:
            raise ProviderError(f"Missing synthetic dataset file: {exc.filename}") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Malformed JSON in synthetic dataset: {exc.msg}") from exc

        # addresses
        addresses: dict[str, _DemoAddress] = {}
        for row in addresses_doc["addresses"]:
            ad = _DemoAddress(
                address=row["address"],
                chain=row["chain"],
                case=row["case"],
                role=row["role"],
                label=row["label"],
                vasp_id=row.get("vasp_id"),
                mixer_id=row.get("mixer_id"),
                bridge_id=row.get("bridge_id"),
            )
            addresses[ad.address] = ad

        # transactions
        txs: list[CanonicalTransaction] = []
        for row in transactions_doc["transactions"]:
            ts_raw = row["block_timestamp"]
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if ts_raw else None
            txs.append(
                CanonicalTransaction(
                    chain=row["chain"],
                    tx_hash=row["tx_hash"],
                    block_height=row.get("block_height"),
                    block_timestamp=ts,
                    from_address=row.get("from_address"),
                    to_address=row.get("to_address"),
                    asset_symbol=row["asset_symbol"],
                    amount=Decimal(str(row["amount"])),
                    fee=Decimal(str(row["fee"])),
                    success=row.get("success", True),
                    raw=dict(row.get("raw", {})) | {"case": row.get("case")},
                )
            )

        # indexes
        tx_by_addr: dict[tuple[str, str], list[CanonicalTransaction]] = defaultdict(list)
        for tx in txs:
            if tx.from_address:
                tx_by_addr[(tx.from_address, tx.chain)].append(tx)
            if tx.to_address:
                tx_by_addr[(tx.to_address, tx.chain)].append(tx)
        for _, value in tx_by_addr.items():
            value.sort(key=lambda t: t.block_timestamp or datetime.min.replace(tzinfo=UTC))

        # blocks
        blocks: dict[tuple[str, int], _DemoBlock] = {}
        height_by_chain: dict[str, int] = defaultdict(int)
        block_tx_count: dict[tuple[str, int], int] = defaultdict(int)
        for tx in txs:
            if tx.block_height is None or tx.block_timestamp is None:
                continue
            block_key = (tx.chain, tx.block_height)
            block_tx_count[block_key] += 1
            if block_key not in blocks:
                blocks[block_key] = _DemoBlock(
                    chain=tx.chain,
                    height=tx.block_height,
                    timestamp=tx.block_timestamp,
                    tx_count=0,
                )
            height_by_chain[tx.chain] = max(height_by_chain[tx.chain], tx.block_height)
        for key, count in block_tx_count.items():
            existing = blocks[key]
            blocks[key] = _DemoBlock(
                chain=existing.chain,
                height=existing.height,
                timestamp=existing.timestamp,
                tx_count=count,
            )

        return cls(
            cases=cases_doc["cases"],
            addresses=addresses,
            transactions=txs,
            vasps={v["id"]: v for v in vasps_doc["vasps"]},
            bridges={b["id"]: b for b in bridges_doc["bridges"]},
            mixers={m["id"]: m for m in mixers_doc["mixers"]},
            tx_by_address=dict(tx_by_addr),
            blocks=blocks,
            height_by_chain=dict(height_by_chain),
        )

    # -------------------------------------------------------------------- helpers
    def cases_for(self, suspect_address: str) -> list[dict[str, Any]]:
        """Return every ``cases.json`` entry whose suspect matches."""
        return [c for c in self.cases if c.get("suspect_address") == suspect_address]

    def addresses_by_role(self, role: str) -> list[_DemoAddress]:
        return [a for a in self.addresses.values() if a.role == role]


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class DemoBlockchainProvider(BlockchainProvider):
    """Concrete :class:`BlockchainProvider` backed by the synthetic dataset.

    The provider only carries an in-memory index — it never touches the
    network. Calling any method is cheap and deterministic.
    """

    chain_code = "demo"

    def __init__(
        self,
        dataset: DemoDataset | None = None,
        *,
        chain_code: str = "demo",
    ) -> None:
        # Per-instance dataset (default load is shared across the registry).
        self._dataset = dataset if dataset is not None else self.get_shared_dataset()
        # The provider can pretend to serve any chain. We override chain_code
        # per instance so the registry can register one demo provider per chain.
        self.chain_code = chain_code

    # -- shared singleton ------------------------------------------------------
    @classmethod
    def get_shared_dataset(cls) -> DemoDataset:
        """Return the process-wide :class:`DemoDataset` (loads on first use)."""
        global _SHARED_DATASET  # noqa: PLW0603
        if _SHARED_DATASET is None:
            _SHARED_DATASET = DemoDataset.load()
        return _SHARED_DATASET

    # -- ABC contract ----------------------------------------------------------
    async def get_balance(self, address: str) -> Decimal:
        return Decimal("0")

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        out: list[CanonicalTransaction] = []
        # The provider is chain-scoped. Look up the address only on the
        # bound chain so cross-chain entries (e.g. bridges) are queried
        # on the right provider instance.
        for tx in self._dataset.tx_by_address.get((address, self.chain_code), []):
            if tx.chain != self.chain_code:
                continue
            if start_time is not None and tx.block_timestamp and tx.block_timestamp < start_time:
                continue
            if end_time is not None and tx.block_timestamp and tx.block_timestamp > end_time:
                continue
            out.append(tx)
        # Also pick up any tx where the address appears on a *different*
        # chain — necessary for bridge addresses that exist on multiple
        # chains. We only return txs whose chain matches ours so the
        # provider's chain scope is preserved.
        for (addr, chain), txs in self._dataset.tx_by_address.items():
            if addr != address or chain == self.chain_code:
                continue
            for tx in txs:
                if tx.chain != self.chain_code:
                    continue
                if (
                    start_time is not None
                    and tx.block_timestamp
                    and tx.block_timestamp < start_time
                ):
                    continue
                if end_time is not None and tx.block_timestamp and tx.block_timestamp > end_time:
                    continue
                out.append(tx)
        out.sort(key=lambda t: t.block_timestamp or datetime.min.replace(tzinfo=UTC))
        return out[:limit]

    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
    ) -> AsyncIterator[CanonicalTransaction]:
        for tx in await self.get_transactions(address, start_time=start_time, limit=10_000):
            yield tx

    async def get_block_height(self) -> int:
        return max(self._dataset.height_by_chain.values(), default=0)

    async def healthcheck(self) -> bool:
        return bool(self._dataset.transactions)

    # -- demo-only extras (NOT in the locked contract) -------------------------
    def get_address_labels(self, address: str) -> list[str]:
        """Return the labels for ``address`` (may be empty)."""
        ad = self._dataset.addresses.get(address)
        return [ad.label] if ad else []

    def get_vasp_id(self, address: str) -> str | None:
        ad = self._dataset.addresses.get(address)
        return ad.vasp_id if ad else None

    def get_mixer_id(self, address: str) -> str | None:
        ad = self._dataset.addresses.get(address)
        return ad.mixer_id if ad else None

    def get_bridge_id(self, address: str) -> str | None:
        ad = self._dataset.addresses.get(address)
        return ad.bridge_id if ad else None

    async def get_token_transfers(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        """MVP: returns the same set as :meth:`get_transactions`.

        Future iterations will differentiate native transfers from ERC-20
        / TRC-20 movements using the ``asset_symbol`` field.
        """
        return await self.get_transactions(
            address, start_time=start_time, end_time=end_time, limit=limit
        )

    async def get_block(self, chain: str, height: int) -> dict[str, Any] | None:
        block = self._dataset.blocks.get((chain, height))
        if not block:
            return None
        return {
            "chain": block.chain,
            "height": block.height,
            "timestamp": block.timestamp.isoformat(),
            "tx_count": block.tx_count,
        }

    # -- helpers ---------------------------------------------------------------
    def _chains_for_address(self, address: str) -> set[str]:
        """Chains where ``address`` has any tx involvement.

        A provider instance is bound to a single ``chain_code`` via the
        constructor. The lookup favours ``self.chain_code`` so the
        provider acts as a chain-scoped view over the dataset, but we
        also include other chains the address appears on so cross-chain
        bridges (where one address has roles on two chains) are still
        discoverable. Callers must filter the returned txs by
        ``tx.chain``.
        """
        chains: set[str] = set()
        ad = self._dataset.addresses.get(address)
        if ad:
            chains.add(ad.chain)
        # Address may appear in transactions on chains not present in
        # addresses.json – infer from the tx index.
        for (addr, chain), _ in self._dataset.tx_by_address.items():
            if addr == address:
                chains.add(chain)
        # Always include the provider's bound chain even if the address
        # isn't indexed there yet (defensive).
        chains.add(self.chain_code)
        return chains


_SHARED_DATASET: DemoDataset | None = None


def reset_shared_dataset() -> None:
    """Drop the in-memory dataset (used by tests)."""
    global _SHARED_DATASET  # noqa: PLW0603
    _SHARED_DATASET = None


def raise_not_implemented(provider: str) -> ProviderError:
    """Helper used by the per-chain stubs (kept here to avoid cycles)."""
    return ProviderError(f"Provider '{provider}' is not implemented yet (Stage 1).")


__all__ = [
    "DemoBlockchainProvider",
    "DemoDataset",
    "DEFAULT_DATASET_DIR",
    "reset_shared_dataset",
    "raise_not_implemented",
]
