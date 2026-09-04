"""Reports router (Phase 17)."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.report_service import ReportService

router = APIRouter()
_service = ReportService()


@router.post("/generate")
async def generate_report(payload: dict):
    return await _service.generate(payload["case_id"], payload["title"])


__all__ = ["router"]