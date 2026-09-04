"""Investigator model (Phase 8)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Investigator(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """An LEA analyst who uses the system (Phase 8)."""

    __tablename__ = "investigators"

    email: Mapped[str] = mapped_column(String(length=320), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(length=200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(length=255), nullable=False)
    role: Mapped[str] = mapped_column(String(length=32), nullable=False, server_default="analyst")
    agency: Mapped[str | None] = mapped_column(String(length=120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Relationships are not declared yet to avoid cyclic imports; added later.


__all__ = ["Investigator"]
