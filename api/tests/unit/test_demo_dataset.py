"""Demo dataset tests."""

from __future__ import annotations

import pytest

from app.providers.demo import DEFAULT_DATASET_DIR, DemoDataset


def test_dataset_loads() -> None:
    ds = DemoDataset.load()
    assert len(ds.cases) == 8
    assert len(ds.transactions) >= 20  # we have exactly 20
    assert ds.vasps, "vasps dict is populated"
    assert ds.bridges, "bridges dict is populated"
    assert ds.mixers, "mixers dict is populated"


@pytest.mark.parametrize(
    "case_id,suspect,expected_vasp",
    [
        ("case1", "0xDEMO_case1_suspect_001", "vasp_alpha"),
        ("case2", "0xDEMO_case2_suspect_001", "vasp_bravo"),
        ("case3", "0xDEMO_case3_suspect_001", "vasp_charlie"),
    ],
)
def test_each_case_has_suspect(
    ds: DemoDataset, case_id: str, suspect: str, expected_vasp: str
) -> None:
    case = next(c for c in ds.cases if c["id"] == case_id)
    assert case["suspect_address"] == suspect
    # The expected VASP appears somewhere in the tx graph.
    found = any(expected_vasp in (a.vasp_id or "") for a in ds.addresses.values())
    assert found, f"{expected_vasp} missing from addresses"


def test_case4_has_three_vasps(ds: DemoDataset) -> None:
    case4_vasps = {"vasp_delta", "vasp_echo", "vasp_foxtrot"}
    actual = {a.vasp_id for a in ds.addresses.values() if a.vasp_id}
    assert case4_vasps.issubset(actual)


def test_case5_has_mixer(ds: DemoDataset) -> None:
    mixer_addrs = {a.address for a in ds.addresses.values() if a.mixer_id}
    assert "0xDEMO_case5_mixer_001" in mixer_addrs


def test_case6_has_bridge(ds: DemoDataset) -> None:
    bridge_addrs = {a.address for a in ds.addresses.values() if a.bridge_id}
    assert "0xDEMO_case6_bridge_eth_01" in bridge_addrs


def test_dataset_default_dir_exists() -> None:
    assert DEFAULT_DATASET_DIR.exists()


@pytest.fixture
def ds() -> DemoDataset:
    return DemoDataset.load()
