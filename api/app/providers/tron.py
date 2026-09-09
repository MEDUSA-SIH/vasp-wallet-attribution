"""Tron live provider — Tatum REST + gateway JSON-RPC (Phase 20, WP-05)."""

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

_DEFAULT_REST_BASE_URL = "https://api.tatum.io"
_DEFAULT_GATEWAY_URL = "https://tron-mainnet.gateway.tatum.io/jsonrpc"
_SUN_PER_TRX = Decimal(10) ** 6
_PAGE_SIZE = 50


class TronProvider(BlockchainProvider):
    """Live TRON provider backed by Tatum (REST account index + gateway height)."""

    chain_code = "tron"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._rest_base = (self._settings.tron_provider_url or _DEFAULT_REST_BASE_URL).rstrip("/")
        self._gateway_url = _DEFAULT_GATEWAY_URL
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._req_id = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        key = self._settings.blockchain_api_key
        if not key:
            raise ProviderError("Tron provider: BLOCKCHAIN_API_KEY is not set")
        return {"accept": "application/json", "x-api-key": key}

    async def get_balance(self, address: str) -> Decimal:
        data = await self._rest_get(f"/v3/tron/account/{address}")
        try:
            raw = data.get("balance", 0) if isinstance(data, dict) else 0
            return Decimal(str(raw)) / _SUN_PER_TRX
        except (InvalidOperation, ValueError, AttributeError) as exc:
            raise ProviderError("Tron provider: bad balance payload") from exc

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        rows: list[dict[str, Any]] = []
        next_cursor: str | None = None
        while len(rows) < limit:
            params: dict[str, Any] = {
                "onlyConfirmed": "true",
                "orderBy": "block_timestamp,asc",
                "pageSize": min(_PAGE_SIZE, limit),
            }
            if next_cursor:
                params["next"] = next_cursor
            batch = await self._rest_get(
                f"/v3/tron/transaction/account/{address}",
                params=params,
            )
            if isinstance(batch, dict):
                txs = batch.get("transactions", [])
                if not isinstance(txs, list):
                    break
                rows.extend(txs)
                nxt = batch.get("next")
                next_cursor = str(nxt) if nxt else None
                if not txs or not next_cursor:
                    break
            elif isinstance(batch, list):
                if not batch:
                    break
                rows.extend(batch)
                break
            else:
                break
        txs_out = [self._to_canonical(r) for r in rows]
        txs_out.sort(key=lambda t: t.block_timestamp or datetime.min.replace(tzinfo=UTC))
        if start_time is not None:
            txs_out = [
                t for t in txs_out if t.block_timestamp is None or t.block_timestamp > start_time
            ]
        if end_time is not None:
            txs_out = [
                t for t in txs_out if t.block_timestamp is None or t.block_timestamp <= end_time
            ]
        return txs_out[:limit]

    async def stream_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
    ) -> AsyncIterator[CanonicalTransaction]:
        for tx in await self.get_transactions(address, start_time=start_time, limit=10_000):
            yield tx

    async def get_block_height(self) -> int:
        import asyncio

        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "eth_blockNumber",
            "params": [],
        }
        for attempt in range(2):
            try:
                resp = await self._client.post(
                    self._gateway_url, headers=self._headers(), json=payload
                )
            except httpx.HTTPError as exc:
                raise ProviderError("Tron provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code in (401, 403):
                raise ProviderError("Tron provider: unauthorized — check BLOCKCHAIN_API_KEY")
            if resp.status_code >= 400:
                raise ProviderError(f"Tron provider error: HTTP {resp.status_code}")
            try:
                data = resp.json()
            except ValueError as exc:
                raise ProviderError("Tron provider: bad JSON") from exc
            if isinstance(data, dict) and data.get("error"):
                err = data["error"]
                msg = str(err.get("message", err) if isinstance(err, dict) else err)[:160]
                raise ProviderError(f"Tron provider error: {msg!r}")
            try:
                result = data.get("result") if isinstance(data, dict) else data
                if isinstance(result, str) and result.startswith("0x"):
                    return int(result, 16)
                return int(str(result))
            except (ValueError, TypeError) as exc:
                raise ProviderError("Tron provider: bad block height") from exc
        raise ProviderError("Tron provider error: rate limited")

    async def healthcheck(self) -> bool:
        try:
            await self.get_block_height()
        except ProviderError:
            return False
        return True

    async def _rest_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        import asyncio

        for attempt in range(2):
            try:
                resp = await self._client.get(
                    f"{self._rest_base}{path}", headers=self._headers(), params=params
                )
            except httpx.HTTPError as exc:
                raise ProviderError("Tron provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code in (401, 403):
                raise ProviderError("Tron provider: unauthorized — check BLOCKCHAIN_API_KEY")
            if resp.status_code >= 400:
                raise ProviderError(f"Tron provider error: HTTP {resp.status_code}")
            try:
                return resp.json()
            except ValueError as exc:
                raise ProviderError("Tron provider: bad JSON") from exc
        raise ProviderError("Tron provider error: rate limited")

    def _to_canonical(self, row: dict[str, Any]) -> CanonicalTransaction:
        raw_data = row.get("rawData") if isinstance(row.get("rawData"), dict) else {}
        contracts = raw_data.get("contract", []) if isinstance(raw_data, dict) else []
        value: dict[str, Any] = {}
        if contracts and isinstance(contracts[0], dict):
            param = contracts[0].get("parameter", {}) or {}
            if isinstance(param, dict):
                v = param.get("value", {}) or {}
                if isinstance(v, dict):
                    value = v
        from_addr = value.get("ownerAddressBase58") or value.get("owner_address")
        to_addr = value.get("toAddressBase58") or value.get("to_address")
        try:
            amount_sun = value.get("amount", value.get("value", 0)) or 0
            amount = Decimal(str(amount_sun)) / _SUN_PER_TRX
        except (InvalidOperation, ValueError):
            amount = Decimal("0")
        try:
            fee_sun = row.get("fee", 0) or 0
            fee = Decimal(str(fee_sun)) / _SUN_PER_TRX
        except (InvalidOperation, ValueError):
            fee = Decimal("0")
        ts_ms = None
        if isinstance(raw_data, dict) and raw_data.get("timestamp") is not None:
            ts_ms = raw_data.get("timestamp")
        elif row.get("block_timestamp") is not None:
            ts_ms = row.get("block_timestamp")
        try:
            ts = datetime.fromtimestamp(int(str(ts_ms)) / 1000, tz=UTC) if ts_ms else None
        except (ValueError, TypeError, OSError, OverflowError):
            ts = None
        height = row.get("blockNumber")
        try:
            bh = int(height) if height is not None and int(str(height)) >= 0 else None
        except (ValueError, TypeError):
            bh = None
        success = True
        ret = row.get("ret")
        if isinstance(ret, list) and ret and isinstance(ret[0], dict):
            success = ret[0].get("contractRet") == "SUCCESS"
        tx_hash = str(row.get("txID") or row.get("txId") or row.get("hash") or "")
        return CanonicalTransaction(
            chain="tron",
            tx_hash=tx_hash,
            block_height=bh,
            block_timestamp=ts,
            from_address=(str(from_addr) if from_addr else None),
            to_address=(str(to_addr) if to_addr else None),
            asset_symbol="TRX",
            amount=amount,
            fee=fee,
            success=success,
            raw=dict(row) | {"source": "tatum-rest", "kind": "tron"},
        )


__all__ = ["TronProvider"]
