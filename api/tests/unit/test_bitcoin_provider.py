"""Bitcoin live provider tests — mocked Tatum REST + gateway (WP-03)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import ProviderError
from app.providers.bitcoin import BitcoinProvider
from app.providers.factory import build_default_provider_registry

ADDR = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
OTHER = "bc1qother000000000000000000000000000000000"

TATUM_TX_RECV = {
    "hash": "txrecv001",
    "blockNumber": 840000,
    "time": 1700000000000,
    "fee": 500,
    "inputs": [
        {
            "coin": {"height": 839999, "value": 100000, "address": OTHER},
            "prevout": {"hash": "prev1", "index": 0},
        }
    ],
    "outputs": [
        {"value": 90000, "address": ADDR},
        {"value": 9500, "address": OTHER},
    ],
}

TATUM_TX_SEND = {
    "hash": "txsend002",
    "blockNumber": 840001,
    "time": 1700000100000,
    "fee": 800,
    "inputs": [
        {
            "coin": {"height": 840000, "value": 90000, "address": ADDR},
            "prevout": {"hash": "prev2", "index": 1},
        }
    ],
    "outputs": [
        {"value": 80000, "address": OTHER},
    ],
}

TATUM_BALANCE = {
    "balance": "0.0009",
    "incoming": "0.0009",
    "outgoing": "0",
    "incomingPending": "0",
    "outgoingPending": "0",
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    import json as _json

    path = request.url.path
    if path.endswith("/v3/bitcoin/transaction/address/" + ADDR):
        return httpx.Response(200, json=[TATUM_TX_SEND, TATUM_TX_RECV])  # newest-first
    if path.endswith("/v3/bitcoin/address/balance/" + ADDR):
        return httpx.Response(200, json=TATUM_BALANCE)
    if request.url.host == "bitcoin-mainnet.gateway.tatum.io":
        body = _json.loads(request.content.decode() or "{}")
        if body.get("method") == "getblockcount":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 840002})
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32601, "message": "Method not found"},
            },
        )
    return httpx.Response(404, json={"message": "not found"})


def _make_provider() -> BitcoinProvider:
    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        blockchain_api_key="test-key",
        bitcoin_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example"
    )
    return BitcoinProvider(settings=settings, client=client)


@pytest.mark.asyncio
async def test_get_transactions_maps_tatum_to_canonical() -> None:
    provider = _make_provider()
    txs = await provider.get_transactions(ADDR)
    assert [t.tx_hash for t in txs] == ["txrecv001", "txsend002"]  # ascending
    assert txs[0].chain == "bitcoin"
    assert txs[0].asset_symbol == "BTC"
    assert txs[0].to_address == ADDR
    assert txs[0].amount == Decimal("0.0009")
    assert txs[1].from_address == ADDR
    assert txs[1].amount == Decimal("0.0009")
    assert txs[0].block_height == 840000
    assert txs[0].success is True
    assert txs[0].fee == Decimal("0.000005")
    assert txs[0].raw.get("source") == "tatum-rest"
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_transactions_applies_time_filter_and_limit() -> None:
    provider = _make_provider()
    cutoff = datetime.fromtimestamp(1700000050, tz=UTC)
    txs = await provider.get_transactions(ADDR, start_time=cutoff, limit=1)
    assert [t.tx_hash for t in txs] == ["txsend002"]
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_balance_reads_btc_units() -> None:
    provider = _make_provider()
    assert await provider.get_balance(ADDR) == Decimal("0.0009")
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_block_height_via_gateway() -> None:
    provider = _make_provider()
    assert await provider.get_block_height() == 840002
    await provider.aclose()


@pytest.mark.asyncio
async def test_healthcheck_true() -> None:
    provider = _make_provider()
    assert await provider.healthcheck() is True
    await provider.aclose()


@pytest.mark.asyncio
async def test_upstream_error_raises_provider_error() -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        blockchain_api_key="bad-key",
        bitcoin_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_fail), base_url="https://tatum.example"
    )
    provider = BitcoinProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
    await provider.aclose()


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error() -> None:
    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        blockchain_api_key="",
        bitcoin_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example"
    )
    provider = BitcoinProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_balance(ADDR)
    await provider.aclose()


@pytest.mark.asyncio
async def test_stream_transactions_yields() -> None:
    provider = _make_provider()
    seen = [tx.tx_hash async for tx in provider.stream_transactions(ADDR)]
    assert seen == ["txrecv001", "txsend002"]
    await provider.aclose()


@pytest.mark.asyncio
async def test_rate_limit_retries_once() -> None:
    calls = {"n": 0}

    def _flaky(request: httpx.Request) -> httpx.Response:
        if "transaction/address" in request.url.path and calls["n"] == 0:
            calls["n"] += 1
            return httpx.Response(429, json={"message": "rate limited"})
        return _mock_handler(request)

    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        blockchain_api_key="test-key",
        bitcoin_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_flaky), base_url="https://tatum.example"
    )
    provider = BitcoinProvider(settings=settings, client=client)
    txs = await provider.get_transactions(ADDR, limit=1)
    assert len(txs) == 1
    assert calls["n"] == 1
    await provider.aclose()


def test_factory_registers_live_bitcoin_when_enabled() -> None:
    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        blockchain_api_key="test-key",
        bitcoin_provider_url="https://tatum.example/",
    )
    reg = build_default_provider_registry(settings)
    provider = reg.get("bitcoin")
    assert isinstance(provider, BitcoinProvider)
    assert provider.chain_code == "bitcoin"
    assert getattr(provider, "_settings", None) is not None
