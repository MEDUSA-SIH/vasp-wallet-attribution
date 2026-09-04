"""Attribution orchestration service (Phase 10 + Phase 11)."""
from __future__ import annotations

from uuid import UUID

from app.attribution.engine import AttributionEngine


class AttributionService:
    """Glue between the API and the AttributionEngine."""

    def __init__(self, engine: AttributionEngine | None = None) -> None:
        self.engine = engine or AttributionEngine()

    async def run(self, case_id: UUID, seeds: list[str]):
        return await self.engine.run(case_id, seeds)


__all__ = ["AttributionService"]