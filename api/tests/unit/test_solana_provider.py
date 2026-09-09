"""Solana live provider tests — mocked gateway JSON-RPC (WP-07)."""

from __future__ import annotations

import json as _json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import ProviderError
from app.providers.factory import build_default_provider_registry
from app.providers.solana import SolanaProvider

ADDR = "DEMOSOLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1"
OTHER = "DEMOSOLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2"

SIG1 = "5UfDuX7M5Y2k9QwErTyUiOpAsDfGhJkLzXcVbNm123456789abcd"
TX_DETAIL = {
    "slot": 280000001,
    "blockTime": 1719226761,
    "meta": {
        "err": None,
        "fee": 5000,
        "preBalances": [3000000000, 1000000],
        "postBalances": [2000000000, 1001000000],
    },
    "transaction": {"message": {"accountKeys": [ADDR, OTHER]}},
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    body = _json.loads(request.content.decode() or "{}")
    method = body.get("method")
    if method == "getBalance":
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": {"value": 2500000000}}
        )
    if method == "getBlockHeight":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 291846993})
    if method == "getSignaturesForAddress":
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": [
                    {"signature": SIG1, "slot": 280000001, "blockTime": 1719226761, "err": None}
                ],
            },
        )
    if method == "getTransaction":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": TX_DETAIL})
    return httpx.Response(404, json={"message": "not found"})


def _make_provider() -> SolanaProvider:
    settings = Settings(
        demo_mode=False,
        provider_solana_enabled=True,
        blockchain_api_key="test-key",
        solana_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example"
    )
    return SolanaProvider(settings=settings, client=client)


@pytest.mark.asyncio
async def test_get_balance_converts_lamports() -> None:
    provider = _make_provider()
    assert await provider.get_balance(ADDR) == Decimal("2.5")
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_block_height_via_gateway() -> None:
    provider = _make_provider()
    assert await provider.get_block_height() == 291846993
    await provider.aclose()


def test_factory_registers_live_solana_when_enabled() -> None:
    settings = Settings(
        demo_mode=False,
        provider_solana_enabled=True,
        blockchain_api_key="test-key",
        solana_provider_url="https://tatum.example/",
    )
    reg = build_default_provider_registry(settings)
    provider = reg.get("solana")
    assert isinstance(provider, SolanaProvider)
    assert provider.chain_code == "solana"


@pytest.mark.asyncio
async def test_healthcheck_true() -> None:
    provider = _make_provider()
    assert await provider.healthcheck() is True
    await provider.aclose()


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error() -> None:
    settings = Settings(
        demo_mode=False,
        provider_solana_enabled=True,
        blockchain_api_key="",
        solana_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example"
    )
    provider = SolanaProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_balance(ADDR)
    await provider.aclose()


@pytest.mark.asyncio
async def test_upstream_error_raises_provider_error() -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    settings = Settings(
        demo_mode=False,
        provider_solana_enabled=True,
        blockchain_api_key="bad-key",
        solana_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_fail), base_url="https://tatum.example"
    )
    provider = SolanaProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_transactions_maps_sol_to_canonical() -> None:
    provider = _make_provider()
    txs = await provider.get_transactions(ADDR)
    assert len(txs) == 1
    assert txs[0].chain == "solana" and txs[0].tx_hash == SIG1
    assert txs[0].from_address == ADDR and txs[0].to_address == OTHER
    assert txs[0].amount == Decimal("1") and txs[0].asset_symbol == "SOL"
    assert txs[0].block_height == 280000001 and txs[0].success is True
    assert txs[0].raw.get("source") == "solana-rpc"
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_transactions_applies_time_filter() -> None:
    provider = _make_provider()
    cutoff = datetime.fromtimestamp(1719226761, tz=UTC)
    assert await provider.get_transactions(ADDR, start_time=cutoff) == []
    await provider.aclose()


@pytest.mark.asyncio
async def test_stream_transactions_yields() -> None:
    provider = _make_provider()
    seen = [t.tx_hash async for t in provider.stream_transactions(ADDR)]
    assert seen == [SIG1]
    await provider.aclose()


@pytest.mark.asyncio
async def test_rate_limit_retries_once() -> None:
    calls = {"n": 0}

    def _flaky(request: httpx.Request) -> httpx.Response:
        body = _json.loads(request.content.decode() or "{}")
        if body.get("method") == "getSignaturesForAddress" and calls["n"] == 0:
            calls["n"] += 1
            return httpx.Response(429, json={"message": "rate limited"})
        return _mock_handler(request)

    settings = Settings(
        demo_mode=False,
        provider_solana_enabled=True,
        blockchain_api_key="test-key",
        solana_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_flaky), base_url="https://tatum.example"
    )
    provider = SolanaProvider(settings=settings, client=client)
    assert len(await provider.get_transactions(ADDR, limit=1)) == 1 and calls["n"] == 1
    await provider.aclose()
