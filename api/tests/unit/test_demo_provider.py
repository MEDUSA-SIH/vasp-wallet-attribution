"""DemoBlockchainProvider unit tests (Phase 21 / 22)."""

from __future__ import annotations

import pytest

from app.providers.demo import (
    DEFAULT_DATASET_DIR,
    DemoBlockchainProvider,
    DemoDataset,
    reset_shared_dataset,
)


@pytest.fixture
def dataset() -> DemoDataset:
    reset_shared_dataset()
    return DemoDataset.load(DEFAULT_DATASET_DIR)


@pytest.fixture
def provider(dataset: DemoDataset) -> DemoBlockchainProvider:
    return DemoBlockchainProvider(dataset=dataset, chain_code="ethereum")


@pytest.mark.asyncio
async def test_get_transactions_case1(provider: DemoBlockchainProvider) -> None:
    txs = await provider.get_transactions("0xDEMO_case1_suspect_001")
    assert len(txs) == 1
    assert txs[0].to_address == "0xDEMO_case1_vasp_alpha_01"
    assert txs[0].chain == "ethereum"


@pytest.mark.asyncio
async def test_get_transactions_case5_mixer(provider: DemoBlockchainProvider) -> None:
    txs = await provider.get_transactions("0xDEMO_case5_suspect_001")
    assert len(txs) == 1
    assert txs[0].to_address == "0xDEMO_case5_mixer_001"


@pytest.mark.asyncio
async def test_get_balance_is_zero(provider: DemoBlockchainProvider) -> None:
    assert await provider.get_balance("0xDEMO_case1_suspect_001") == 0


@pytest.mark.asyncio
async def test_get_block_height(provider: DemoBlockchainProvider) -> None:
    height = await provider.get_block_height()
    assert height > 0


@pytest.mark.asyncio
async def test_healthcheck(provider: DemoBlockchainProvider) -> None:
    assert await provider.healthcheck() is True


def test_get_address_labels(provider: DemoBlockchainProvider) -> None:
    labels = provider.get_address_labels("0xDEMO_case1_vasp_alpha_01")
    assert labels == ["VASP Alpha deposit"]


def test_get_vasp_id(provider: DemoBlockchainProvider) -> None:
    assert provider.get_vasp_id("0xDEMO_case1_vasp_alpha_01") == "vasp_alpha"
    assert provider.get_vasp_id("0xDEMO_unknown") is None


def test_get_mixer_id(provider: DemoBlockchainProvider) -> None:
    assert provider.get_mixer_id("0xDEMO_case5_mixer_001") == "mixer_demo_a"


def test_get_bridge_id(provider: DemoBlockchainProvider) -> None:
    assert provider.get_bridge_id("0xDEMO_case6_bridge_eth_01") == "bridge_eth_btc"


@pytest.mark.asyncio
async def test_btc_provider_returns_btc_txs_only(dataset: DemoDataset) -> None:
    p = DemoBlockchainProvider(dataset=dataset, chain_code="bitcoin")
    txs = await p.get_transactions("0xDEMO_case6_bridge_eth_01")
    # The BTC provider must only return txs with chain=bitcoin.
    assert all(tx.chain == "bitcoin" for tx in txs)
    # The BTC tx has the bridge as sender and the VASP_foxtrot BTC deposit
    # as recipient.
    btc_bridge_txs = [t for t in txs if t.from_address == "0xDEMO_case6_bridge_eth_01"]
    assert btc_bridge_txs
    assert btc_bridge_txs[0].to_address == "DEMOcase6vasp_foxtrot_btc_01"
