"""Password reset token model — one-time bcrypt-hashed reset tokens."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class PasswordResetToken(BaseModel, UUIDPrimaryKeyMixin):
    """A single-use password reset token (raw value never stored)."""

    __tablename__ = "password_reset_tokens"

    investigator_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("investigators.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(length=255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["PasswordResetToken"]
