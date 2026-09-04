"""Common shared schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health endpoint payload (Phase 25)."""

    status: str = Field(default="ok", description="One of: ok, degraded, down")
    demo_mode: bool = Field(description="Whether the service is running offline demo mode")
    version: str = Field(description="API version string")


class ORMBase(BaseModel):
    """Shared Pydantic configuration for ORM-backed schemas."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IdMixin(BaseModel):
    """Add an `id` field backed by UUID."""

    id: UUID


class TimestampMixin(BaseModel):
    """Standard timestamp fields for response models."""

    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseModel):
    """Reusable pagination payload."""

    page: int = Field(default=1, ge=1, le=10_000)
    page_size: int = Field(default=50, ge=1, le=500)


class PaginatedResponse(BaseModel):
    """Generic paginated envelope."""

    items: list[Any]
    page: int
    page_size: int
    total: int


__all__ = [
    "HealthResponse",
    "ORMBase",
    "IdMixin",
    "TimestampMixin",
    "PaginationParams",
    "PaginatedResponse",
]