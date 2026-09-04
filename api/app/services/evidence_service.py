"""Evidence package service (Phase 16)."""

from __future__ import annotations


class EvidenceService:
    """Stub evidence service – will eventually assemble evidence packages."""

    async def collect(self, case_id: str) -> dict[str, str]:
        return {"case_id": case_id, "items": "0"}


__all__ = ["EvidenceService"]
