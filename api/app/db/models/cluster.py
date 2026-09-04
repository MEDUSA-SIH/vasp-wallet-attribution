"""Cluster models (Phase 8)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class Cluster(BaseModel, UUIDPrimaryKeyMixin, TimestampMixin):
    """A heuristic wallet cluster (Phase 8)."""

    __tablename__ = "clusters"

    label: Mapped[str | None] = mapped_column(String(length=200), nullable=True)
    heuristic: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")


class ClusterWallet(BaseModel):
    """Many-to-many link between a cluster and its wallets (Phase 8)."""

    __tablename__ = "cluster_wallets"

    cluster_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("clusters.id"),
        primary_key=True,
    )
    wallet_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("wallets.id"),
        primary_key=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, server_default="0")


__all__ = ["Cluster", "ClusterWallet"]
