"""Investigation run record (Phase 8 + Phase 10)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Investigation(BaseModel, UUIDPrimaryKeyMixin):
    """A single attribution run for a case (Phase 10)."""

    __tablename__ = "investigations"

    case_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    started_by: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("investigators.id"), nullable=False
    )
    hops_used: Mapped[int] = mapped_column(
        # Integer is referenced lazily to avoid circular import in some envs.
        __import__("sqlalchemy").Integer,
        nullable=False,
        server_default="0",
    )
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, server_default="running")
    results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = ["Investigation"]