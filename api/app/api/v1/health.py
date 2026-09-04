"""Health router (Phase 25)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import __version__
from app.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Liveness probe."""
    demo_mode = getattr(request.app.state, "settings", get_settings()).demo_mode
    return HealthResponse(status="ok", demo_mode=demo_mode, version=__version__)


__all__ = ["router"]
