"""Wallet schemas (Phase 8 + Phase 11)."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdMixin, TimestampMixin


class WalletBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address: str = Field(min_length=1, max_length=255)
    chain_id: UUID
    label: str | None = Field(default=None, max_length=200)
    tags: dict | None = None
    metadata_json: dict | None = None


class WalletCreate(WalletBase):
    first_seen_at: datetime | None = None


class WalletUpdate(BaseModel):
    label: str | None = None
    tags: dict | None = None
    metadata_json: dict | None = None


class WalletRead(WalletBase, IdMixin, TimestampMixin):
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


__all__ = ["WalletBase", "WalletCreate", "WalletUpdate", "WalletRead"]