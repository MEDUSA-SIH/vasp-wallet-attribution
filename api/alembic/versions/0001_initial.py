"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-04 00:00:00

Stage-0 scaffold migration: declares all tables defined in app/db/models/
(database tables). Bodies will be expanded in later stages; this revision
creates the full skeleton so the database is structurally complete.

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # investigators
    op.create_table(
        "investigators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="analyst"),
        sa.Column("agency", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # chains
    op.create_table(
        "chains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("native_symbol", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # cases
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(length=64), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=False,
        ),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=True,
        ),
        sa.Column(
            "opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cases_status", "cases", ["status"])

    # vasp
    op.create_table(
        "vasps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("regulator", sa.String(length=120), nullable=True),
        sa.Column("is_indian", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fiu_ind_registration_id", sa.String(length=120), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_vasps_name", "vasps", ["name"])

    # tokens
    op.create_table(
        "tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chains.id"), nullable=False
        ),
        sa.Column("contract_address", sa.String(length=128), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("decimals", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("is_native", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_tokens_chain_symbol", "tokens", ["chain_id", "symbol"])

    # wallets
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column(
            "chain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chains.id"), nullable=False
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("address", "chain_id", name="uq_wallets_address_chain"),
    )
    op.create_index("ix_wallets_address", "wallets", ["address"])

    # blocks
    op.create_table(
        "blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chains.id"), nullable=False
        ),
        sa.Column("height", sa.BigInteger(), nullable=False),
        sa.Column("hash", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tx_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("chain_id", "height", name="uq_blocks_chain_height"),
    )

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chains.id"), nullable=False
        ),
        sa.Column(
            "block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("blocks.id"), nullable=True
        ),
        sa.Column("hash", sa.String(length=128), nullable=False),
        sa.Column(
            "from_wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wallets.id"),
            nullable=True,
        ),
        sa.Column(
            "to_wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wallets.id"),
            nullable=True,
        ),
        sa.Column(
            "token_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=True
        ),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("fee", sa.Numeric(38, 18), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("chain_id", "hash", name="uq_tx_chain_hash"),
    )
    op.create_index("ix_tx_from", "transactions", ["from_wallet_id"])
    op.create_index("ix_tx_to", "transactions", ["to_wallet_id"])
    op.create_index("ix_tx_timestamp", "transactions", ["timestamp"])

    # clusters
    op.create_table(
        "clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("heuristic", sa.String(length=64), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "cluster_wallets",
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clusters.id"),
            primary_key=True,
        ),
        sa.Column(
            "wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wallets.id"),
            primary_key=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
    )

    # attributions
    op.create_table(
        "attributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False
        ),
        sa.Column(
            "wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id"), nullable=False
        ),
        sa.Column(
            "vasp_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vasps.id"), nullable=True
        ),
        sa.Column(
            "cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clusters.id"), nullable=True
        ),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("typology", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_attributions_case", "attributions", ["case_id"])
    op.create_index("ix_attributions_wallet", "attributions", ["wallet_id"])

    # risks
    op.create_table(
        "risks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id"), nullable=False
        ),
        sa.Column("typology", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_risk_wallet", "risks", ["wallet_id"])

    # investigations
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False
        ),
        sa.Column(
            "started_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=False,
        ),
        sa.Column("hops_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # reports
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("format", sa.String(length=16), nullable=False, server_default="pdf"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("artifact_path", sa.String(length=512), nullable=True),
        sa.Column(
            "generated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    # api_requests
    op.create_table(
        "api_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=True,
        ),
        sa.Column("method", sa.String(length=8), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_api_requests_created", "api_requests", ["created_at"])

    # audit
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_created", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("api_requests")
    op.drop_table("reports")
    op.drop_table("investigations")
    op.drop_table("risks")
    op.drop_table("attributions")
    op.drop_table("cluster_wallets")
    op.drop_table("clusters")
    op.drop_table("transactions")
    op.drop_table("blocks")
    op.drop_table("wallets")
    op.drop_table("tokens")
    op.drop_table("vasps")
    op.drop_table("cases")
    op.drop_table("chains")
    op.drop_table("investigators")
