"""Admin investigator management — RBAC guarded (admin only)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_role
from app.dependencies import SessionDep
from app.schemas.auth import (
    AdminResetPasswordResponse,
    InvestigatorCreate,
    InvestigatorRead,
    InvestigatorUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services import investigator_service as svc

router = APIRouter(dependencies=[Depends(require_role("admin"))])


@router.get("", response_model=PaginatedResponse)
async def list_investigators(
    session: SessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> PaginatedResponse:
    items, total = await svc.list_investigators(session, page=page, page_size=page_size)
    return PaginatedResponse(
        items=[InvestigatorRead.model_validate(i) for i in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=InvestigatorRead, status_code=status.HTTP_201_CREATED)
async def create_investigator(payload: InvestigatorCreate, session: SessionDep) -> InvestigatorRead:
    try:
        inv = await svc.create_investigator(session, payload)
    except svc.DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from None
    await session.commit()
    return InvestigatorRead.model_validate(inv)


@router.get("/{investigator_id}", response_model=InvestigatorRead)
async def get_investigator(investigator_id: UUID, session: SessionDep) -> InvestigatorRead:
    inv = await svc.get_by_id(session, investigator_id)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigator not found")
    return InvestigatorRead.model_validate(inv)


@router.patch("/{investigator_id}", response_model=InvestigatorRead)
async def update_investigator(
    investigator_id: UUID, payload: InvestigatorUpdate, session: SessionDep
) -> InvestigatorRead:
    inv = await svc.get_by_id(session, investigator_id)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigator not found")
    await svc.update_investigator(session, inv, payload)
    await session.commit()
    return InvestigatorRead.model_validate(inv)


@router.post("/{investigator_id}/reset-password", response_model=AdminResetPasswordResponse)
async def reset_password(investigator_id: UUID, session: SessionDep) -> AdminResetPasswordResponse:
    inv = await svc.get_by_id(session, investigator_id)
    if inv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigator not found")
    temp = await svc.admin_reset_password(session, inv, None)
    await session.commit()
    return AdminResetPasswordResponse(temp_password=temp)


__all__ = ["router"]
