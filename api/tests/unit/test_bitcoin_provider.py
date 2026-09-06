"""Bitcoin live provider tests — mocked QuickNode Blockbook (WP-03)."""

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

BB_TX_RECV = {
    "txid": "txrecv001",
    "version": 2,
    "lockTime": 0,
    "blockHash": "00000000000000000001",
    "blockHeight": 840000,
    "confirmations": 10,
    "blockTime": 1700000000,
    "value": 99500,
    "valueIn": 100000,
    "fees": 500,
    "size": 225,
    "vin": [
        {
            "txid": "prev1",
            "vout": 0,
            "sequence": 4294967295,
            "n": 0,
            "addresses": [OTHER],
            "isAddress": True,
            "isOwn": False,
            "value": 100000,
        }
    ],
    "vout": [
        {
            "value": 90000,
            "n": 0,
            "spent": False,
            "hex": "0014ab",
            "addresses": [ADDR],
            "isAddress": True,
        },
        {
            "value": 9500,
            "n": 1,
            "spent": False,
            "hex": "0014cd",
            "addresses": [OTHER],
            "isAddress": True,
        },
    ],
}

BB_TX_SEND = {
    "txid": "txsend002",
    "version": 2,
    "lockTime": 0,
    "blockHash": "00000000000000000002",
    "blockHeight": 840001,
    "confirmations": 9,
    "blockTime": 1700000100,
    "value": 80000,
    "valueIn": 90000,
    "fees": 800,
    "size": 220,
    "vin": [
        {
            "txid": "prev2",
            "vout": 1,
            "sequence": 4294967295,
            "n": 0,
            "addresses": [ADDR],
            "isAddress": True,
            "isOwn": True,
            "value": 90000,
        }
    ],
    "vout": [
        {
            "value": 80000,
            "n": 0,
            "spent": False,
            "hex": "0014ef",
            "addresses": [OTHER],
            "isAddress": True,
        }
    ],
}

BB_PAGE = {
    "address": ADDR,
    "balance": "90000",
    "totalReceived": "90000",
    "totalSent": "0",
    "unconfirmedBalance": "0",
    "unconfirmedTxs": 0,
    "txs": 2,
    "transactions": [BB_TX_SEND, BB_TX_RECV],  # newest-first on wire
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    import json as _json

    body = _json.loads(request.content.decode() or "{}")
    method = body.get("method")
    if method == "bb_getAddress":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": BB_PAGE})
    if method == "getblockchaininfo":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"blocks": 840002}})
    if method == "getblockcount":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 840002})
    return httpx.Response(
        200,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        },
    )


def _make_provider() -> BitcoinProvider:
    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        bitcoin_provider_url="https://qn.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://qn.example"
    )
    return BitcoinProvider(settings=settings, client=client)


@pytest.mark.asyncio
async def test_get_transactions_maps_bb_to_canonical() -> None:
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
    assert txs[0].raw.get("source") == "quicknode-bb"
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_transactions_applies_time_filter_and_limit() -> None:
    provider = _make_provider()
    cutoff = datetime.fromtimestamp(1700000050, tz=UTC)
    txs = await provider.get_transactions(ADDR, start_time=cutoff, limit=1)
    assert [t.tx_hash for t in txs] == ["txsend002"]
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_balance_converts_sats() -> None:
    provider = _make_provider()
    assert await provider.get_balance(ADDR) == Decimal("0.0009")
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_block_height() -> None:
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
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32601, "message": "Method not found"},
            },
        )

    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        bitcoin_provider_url="https://qn.example/",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(_fail), base_url="https://qn.example")
    provider = BitcoinProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
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
        import json as _json

        body = _json.loads(request.content.decode() or "{}")
        if body.get("method") == "bb_getAddress" and calls["n"] == 0:
            calls["n"] += 1
            return httpx.Response(429, json={"error": "rate limited"})
        return _mock_handler(request)

    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        bitcoin_provider_url="https://qn.example/",
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(_flaky), base_url="https://qn.example")
    provider = BitcoinProvider(settings=settings, client=client)
    txs = await provider.get_transactions(ADDR, limit=1)
    assert len(txs) == 1
    assert calls["n"] == 1
    await provider.aclose()


def test_factory_registers_live_bitcoin_when_enabled() -> None:
    settings = Settings(
        demo_mode=False,
        provider_bitcoin_enabled=True,
        bitcoin_provider_url="https://qn.example/",
    )
    reg = build_default_provider_registry(settings)
    provider = reg.get("bitcoin")
    assert isinstance(provider, BitcoinProvider)
    assert provider.chain_code == "bitcoin"
    assert getattr(provider, "_settings", None) is not None
