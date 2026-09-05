"""Ethereum live provider — Etherscan V2 hosted explorer (Phase 20, WP-04)."""

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

_DEFAULT_BASE_URL = "https://api.etherscan.io/v2/api"
_WEI_PER_ETH = Decimal(10) ** 18
_RATE_LIMIT_MARKERS = ("notok", "rate limit", "max rate", "too many")


class EthereumProvider(BlockchainProvider):
    """Live Ethereum provider backed by Etherscan V2 (hosted explorer)."""

    chain_code = "ethereum"

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        base = (self._settings.ethereum_provider_url or _DEFAULT_BASE_URL).rstrip("/")
        self._base_url = base
        self._client = client or httpx.AsyncClient(timeout=10.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_balance(self, address: str) -> Decimal:
        data = await self._account_action("balance", address=address, tag="latest")
        try:
            return Decimal(str(data)) / _WEI_PER_ETH
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ProviderError(f"Ethereum provider: bad balance payload: {data!r}") from exc

    async def get_transactions(
        self,
        address: str,
        *,
        start_time: Any = None,
        end_time: Any = None,
        limit: int = 100,
    ) -> list[CanonicalTransaction]:
        normals = await self._account_list("txlist", address)
        tokens = await self._account_list("tokentx", address)
        internals = await self._account_list("txlistinternal", address)
        txs: list[CanonicalTransaction] = []
        txs.extend(self._to_canonical(r, kind="normal") for r in normals)
        txs.extend(self._to_canonical(r, kind="token") for r in tokens)
        txs.extend(self._to_canonical(r, kind="internal") for r in internals)
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
        params: dict[str, Any] = {"module": "proxy", "action": "eth_blockNumber"}
        self._apply_auth(params)
        try:
            resp = await self._client.get(self._base_url, params=params)
            payload: dict[str, Any] = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Ethereum provider unreachable: {exc}") from exc
        result = payload.get("result")
        if isinstance(result, str) and result.startswith("0x"):
            try:
                return int(result, 16)
            except ValueError as exc:
                raise ProviderError(f"Ethereum provider: bad block height: {result!r}") from exc
        raise ProviderError(f"Ethereum provider error: {payload.get('message', payload)!r}")

    async def healthcheck(self) -> bool:
        try:
            await self.get_block_height()
        except ProviderError:
            return False
        return True

    async def _account_action(self, action: str, address: str, **extra: Any) -> Any:
        params: dict[str, Any] = {"module": "account", "action": action, "address": address}
        params.update(extra)
        self._apply_auth(params)
        try:
            resp = await self._client.get(self._base_url, params=params)
            payload: dict[str, Any] = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Ethereum provider unreachable: {exc}") from exc
        if action == "balance":
            if payload.get("status") == "1":
                return payload.get("result", "0")
            raise ProviderError(f"Ethereum provider error: {payload.get('message', payload)!r}")
        return payload

    async def _account_list(self, action: str, address: str) -> list[dict[str, Any]]:
        import asyncio

        params: dict[str, Any] = {
            "module": "account",
            "action": action,
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 1000,
            "sort": "asc",
        }
        self._apply_auth(params)
        payload: dict[str, Any] = {}
        for attempt in range(2):
            try:
                resp = await self._client.get(self._base_url, params=params)
                payload = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise ProviderError(f"Ethereum provider unreachable: {exc}") from exc
            if payload.get("status") == "1":
                result = payload.get("result", [])
                return result if isinstance(result, list) else []
            message = str(payload.get("message", ""))
            result = payload.get("result")
            detail = str(result)[:160] if isinstance(result, str) and result else message
            if "no transactions found" in message.lower() or "no data" in message.lower():
                return []
            if self._is_rate_limit(message, detail) and attempt == 0:
                await asyncio.sleep(1.0)
                continue
            raise ProviderError(f"Ethereum provider error: {message!r} ({detail})")
        raise ProviderError(f"Ethereum provider error: {payload.get('message', payload)!r}")

    @staticmethod
    def _is_rate_limit(message: str, detail: str) -> bool:
        haystack = f"{message} {detail}".lower()
        return any(marker in haystack for marker in _RATE_LIMIT_MARKERS)

    def _apply_auth(self, params: dict[str, Any]) -> None:
        if "v2/api" in self._base_url or "v2" in self._base_url:
            params.setdefault("chainid", 1)
        api_key = self._settings.blockchain_api_key
        if api_key:
            params.setdefault("apikey", api_key)

    def _to_canonical(self, row: dict[str, Any], kind: str) -> CanonicalTransaction:
        if kind == "token":
            decimals = self._safe_int(row.get("tokenDecimal", "18"), 18)
            symbol = str(row.get("tokenSymbol") or "UNKNOWN")
        else:
            decimals = 18
            symbol = "ETH"
        amount = self._scaled(row.get("value", "0"), decimals)
        fee = self._fee(row)
        return CanonicalTransaction(
            chain="ethereum",
            tx_hash=str(row.get("hash", "")),
            block_height=self._safe_int_or_none(row.get("blockNumber")),
            block_timestamp=self._ts(row.get("timeStamp")),
            from_address=(str(row["from"]) if row.get("from") else None),
            to_address=(str(row["to"]) if row.get("to") else None),
            asset_symbol=symbol,
            amount=amount,
            fee=fee,
            success=self._ok(row),
            raw=dict(row) | {"source": "etherscan-v2", "kind": kind},
        )

    @staticmethod
    def _scaled(value: Any, decimals: int) -> Decimal:
        try:
            return Decimal(str(value or "0")) / (Decimal(10) ** decimals)
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(str(value))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_int_or_none(value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _ts(value: Any) -> datetime | None:
        if value is None or value == "":
            return None
        try:
            return datetime.fromtimestamp(int(str(value)), tz=UTC)
        except (ValueError, TypeError, OSError, OverflowError):
            return None

    @staticmethod
    def _fee(row: dict[str, Any]) -> Decimal:
        try:
            used = Decimal(str(row.get("gasUsed") or "0"))
            price = Decimal(str(row.get("gasPrice") or "0"))
            return (used * price) / _WEI_PER_ETH
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @staticmethod
    def _ok(row: dict[str, Any]) -> bool:
        if str(row.get("isError", "0")) != "0":
            return False
        status = row.get("txreceipt_status")
        return status in (None, "", "1")


__all__ = ["EthereumProvider"]
