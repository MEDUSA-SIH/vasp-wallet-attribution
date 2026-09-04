"""Report service — builds investigation reports."""

from __future__ import annotations


class ReportService:
    """Stub report service – will eventually render PDF / DOCX artefacts."""

    async def generate(self, case_id: str, title: str) -> dict[str, str]:
        return {"status": "queued", "case_id": case_id, "title": title}


__all__ = ["ReportService"]
