"""Admin endpoints — app settings and admin helpers."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/settings")
async def admin_settings(request: Request):
    settings = request.app.state.settings
    return {
        "app_name": settings.app_name,
        "version": "0.1.0",
        "demo_mode": settings.demo_mode,
        "env": settings.app_env,
    }


__all__ = ["router"]
