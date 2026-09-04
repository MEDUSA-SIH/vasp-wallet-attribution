"""Token model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Token(BaseModel, UUIDPrimaryKeyMixin):
    """A fungible token on a chain."""

    __tablename__ = "tokens"

    chain_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("chains.id"), nullable=False
    )
    contract_address: Mapped[str | None] = mapped_column(String(length=128), nullable=True)
    symbol: Mapped[str] = mapped_column(String(length=32), nullable=False)
    name: Mapped[str] = mapped_column(String(length=120), nullable=False)
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, server_default="18")
    is_native: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


__all__ = ["Token"]
