"""Versioned v1 routers."""
from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.attribution import router as attribution_router
from app.api.v1.cases import router as cases_router
from app.api.v1.health import router as health_router
from app.api.v1.reports import router as reports_router
from app.api.v1.wallets import router as wallets_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_v1_router.include_router(wallets_router, prefix="/wallets", tags=["wallets"])
api_v1_router.include_router(attribution_router, prefix="/attribution", tags=["attribution"])
api_v1_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_v1_router.include_router(admin_router, prefix="/admin", tags=["admin"])

__all__ = ["api_v1_router"]