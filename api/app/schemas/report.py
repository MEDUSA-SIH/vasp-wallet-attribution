"""Report schemas (Phase 17)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import IdMixin, TimestampMixin


class ReportBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    case_id: UUID
    title: str = Field(min_length=1, max_length=255)
    summary: str | None = None
    format: str = Field(default="pdf", max_length=16)
    status: str = Field(default="draft", max_length=32)


class ReportCreate(ReportBase):
    generated_by: UUID


class ReportRead(ReportBase, IdMixin, TimestampMixin):
    artifact_path: str | None = None
    generated_by: UUID


__all__ = ["ReportBase", "ReportCreate", "ReportRead"]
