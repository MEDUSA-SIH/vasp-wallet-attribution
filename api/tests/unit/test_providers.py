"""Provider abstraction unit tests."""

from __future__ import annotations

import pytest

from app.providers.base import ProviderRegistry
from app.providers.demo import DemoBlockchainProvider


@pytest.mark.asyncio
async def test_demo_provider_balance_is_zero() -> None:
    p = DemoBlockchainProvider()
    assert await p.get_balance("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") == 0  # type: ignore[comparison-overlap]


def test_registry_roundtrip() -> None:
    reg = ProviderRegistry()
    p = DemoBlockchainProvider()
    reg.register(p)
    assert reg.get("demo") is p
    assert "demo" in reg.available()


def test_registry_missing_raises() -> None:
    reg = ProviderRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")
