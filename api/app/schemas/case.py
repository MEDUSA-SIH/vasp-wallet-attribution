"""Case schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdMixin, TimestampMixin


class CaseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_number: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="open", max_length=32)
    priority: str = Field(default="medium", max_length=16)


class CaseCreate(CaseBase):
    """Create a new case."""

    created_by: UUID
    assigned_to: UUID | None = None


class CaseUpdate(BaseModel):
    """Partial update payload."""

    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: UUID | None = None


class CaseRead(CaseBase, IdMixin, TimestampMixin):
    """Response shape for a Case."""

    created_by: UUID
    assigned_to: UUID | None = None
    opened_at: datetime
    closed_at: datetime | None = None


__all__ = ["CaseBase", "CaseCreate", "CaseUpdate", "CaseRead"]
