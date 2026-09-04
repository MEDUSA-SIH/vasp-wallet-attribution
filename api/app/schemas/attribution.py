"""Attribution schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdMixin, TimestampMixin


class AttributionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: UUID
    wallet_id: UUID
    vasp_id: UUID | None = None
    cluster_id: UUID | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = Field(default=0.0, ge=0.0)
    typology: str | None = None
    status: str = Field(default="draft", max_length=32)
    explanation: dict | None = None


class AttributionCreate(BaseModel):
    """Create an attribution record manually."""

    case_id: UUID
    wallet_id: UUID
    vasp_id: UUID | None = None
    confidence: float | None = None


class AttributionRead(AttributionBase, IdMixin, TimestampMixin):
    """Response shape for an Attribution."""


class AttributionRankingEntry(BaseModel):
    """One entry in a ranking result."""

    wallet_id: UUID
    address: str | None = None
    vasp_name: str | None = None
    confidence: float
    score: float
    hops: int
    rationale: str | None = None


class AttributionRankingResponse(BaseModel):
    """Response for /attribution/rank."""

    case_id: UUID
    entries: list[AttributionRankingEntry]
    min_confidence: float


__all__ = [
    "AttributionBase",
    "AttributionCreate",
    "AttributionRead",
    "AttributionRankingEntry",
    "AttributionRankingResponse",
]
