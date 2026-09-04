"""Case service — handles investigations and cases.

Real CRUD operations will live here.  Stage 0 exposes only ``ping`` so other
modules can import without breaking.
"""

from __future__ import annotations

from uuid import UUID


class CaseService:
    """Stub case service."""

    async def ping(self, case_id: UUID) -> str:
        return f"case:{case_id}"


__all__ = ["CaseService"]
