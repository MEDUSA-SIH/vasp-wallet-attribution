"""VASP model."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, TimestampMixin, UUIDPrimaryKeyMixin


class VASP(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """A Virtual Asset Service Provider."""

    __tablename__ = "vasps"

    name: Mapped[str] = mapped_column(String(length=200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(length=8), nullable=True)
    regulator: Mapped[str | None] = mapped_column(String(length=120), nullable=True)
    is_indian: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    fiu_ind_registration_id: Mapped[str | None] = mapped_column(String(length=120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


__all__ = ["VASP"]
