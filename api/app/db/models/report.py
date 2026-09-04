"""Report model (Phase 8 + Phase 17)."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Report(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """An investigation report (Phase 17)."""

    __tablename__ = "reports"

    case_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("cases.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(length=255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(length=16), nullable=False, server_default="pdf")
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, server_default="draft")
    artifact_path: Mapped[str | None] = mapped_column(String(length=512), nullable=True)
    generated_by: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("investigators.id"), nullable=False
    )


__all__ = ["Report"]