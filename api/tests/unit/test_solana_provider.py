"""Solana live provider tests — mocked gateway JSON-RPC (WP-07)."""
from __future__ import annotations
from decimal import Decimal
import httpx, pytest
from app.config import Settings
from app.core.exceptions import ProviderError
from app.providers.factory import build_default_provider_registry
from app.providers.solana import SolanaProvider

ADDR = "DEMOSOLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1"
OTHER = "DEMOSOLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2"

def _mock_handler(request: httpx.Request) -> httpx.Response:
    import json as _json
    body = _json.loads(request.content.decode() or "{}")
    method = body.get("method")
    if method == "getBalance":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"value": 2500000000}})
    if method == "getBlockHeight":
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": 291846993})
    return httpx.Response(404, json={"message": "not found"})

def _make_provider() -> SolanaProvider:
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="test-key", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example")
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
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="test-key", solana_provider_url="https://tatum.example/")
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
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_mock_handler), base_url="https://tatum.example")
    provider = SolanaProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_balance(ADDR)
    await provider.aclose()

@pytest.mark.asyncio
async def test_upstream_error_raises_provider_error() -> None:
    def _fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})
    settings = Settings(demo_mode=False, provider_solana_enabled=True, blockchain_api_key="bad-key", solana_provider_url="https://tatum.example/")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_fail), base_url="https://tatum.example")
    provider = SolanaProvider(settings=settings, client=client)
    with pytest.raises(ProviderError):
        await provider.get_block_height()
    await provider.aclose()
