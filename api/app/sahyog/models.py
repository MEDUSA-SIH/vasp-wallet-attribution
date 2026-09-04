"""SAHYOG message models (Phase 7)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class SahyogCase:
    """A case ingested from SAHYOG (Phase 7)."""

    id: UUID
    case_number: str
    title: str
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class SahyogMessage:
    """An outbound message ready to be sent to SAHYOG."""

    id: UUID = field(default_factory=uuid4)
    case_id: UUID | None = None
    body: dict | None = None


@dataclass(slots=True)
class SahyogReceipt:
    """Acknowledgement from SAHYOG."""

    message_id: UUID
    accepted: bool
    detail: str = ""


__all__ = ["SahyogCase", "SahyogMessage", "SahyogReceipt"]