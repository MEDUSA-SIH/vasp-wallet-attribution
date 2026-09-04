"""Attribution router (Phase 10 + Phase 11).

Exposes the minimal smoke path for WP-11:

    POST /api/v1/attribution/run
    {
        "case_id": "...",          # optional
        "suspect_address": "...",
        "chain": "ethereum"
    }

The handler delegates to :meth:`AttributionService.run_demo_attribution`
which walks the demo graph and returns a structured candidate list.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import ProviderRegistryDep
from app.services.attribution_service import AttributionService

router = APIRouter()
_service = AttributionService()


class AttributionRunRequest(BaseModel):
    """Request body for ``POST /attribution/run`` (Phase 10 / WP-11)."""

    suspect_address: str = Field(min_length=1, max_length=255)
    chain: str = Field(default="ethereum", max_length=32)
    case_id: UUID | None = None
    max_hops: int = Field(default=5, ge=1, le=10)


class AttributionRunResponse(BaseModel):
    """Response shape for ``POST /attribution/run``."""

    run_id: str
    case_id: str | None = None
    suspect_address: str
    chain: str
    outcome: str
    demo_mode: bool
    hops_used: int
    insufficient_evidence: bool
    candidates: list[dict[str, Any]]
    started_at: str
    finished_at: str | None
    notes: list[str]


@router.post("/run", response_model=AttributionRunResponse)
async def run_attribution_endpoint(
    payload: AttributionRunRequest,
    registry: ProviderRegistryDep,
) -> AttributionRunResponse:
    """Smoke endpoint used by the offline demo path (WP-11)."""
    try:
        # Validate the chain has a provider up front for a friendlier 400.
        registry.get(payload.chain)
    except KeyError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or unsupported chain '{payload.chain}'",
        ) from exc

    result = await _service.run_demo_attribution(
        payload.suspect_address,
        chain=payload.chain,
        case_id=payload.case_id,
        registry=registry,
        max_hops=payload.max_hops,
    )
    return AttributionRunResponse(**result.as_dict())


__all__ = ["router", "AttributionRunRequest", "AttributionRunResponse"]