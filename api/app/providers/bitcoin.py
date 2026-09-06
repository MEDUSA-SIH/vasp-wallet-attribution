"""Bitcoin live provider — QuickNode Blockbook JSON-RPC (Phase 20, WP-03)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BlockchainProvider
from app.providers.canonical import CanonicalTransaction

_DEFAULT_BASE_URL = ""
_SATS_PER_BTC = Decimal(10) ** 8
_PAGE_SIZE = 100


class BitcoinProvider(BlockchainProvider):
    """Live Bitcoin provider backed by QuickNode Blockbook (`bb_getAddress`)."""

    chain_code = "bitcoin"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._base_url = (self._settings.bitcoin_provider_url or _DEFAULT_BASE_URL).rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._req_id = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_balance(self, address: str) -> Decimal:
        res = await self._rpc(
            "bb_getAddress", [address, {"page": 1, "size": 1, "details": "basic"}]
        )
        try:
            return Decimal(str(res.get("balance", "0"))) / _SATS_PER_BTC
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise ProviderError("Bitcoin provider: bad balance payload") from exc

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        rows: list[dict[str, Any]] = []
        page = 1
        total: int | None = None
        while len(rows) < limit:
            res = await self._rpc(
                "bb_getAddress",
                [address, {"page": page, "size": _PAGE_SIZE, "details": "txs"}],
            )
            batch = res.get("transactions", []) or []
            if total is None:
                total = int(res.get("txs", len(batch)) or len(batch))
            if not batch:
                break
            rows.extend(batch)
            if len(rows) >= (total or 0) or len(batch) < _PAGE_SIZE:
                break
            page += 1
        txs = [self._to_canonical(address, r) for r in rows]
        txs.sort(key=lambda t: t.block_timestamp or datetime.min.replace(tzinfo=UTC))
        if start_time is not None:
            txs = [t for t in txs if t.block_timestamp is None or t.block_timestamp >= start_time]
        if end_time is not None:
            txs = [t for t in txs if t.block_timestamp is None or t.block_timestamp <= end_time]
        return txs[:limit]

    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
    ) -> AsyncIterator[CanonicalTransaction]:
        for tx in await self.get_transactions(address, start_time=start_time, limit=10_000):
            yield tx

    async def get_block_height(self) -> int:
        try:
            res = await self._rpc("getblockchaininfo", [])
            return int(res["blocks"])
        except (ProviderError, KeyError, ValueError, TypeError):
            res = await self._rpc("getblockcount", [])
            if isinstance(res, int):
                return res
            raise ProviderError("Bitcoin provider: bad block height") from None

    async def healthcheck(self) -> bool:
        try:
            await self.get_block_height()
        except ProviderError:
            return False
        return True

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        import asyncio

        if not self._base_url:
            raise ProviderError("Bitcoin provider: BITCOIN_PROVIDER_URL is not set")
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": self._req_id, "method": method, "params": params}
        for attempt in range(2):
            try:
                resp = await self._client.post(self._base_url, json=payload)
            except httpx.HTTPError as exc:
                raise ProviderError("Bitcoin provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code >= 400:
                raise ProviderError(f"Bitcoin provider error: HTTP {resp.status_code}")
            try:
                data = resp.json()
            except ValueError as exc:
                raise ProviderError("Bitcoin provider: bad JSON") from exc
            if isinstance(data, dict) and data.get("error"):
                msg = str(data["error"].get("message", data["error"]))[:160]
                if (
                    any(m in msg.lower() for m in ("rate limit", "too many", "throttle"))
                    and attempt == 0
                ):
                    await asyncio.sleep(1.0)
                    continue
                if "method not found" in msg.lower() and method.startswith("bb_"):
                    raise ProviderError(
                        "Bitcoin provider: bb_getAddress unavailable" " — enable Blockbook add-on"
                    )
                raise ProviderError(f"Bitcoin provider error: {msg!r}")
            return data.get("result") if isinstance(data, dict) else data
        raise ProviderError("Bitcoin provider error: rate limited")

    def _to_canonical(self, queried: str, row: dict[str, Any]) -> CanonicalTransaction:
        vins = row.get("vin", []) or []
        vouts = row.get("vout", []) or []
        recv = sum(
            int(v.get("value", 0) or 0) for v in vouts if queried in (v.get("addresses") or [])
        )
        sent = sum(int(v.get("value", 0) or 0) for v in vins if v.get("isOwn") is True)
        if recv > 0 and sent == 0:
            from_addr = next(
                (a for v in vins for a in (v.get("addresses") or []) if a and v.get("isAddress")),
                None,
            )
            to_addr: str | None = queried
            amount = Decimal(recv) / _SATS_PER_BTC
        elif sent > 0:
            from_addr = queried
            to_addr = next(
                (a for v in vouts for a in (v.get("addresses") or []) if a and a != queried),
                None,
            )
            amount = Decimal(sent) / _SATS_PER_BTC
        else:
            from_addr, to_addr, amount = None, queried, Decimal("0")
        try:
            fee = Decimal(str(row.get("fees", 0) or 0)) / _SATS_PER_BTC
        except InvalidOperation:
            fee = Decimal("0")
        bt = row.get("blockTime")
        try:
            ts = datetime.fromtimestamp(int(bt), tz=UTC) if bt else None
        except (ValueError, TypeError, OSError, OverflowError):
            ts = None
        height = row.get("height", row.get("blockHeight"))
        try:
            bh = int(height) if height is not None and int(height) >= 0 else None
        except (ValueError, TypeError):
            bh = None
        conf = row.get("confirmations", 1)
        try:
            success = conf is None or int(conf or 0) >= 0
        except (ValueError, TypeError):
            success = True
        return CanonicalTransaction(
            chain="bitcoin",
            tx_hash=str(row.get("txid", "")),
            block_height=bh,
            block_timestamp=ts,
            from_address=(str(from_addr) if from_addr else None),
            to_address=(str(to_addr) if to_addr else None),
            asset_symbol="BTC",
            amount=amount,
            fee=fee,
            success=success,
            raw=dict(row) | {"source": "quicknode-bb", "kind": "btc"},
        )


__all__ = ["BitcoinProvider"]
