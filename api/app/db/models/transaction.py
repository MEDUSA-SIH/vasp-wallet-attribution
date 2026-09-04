"""Transaction model (Phase 8)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Transaction(BaseModel, UUIDPrimaryKeyMixin):
    """A single on-chain transaction (Phase 8)."""

    __tablename__ = "transactions"

    chain_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("chains.id"), nullable=False
    )
    block_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("blocks.id"), nullable=True
    )
    hash: Mapped[str] = mapped_column(String(length=128), nullable=False)
    from_wallet_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("wallets.id"), nullable=True
    )
    to_wallet_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("wallets.id"), nullable=True
    )
    token_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tokens.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    fee: Mapped[Decimal | None] = mapped_column(Numeric(38, 18), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("chain_id", "hash", name="uq_tx_chain_hash"),
        Index("ix_tx_from", "from_wallet_id"),
        Index("ix_tx_to", "to_wallet_id"),
        Index("ix_tx_timestamp", "timestamp"),
    )


__all__ = ["Transaction"]
