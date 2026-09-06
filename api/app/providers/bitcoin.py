"""Bitcoin live provider — Tatum REST + gateway JSON-RPC (Phase 20, WP-03)."""

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
_DEFAULT_GATEWAY_URL = "https://bitcoin-mainnet.gateway.tatum.io"
_SATS_PER_BTC = Decimal(10) ** 8
_PAGE_SIZE = 50


class BitcoinProvider(BlockchainProvider):
    """Live Bitcoin provider backed by Tatum (REST address index + gateway height)."""

    chain_code = "bitcoin"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._rest_base = (self._settings.bitcoin_provider_url or _DEFAULT_REST_BASE_URL).rstrip(
            "/"
        )
        self._gateway_url = _DEFAULT_GATEWAY_URL
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._req_id = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        key = self._settings.blockchain_api_key
        if not key:
            raise ProviderError("Bitcoin provider: BLOCKCHAIN_API_KEY is not set")
        return {"accept": "application/json", "x-api-key": key}

    async def get_balance(self, address: str) -> Decimal:
        data = await self._rest_get(f"/v3/bitcoin/address/balance/{address}")
        try:
            return Decimal(str(data.get("balance", "0")))
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
        offset = 0
        while len(rows) < limit:
            batch = await self._rest_get(
                f"/v3/bitcoin/transaction/address/{address}",
                params={"pageSize": min(_PAGE_SIZE, limit), "offset": offset},
            )
            if not isinstance(batch, list) or not batch:
                break
            rows.extend(batch)
            if len(batch) < _PAGE_SIZE:
                break
            offset += len(batch)
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
        import asyncio

        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "getblockcount",
            "params": [],
        }
        for attempt in range(2):
            try:
                resp = await self._client.post(
                    self._gateway_url, headers=self._headers(), json=payload
                )
            except httpx.HTTPError as exc:
                raise ProviderError("Bitcoin provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code in (401, 403):
                raise ProviderError("Bitcoin provider: unauthorized — check BLOCKCHAIN_API_KEY")
            if resp.status_code >= 400:
                raise ProviderError(f"Bitcoin provider error: HTTP {resp.status_code}")
            try:
                data = resp.json()
            except ValueError as exc:
                raise ProviderError("Bitcoin provider: bad JSON") from exc
            if isinstance(data, dict) and data.get("error"):
                msg = str(data["error"].get("message", data["error"]))[:160]
                raise ProviderError(f"Bitcoin provider error: {msg!r}")
            try:
                result = data.get("result") if isinstance(data, dict) else data
                return int(result)  # type: ignore[arg-type]
            except (ValueError, TypeError) as exc:
                raise ProviderError("Bitcoin provider: bad block height") from exc
        raise ProviderError("Bitcoin provider error: rate limited")

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
                raise ProviderError("Bitcoin provider unreachable") from exc
            if resp.status_code == 429 and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            if resp.status_code in (401, 403):
                raise ProviderError("Bitcoin provider: unauthorized — check BLOCKCHAIN_API_KEY")
            if resp.status_code >= 400:
                raise ProviderError(f"Bitcoin provider error: HTTP {resp.status_code}")
            try:
                return resp.json()
            except ValueError as exc:
                raise ProviderError("Bitcoin provider: bad JSON") from exc
        raise ProviderError("Bitcoin provider error: rate limited")

    def _to_canonical(self, queried: str, row: dict[str, Any]) -> CanonicalTransaction:
        inputs = row.get("inputs", []) or []
        outputs = row.get("outputs", []) or []
        recv = sum(int(o.get("value", 0) or 0) for o in outputs if o.get("address") == queried)
        sent = sum(
            int((i.get("coin") or {}).get("value", 0) or 0)
            for i in inputs
            if (i.get("coin") or {}).get("address") == queried
        )
        if recv > 0 and sent == 0:
            from_addr = next(
                (
                    (i.get("coin") or {}).get("address")
                    for i in inputs
                    if (i.get("coin") or {}).get("address")
                ),
                None,
            )
            to_addr: str | None = queried
            amount = Decimal(recv) / _SATS_PER_BTC
        elif sent > 0:
            from_addr = queried
            to_addr = next(
                (o.get("address") for o in outputs if o.get("address") != queried),
                None,
            )
            amount = Decimal(sent) / _SATS_PER_BTC
        else:
            from_addr, to_addr, amount = None, queried, Decimal("0")
        try:
            fee = Decimal(str(row.get("fee", 0) or 0)) / _SATS_PER_BTC
        except InvalidOperation:
            fee = Decimal("0")
        ms = row.get("time")
        try:
            ts = datetime.fromtimestamp(int(ms) / 1000, tz=UTC) if ms else None
        except (ValueError, TypeError, OSError, OverflowError):
            ts = None
        height = row.get("blockNumber")
        try:
            bh = int(height) if height is not None and int(height) >= 0 else None
        except (ValueError, TypeError):
            bh = None
        return CanonicalTransaction(
            chain="bitcoin",
            tx_hash=str(row.get("hash", "")),
            block_height=bh,
            block_timestamp=ts,
            from_address=(str(from_addr) if from_addr else None),
            to_address=(str(to_addr) if to_addr else None),
            asset_symbol="BTC",
            amount=amount,
            fee=fee,
            success=True,
            raw=dict(row) | {"source": "tatum-rest", "kind": "btc"},
        )


__all__ = ["BitcoinProvider"]
