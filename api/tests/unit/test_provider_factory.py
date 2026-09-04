"""Provider factory unit tests (Phase 20 / 22)."""
from __future__ import annotations

import pytest

from app.config import Settings
from app.providers.demo import DemoBlockchainProvider
from app.providers.factory import SUPPORTED_CHAIN_CODES, build_default_provider_registry


def test_demo_mode_registers_demo_provider_for_every_chain() -> None:
    settings = Settings(demo_mode=True)
    reg = build_default_provider_registry(settings)
    for code in SUPPORTED_CHAIN_CODES:
        provider = reg.get(code)
        assert isinstance(provider, DemoBlockchainProvider)
        assert provider.chain_code == code


def test_real_mode_registers_stub_providers() -> None:
    settings = Settings(demo_mode=False)
    reg = build_default_provider_registry(settings)
    # bitcoin provider is a stub (raises NotImplementedError)
    p = reg.get("bitcoin")
    assert p.__class__.__name__ == "BitcoinProvider"


def test_real_mode_unknown_chain_raises() -> None:
    settings = Settings(demo_mode=False)
    reg = build_default_provider_registry(settings)
    with pytest.raises(KeyError):
        reg.get("nope")