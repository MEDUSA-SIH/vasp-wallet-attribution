"""Wallet model (Phase 8)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Wallet(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """An on-chain wallet address (Phase 8)."""

    __tablename__ = "wallets"

    address: Mapped[str] = mapped_column(String(length=255), nullable=False)
    chain_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("chains.id"), nullable=False
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    label: Mapped[str | None] = mapped_column(String(length=200), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        # UniqueConstraint on (address, chain_id) is created in the migration.
        {},
    )


__all__ = ["Wallet"]