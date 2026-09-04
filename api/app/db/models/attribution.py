"""Attribution model (Phase 8 + Phase 10)."""
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


class Attribution(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """A wallet → VASP attribution record (Phase 10)."""

    __tablename__ = "attributions"

    case_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    wallet_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False
    )
    vasp_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("vasps.id"), nullable=True
    )
    cluster_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("clusters.id"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")
    typology: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, server_default="draft")
    explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_attributions_case", "case_id"),
        Index("ix_attributions_wallet", "wallet_id"),
    )


__all__ = ["Attribution"]