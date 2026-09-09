"""Solana live provider — Tatum gateway JSON-RPC (Phase 20, WP-07)."""
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

_DEFAULT_GATEWAY_URL = "https://solana-mainnet.gateway.tatum.io"
_LAMPORTS_PER_SOL = Decimal(10) ** 9

class SolanaProvider(BlockchainProvider):
    """Live Solana provider backed by Tatum gateway JSON-RPC."""
    chain_code = "solana"
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
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
        return {"accept": "application/json", "content-type": "application/json", "x-api-key": key}
    async def _rpc_post(self, method: str, params: list[Any]) -> Any:
        import asyncio
        self._req_id += 1
        payload = {"jsonrpc": "2.0", "id": self._req_id, "method": method, "params": params}
        for attempt in range(2):
            try:
                resp = await self._client.post(self._gateway_url, headers=self._headers(), json=payload)
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
    async def get_transactions(self, address: str, *, start_time: Any = None, end_time: Any = None, limit: int = 100) -> list[CanonicalTransaction]:
        raise ProviderError("Solana provider: get_transactions not yet implemented (Task 3)")
    async def stream_transactions(self, address: str, *, start_time: Any = None) -> AsyncIterator[CanonicalTransaction]:
        for tx in await self.get_transactions(address, start_time=start_time, limit=10_000):
            yield tx
