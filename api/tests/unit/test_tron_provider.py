"""Tron live provider tests — mocked Tatum REST + gateway (WP-05)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import ProviderError
from app.providers.factory import build_default_provider_registry
from app.providers.tron import TronProvider

ADDR = "TGDqQAP5bduoPKVgdbk7fGyW4DwEt3RRn8"
OTHER = "TJWCFsbeK6aybMTnsis1mccNX4gjW4ecah"

TRON_NATIVE = {
    "txID": "cbafc7eccf7a45bccb8153e190e1d19136d11770055d3e63d3e41176b899b84b",
    "blockNumber": 45223389,
    "block_timestamp": 1719226761000,
    "ret": [{"contractRet": "SUCCESS"}],
    "rawData": {
        "timestamp": 1719226761000,
        "contract": [
            {
                "parameter": {
                    "value": {
                        "amount": 1000000,
                        "ownerAddressBase58": ADDR,
                        "toAddressBase58": OTHER,
                    }
                },
                "type_url": "type.googleapis.com/protocol.TransferContract",
                "type": "TransferContract",
            }
        ],
    },
}

TRON_ACCOUNT = {
    "address": ADDR,
    "balance": 5000000000,
    "createTime": 1719225900000,
    "trc10": [],
    "trc20": [],
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    import json as _json

    path = request.url.path
    if path.endswith(f"/v3/tron/transaction/account/{ADDR}"):
        return httpx.Response(200, json={"transactions": [TRON_NATIVE], "next": None})
    if path.endswith(f"/v3/tron/account/{ADDR}"):
        return httpx.Response(200, json=TRON_ACCOUNT)
    if request.url.host == "tron-mainnet.gateway.tatum.io":
        body = _json.loads(request.content.decode() or "{}")
        if body.get("method") == "eth_blockNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x2b3c4d5"})
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32601, "message": "Method not found"},
            },
        )
    return httpx.Response(404, json={"message": "not found"})


def _make_provider() -> TronProvider:
    settings = Settings(
        demo_mode=False,
        provider_tron_enabled=True,
        blockchain_api_key="test-key",
        tron_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example"
    )
    return TronProvider(settings=settings, client=client)


@pytest.mark.asyncio
async def test_get_transactions_maps_tron_to_canonical() -> None:
    provider = _make_provider()
    txs = await provider.get_transactions(ADDR)
    assert len(txs) == 1
    assert txs[0].chain == "tron"
    assert txs[0].tx_hash == TRON_NATIVE["txID"]
    assert txs[0].from_address == ADDR
    assert txs[0].to_address == OTHER
    assert txs[0].amount == Decimal("1")  # 1_000_000 SUN
    assert txs[0].asset_symbol == "TRX"
    assert txs[0].block_height == 45223389
    assert txs[0].success is True
    assert txs[0].raw.get("source") == "tatum-rest"
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_transactions_applies_time_filter() -> None:
    provider = _make_provider()
    cutoff = datetime.fromtimestamp(1719226761, tz=UTC)
    txs = await provider.get_transactions(ADDR, start_time=cutoff)
    assert txs == []
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_balance_converts_sun() -> None:
    provider = _make_provider()
    assert await provider.get_balance(ADDR) == Decimal("5000")
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_block_height_via_gateway() -> None:
    provider = _make_provider()
    assert await provider.get_block_height() == int("0x2b3c4d5", 16)
    await provider.aclose()


@pytest.mark.asyncio
async def test_healthcheck_true() -> None:
    provider = _make_provider()
    assert await provider.healthcheck() is True
    await provider.aclose()


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error() -> None:
    settings = Settings(
        demo_mode=False,
        provider_tron_enabled=True,
        blockchain_api_key="",
        tron_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example"
    )
    provider = TronProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_balance(ADDR)
    await provider.aclose()


@pytest.mark.asyncio
async def test_upstream_error_raises_provider_error() -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    settings = Settings(
        demo_mode=False,
        provider_tron_enabled=True,
        blockchain_api_key="bad-key",
        tron_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_fail), base_url="https://tatum.example"
    )
    provider = TronProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
    await provider.aclose()


@pytest.mark.asyncio
async def test_stream_transactions_yields() -> None:
    provider = _make_provider()
    seen = [tx.tx_hash async for tx in provider.stream_transactions(ADDR)]
    assert seen == [TRON_NATIVE["txID"]]
    await provider.aclose()


@pytest.mark.asyncio
async def test_rate_limit_retries_once() -> None:
    calls = {"n": 0}

    def _flaky(request: httpx.Request) -> httpx.Response:
        if "transaction/account" in request.url.path and calls["n"] == 0:
            calls["n"] += 1
            return httpx.Response(429, json={"message": "rate limited"})
        return _mock_handler(request)

    settings = Settings(
        demo_mode=False,
        provider_tron_enabled=True,
        blockchain_api_key="test-key",
        tron_provider_url="https://tatum.example/",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_flaky), base_url="https://tatum.example"
    )
    provider = TronProvider(settings=settings, client=client)
    txs = await provider.get_transactions(ADDR, limit=1)
    assert len(txs) == 1
    assert calls["n"] == 1
    await provider.aclose()


def test_factory_registers_live_tron_when_enabled() -> None:
    settings = Settings(
        demo_mode=False,
        provider_tron_enabled=True,
        blockchain_api_key="test-key",
        tron_provider_url="https://tatum.example/",
    )
    reg = build_default_provider_registry(settings)
    provider = reg.get("tron")
    assert isinstance(provider, TronProvider)
    assert provider.chain_code == "tron"
    assert getattr(provider, "_settings", None) is not None
