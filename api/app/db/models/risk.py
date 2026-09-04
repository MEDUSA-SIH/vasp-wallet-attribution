"""Risk model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Risk(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """A risk score for a wallet."""

    __tablename__ = "risks"

    wallet_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False
    )
    typology: Mapped[str] = mapped_column(String(length=64), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("ix_risk_wallet", "wallet_id"),)


__all__ = ["Risk"]
