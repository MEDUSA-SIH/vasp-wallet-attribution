"""DB models unit tests (Phase 8).

These tests do not require a real DB – they instantiate the SQLAlchemy
models and verify metadata.
"""

from __future__ import annotations

from app.db.base import BaseModel
from app.db.models import (
    VASP,
    APIRequest,
    Attribution,
    AuditEvent,
    Block,
    Case,
    Chain,
    Cluster,
    ClusterWallet,
    Investigation,
    Investigator,
    Report,
    Risk,
    Token,
    Transaction,
    Wallet,
)


def test_all_tables_registered() -> None:
    expected = {
        "investigators",
        "cases",
        "chains",
        "wallets",
        "tokens",
        "blocks",
        "transactions",
        "vasps",
        "clusters",
        "cluster_wallets",
        "attributions",
        "risks",
        "investigations",
        "reports",
        "api_requests",
        "audit_events",
    }
    assert set(BaseModel.metadata.tables.keys()) == expected


def test_models_instantiable() -> None:
    # Smoke test – each model can be referenced via its class.
    for cls in (
        Investigator,
        Case,
        Wallet,
        Chain,
        Token,
        Block,
        Transaction,
        VASP,
        Cluster,
        ClusterWallet,
        Attribution,
        Risk,
        Investigation,
        Report,
        APIRequest,
        AuditEvent,
    ):
        assert cls.__name__
