"""Block model (Phase 8)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Block(BaseModel, UUIDPrimaryKeyMixin):
    """A confirmed block (Phase 8)."""

    __tablename__ = "blocks"

    chain_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("chains.id"), nullable=False
    )
    height: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hash: Mapped[str] = mapped_column(String(length=128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    __table_args__ = (UniqueConstraint("chain_id", "height", name="uq_blocks_chain_height"),)


__all__ = ["Block"]
