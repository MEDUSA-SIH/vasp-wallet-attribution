"""Wallets router (Phase 11)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_wallets():
    return {"items": []}


@router.post("/")
async def create_wallet(payload: dict):
    return {"id": "00000000-0000-0000-0000-000000000000", **payload}


@router.get("/{wallet_id}")
async def get_wallet(wallet_id: UUID):
    return {"id": str(wallet_id)}


__all__ = ["router"]