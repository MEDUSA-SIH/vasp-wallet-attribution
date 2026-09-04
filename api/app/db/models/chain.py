"""Chain model (Phase 8)."""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin


class Chain(BaseModel, UUIDPrimaryKeyMixin):
    """A supported blockchain (Phase 8)."""

    __tablename__ = "chains"

    code: Mapped[str] = mapped_column(String(length=32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(length=120), nullable=False)
    native_symbol: Mapped[str | None] = mapped_column(String(length=16), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at = mapped_column(  # type: ignore[assignment]
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["Chain"]