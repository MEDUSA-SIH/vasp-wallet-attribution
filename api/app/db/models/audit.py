"""Audit event model (Phase 8 + Phase 25)."""

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


class AuditEvent(BaseModel, UUIDPrimaryKeyMixin):
    """An immutable audit log entry (Phase 25)."""

    __tablename__ = "audit_events"

    actor_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("investigators.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(length=64), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["AuditEvent"]
