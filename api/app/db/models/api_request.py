"""API request log model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class APIRequest(BaseModel, UUIDPrimaryKeyMixin):
    """A request hit recorded for auditing / rate limiting."""

    __tablename__ = "api_requests"

    investigator_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("investigators.id"), nullable=True
    )
    method: Mapped[str] = mapped_column(String(length=8), nullable=False)
    path: Mapped[str] = mapped_column(String(length=512), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["APIRequest"]
