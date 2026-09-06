"""auth rbac

Revision ID: 0002_auth_rbac
Revises: 0001_initial
Create Date: 2026-09-06

Adds investigators.token_version for stateless JWT revocation and the
password_reset_tokens table for out-of-band password resets.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_auth_rbac"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investigators",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE investigators SET role = 'investigator' WHERE role = 'analyst'")
    op.alter_column(
        "investigators",
        "role",
        existing_type=sa.String(length=32),
        server_default="investigator",
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "investigator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigators.id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_investigator_id",
        "password_reset_tokens",
        ["investigator_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_investigator_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.alter_column(
        "investigators",
        "role",
        existing_type=sa.String(length=32),
        server_default="analyst",
    )
    op.drop_column("investigators", "token_version")
