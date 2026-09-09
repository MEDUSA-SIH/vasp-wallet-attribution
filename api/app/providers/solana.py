"""Solana live provider — Tatum gateway JSON-RPC (Phase 20, WP-07)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.core.exceptions import ProviderError
from app.providers.base import BlockchainProvider
from app.providers.canonical import CanonicalTransaction

_DEFAULT_GATEWAY_URL = "https://solana-mainnet.gateway.tatum.io"
_LAMPORTS_PER_SOL = Decimal(10) ** 9


class SolanaProvider(BlockchainProvider):
    """Live Solana provider backed by Tatum gateway JSON-RPC."""

    chain_code = "solana"

    def __init__(
        self, settings: Settings | None = None, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._gateway_url = (self._settings.solana_provider_url or _DEFAULT_GATEWAY_URL).rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._req_id = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        key = self._settings.blockchain_api_key
        if not key:
            raise ProviderError("Solana provider: BLOCKCHAIN_API_KEY is not set")
        return {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": key,
        }

    async def _rpc_post(self, method: str, params: list[Any]) -> Any:
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": self._req_id, "method": method, "params": params}
        for attempt in range(2):
            try:
                resp = await self._client.post(
                    self._gateway_url, headers=self._headers(), json=payload
                )
            except httpx.HTTPError as exc:
                raise ProviderError("Solana provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code in (401, 403):
                raise ProviderError("Solana provider: unauthorized — check BLOCKCHAIN_API_KEY")
            if resp.status_code >= 400:
                raise ProviderError(f"Solana provider error: HTTP {resp.status_code}")
            try:
                data = resp.json()
            except ValueError as exc:
                raise ProviderError("Solana provider: bad JSON") from exc
            if isinstance(data, dict) and data.get("error"):
                err = data["error"]
                msg = str(err.get("message", err) if isinstance(err, dict) else err)[:160]
                raise ProviderError(f"Solana provider error: {msg!r}")
            return data.get("result") if isinstance(data, dict) else data
        raise ProviderError("Solana provider error: rate limited")

    async def get_balance(self, address: str) -> Decimal:
        result = await self._rpc_post("getBalance", [address])
        try:
            lamports = result.get("value", 0) if isinstance(result, dict) else 0
            return Decimal(str(lamports)) / _LAMPORTS_PER_SOL
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise ProviderError("Solana provider: bad balance payload") from exc

    async def get_block_height(self) -> int:
        result = await self._rpc_post("getBlockHeight", [])
        try:
            return int(str(result)) if not isinstance(result, int) else result
        except (ValueError, TypeError) as exc:
            raise ProviderError("Solana provider: bad block height") from exc

    async def healthcheck(self) -> bool:
        try:
            await self.get_block_height()
        except ProviderError:
            return False
        return True

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        sigs: list[dict[str, Any]] = []
        before: str | None = None
        while len(sigs) < limit:
            opt: dict[str, Any] = {
                "limit": min(max(limit - len(sigs), 1), 1000),
                "commitment": "finalized",
            }
            if before:
                opt["before"] = before
            batch = await self._rpc_post("getSignaturesForAddress", [address, opt])
            if not isinstance(batch, list) or not batch:
                break
            sigs.extend(r for r in batch if isinstance(r, dict) and r.get("signature"))
            sig_rows = [r for r in batch if isinstance(r, dict) and r.get("signature")]
            before = str(sig_rows[-1].get("signature")) if sig_rows else before
            if len(batch) < opt["limit"]:
                break
        out: list[CanonicalTransaction] = []
        for row in sigs[:limit]:
            sig = str(row.get("signature"))
            detail = await self._rpc_post(
                "getTransaction", [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
            )
            if not isinstance(detail, dict):
                continue
            out.append(self._to_canonical(address, row, sig, detail))
        out.sort(key=lambda t: t.block_timestamp or datetime.min.replace(tzinfo=UTC))
        if start_time is not None:
            out = [t for t in out if t.block_timestamp is None or t.block_timestamp > start_time]
        if end_time is not None:
            out = [t for t in out if t.block_timestamp is None or t.block_timestamp <= end_time]
        return out[:limit]

    def _to_canonical(
        self, address: str, sig_row: dict[str, Any], sig: str, detail: dict[str, Any]
    ) -> CanonicalTransaction:
        meta = detail.get("meta") if isinstance(detail.get("meta"), dict) else {}
        msg = (
            detail.get("transaction", {}).get("message", {})
            if isinstance(detail.get("transaction"), dict)
            else {}
        )
        keys = msg.get("accountKeys", []) if isinstance(msg, dict) else []
        keys = [str(k) for k in keys if isinstance(k, str)]
        pre = meta.get("preBalances", []) if isinstance(meta.get("preBalances"), list) else []
        post = meta.get("postBalances", []) if isinstance(meta.get("postBalances"), list) else []
        increase, to_addr = Decimal("0"), None
        for i, k in enumerate(keys):
            try:
                delta = (
                    Decimal(str(post[i])) - Decimal(str(pre[i]))
                    if i < len(pre) and i < len(post)
                    else Decimal("0")
                )
            except (InvalidOperation, ValueError):
                delta = Decimal("0")
            if delta > increase:
                increase, to_addr = delta, k
        try:
            amount = increase / _LAMPORTS_PER_SOL
        except (InvalidOperation, ValueError):
            amount = Decimal("0")
        try:
            fee = Decimal(str(meta.get("fee", 0) or 0)) / _LAMPORTS_PER_SOL
        except (InvalidOperation, ValueError):
            fee = Decimal("0")
        from_addr = keys[0] if keys else None
        if to_addr is None:
            to_addr = address if address in keys else (keys[1] if len(keys) > 1 else None)
        bt_raw = detail.get("blockTime")
        bt = bt_raw if bt_raw is not None else sig_row.get("blockTime")
        try:
            ts = datetime.fromtimestamp(int(str(bt)), tz=UTC) if bt is not None else None
        except (ValueError, TypeError, OSError, OverflowError):
            ts = None
        slot_raw = detail.get("slot")
        slot = slot_raw if slot_raw is not None else sig_row.get("slot")
        try:
            bh = int(str(slot)) if slot is not None and int(str(slot)) >= 0 else None
        except (ValueError, TypeError):
            bh = None
        return CanonicalTransaction(
            chain="solana",
            tx_hash=sig,
            block_height=bh,
            block_timestamp=ts,
            from_address=(str(from_addr) if from_addr else None),
            to_address=(str(to_addr) if to_addr else None),
            asset_symbol="SOL",
            amount=amount,
            fee=fee,
            success=(meta.get("err") is None),
            raw={"source": "solana-rpc", "signature": sig_row, "detail": detail},
        )

    async def stream_transactions(
        self, address: str, *, start_time: Any = None
    ) -> AsyncIterator[CanonicalTransaction]:
        for tx in await self.get_transactions(address, start_time=start_time, limit=10_000):
            yield tx
