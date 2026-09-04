"""Cases router (Phase 12)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.services.case_service import CaseService

router = APIRouter()
_service = CaseService()


@router.get("/")
async def list_cases():
    return {"items": [], "page": 1}


@router.post("/")
async def create_case(payload: dict):
    return {"id": "00000000-0000-0000-0000-000000000000", **payload}


@router.get("/{case_id}")
async def get_case(case_id: UUID):
    return await _service.ping(case_id)


__all__ = ["router"]
