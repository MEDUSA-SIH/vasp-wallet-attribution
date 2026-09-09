"""BNB Chain live provider tests — mocked Etherscan V2 chainid 56 (WP-06)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app.config import Settings
from app.core.exceptions import ProviderError
from app.providers.bnb import BnbProvider
from app.providers.demo import DemoBlockchainProvider
from app.providers.factory import build_default_provider_registry

SUSPECT = "0x1111111111111111111111111111111111111111"
MID = "0x2222222222222222222222222222222222222222"
DEST = "0x3333333333333333333333333333333333333333"

NORMAL_TX = {
    "hash": "0xbnb123",
    "blockNumber": "22345678",
    "timeStamp": "1700000000",
    "from": SUSPECT,
    "to": MID,
    "value": "1000000000000000000",  # 1 BNB
    "gasUsed": "21000",
    "gasPrice": "5000000000",  # 5 gwei
    "isError": "0",
    "txreceipt_status": "1",
}

TOKEN_TX = {
    "hash": "0xbnb456",
    "blockNumber": "22345679",
    "timeStamp": "1700000100",
    "from": MID,
    "to": DEST,
    "value": "2500000000000000000",  # 2.5 USDT (18 decimals, BEP-20)
    "tokenDecimal": "18",
    "tokenSymbol": "USDT",
    "gasUsed": "60000",
    "gasPrice": "5000000000",
    "isError": "0",
    "txreceipt_status": "1",
}


def _mock_handler(request: httpx.Request) -> httpx.Response:
    params = dict(request.url.params)
    assert params.get("chainid") == "56"
    action = params.get("action")
    if params.get("module") == "proxy" and action == "eth_blockNumber":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x154a8b2"})
    if action == "txlist":
        return httpx.Response(200, json={"status": "1", "message": "OK", "result": [NORMAL_TX]})
    if action == "tokentx":
        return httpx.Response(200, json={"status": "1", "message": "OK", "result": [TOKEN_TX]})
    if action == "txlistinternal":
        return httpx.Response(200, json={"status": "1", "message": "OK", "result": []})
    if action == "balance":
        return httpx.Response(
            200, json={"status": "1", "message": "OK", "result": "2000000000000000000"}
        )
    return httpx.Response(
        200, json={"status": "0", "message": "No transactions found", "result": []}
    )


def _make_provider() -> BnbProvider:
    settings = Settings(
        demo_mode=False,
        provider_bnb_enabled=True,
        blockchain_api_key="test-key",
        bnb_provider_url="https://api.etherscan.io/v2/api",
    )
    transport = httpx.MockTransport(_mock_handler)
    client = httpx.AsyncClient(transport=transport, base_url="https://api.etherscan.io")
    return BnbProvider(settings=settings, client=client)


@pytest.mark.asyncio
async def test_get_transactions_merges_normal_and_token() -> None:
    provider = _make_provider()
    txs = await provider.get_transactions(SUSPECT)
    assert len(txs) == 2
    # Ascending timestamp order.
    assert txs[0].tx_hash == "0xbnb123"
    assert txs[1].tx_hash == "0xbnb456"
    assert txs[0].chain == "bnb"
    assert txs[0].asset_symbol == "BNB"
    assert txs[0].amount == Decimal("1")
    assert txs[1].asset_symbol == "USDT"
    assert txs[1].amount == Decimal("2.5")
    assert txs[0].block_height == 22345678
    assert txs[0].success is True
    assert txs[0].raw.get("source") == "etherscan-v2"
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_transactions_applies_time_filter_and_limit() -> None:
    provider = _make_provider()
    cutoff = datetime.fromtimestamp(1700000050, tz=UTC)
    txs = await provider.get_transactions(SUSPECT, start_time=cutoff, limit=1)
    assert len(txs) == 1
    assert txs[0].tx_hash == "0xbnb456"
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_balance_converts_wei() -> None:
    provider = _make_provider()
    assert await provider.get_balance(SUSPECT) == Decimal("2")
    await provider.aclose()


@pytest.mark.asyncio
async def test_get_block_height_parses_hex() -> None:
    provider = _make_provider()
    assert await provider.get_block_height() == int("0x154a8b2", 16)
    await provider.aclose()


@pytest.mark.asyncio
async def test_healthcheck_true() -> None:
    provider = _make_provider()
    assert await provider.healthcheck() is True
    await provider.aclose()


@pytest.mark.asyncio
async def test_upstream_error_raises_provider_error() -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"status": "0", "message": "Invalid API Key", "result": []})

    settings = Settings(
        demo_mode=False,
        provider_bnb_enabled=True,
        blockchain_api_key="test-key",
        bnb_provider_url="https://api.etherscan.io/v2/api",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_fail), base_url="https://api.etherscan.io"
    )
    provider = BnbProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
    await provider.aclose()


@pytest.mark.asyncio
async def test_stream_transactions_yields() -> None:
    provider = _make_provider()
    seen = [tx.tx_hash async for tx in provider.stream_transactions(SUSPECT)]
    assert seen == ["0xbnb123", "0xbnb456"]
    await provider.aclose()


@pytest.mark.asyncio
async def test_rate_limit_retries_once_then_returns() -> None:
    calls = {"n": 0}

    def _flaky(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        if params.get("action") == "txlist" and calls["n"] == 0:
            calls["n"] += 1
            return httpx.Response(
                200,
                json={"status": "0", "message": "NOTOK", "result": "Max rate limit reached"},
            )
        return _mock_handler(request)

    settings = Settings(
        demo_mode=False,
        provider_bnb_enabled=True,
        blockchain_api_key="k",
        bnb_provider_url="https://api.etherscan.io/v2/api",
    )
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(_flaky), base_url="https://api.etherscan.io"
    )
    provider = BnbProvider(settings=settings, client=client)
    txs = await provider.get_transactions(SUSPECT, limit=1)
    assert len(txs) == 1
    assert calls["n"] == 1
    await provider.aclose()


def test_factory_registers_live_bnb_when_enabled() -> None:
    settings = Settings(
        demo_mode=False,
        provider_bnb_enabled=True,
        blockchain_api_key="test-key",
        bnb_provider_url="https://api.etherscan.io/v2/api",
    )
    reg = build_default_provider_registry(settings)
    provider = reg.get("bnb")
    assert isinstance(provider, BnbProvider)
    assert provider.chain_code == "bnb"
    # Live wiring carries settings (stub takes no args and holds no config).
    assert getattr(provider, "_settings", None) is not None
    assert provider._settings.blockchain_api_key == "test-key"  # type: ignore[attr-defined]
    # Other chains stay stubs; demo path untouched.
    assert reg.get("bitcoin").__class__.__name__ == "BitcoinProvider"


def test_factory_demo_mode_still_registers_demo_for_bnb() -> None:
    reg = build_default_provider_registry(Settings(demo_mode=True))
    assert isinstance(reg.get("bnb"), DemoBlockchainProvider)
