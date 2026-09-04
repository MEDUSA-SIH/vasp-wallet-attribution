"""Attribution router (Phase 10 + Phase 11)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.attribution.engine import run_attribution

router = APIRouter()


@router.post("/run")
async def run_attribution_endpoint(payload: dict):
    case_id = UUID(payload["case_id"])
    seeds = payload.get("seeds", [])
    result = await run_attribution(case_id, seeds)
    return {"case_id": str(result.case_id), "rankings": result.rankings}


__all__ = ["router"]