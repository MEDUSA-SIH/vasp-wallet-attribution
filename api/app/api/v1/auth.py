"""Auth endpoints — login, current investigator, password management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.core.security import create_access_token
from app.dependencies import CurrentInvestigatorDep, OptionalInvestigatorDep, SessionDep
from app.schemas.auth import (
    InvestigatorRead,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    TokenResponse,
)
from app.services import investigator_service as svc

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    try:
        investigator = await svc.authenticate(session, str(payload.email), payload.password)
    except svc.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        ) from None
    except svc.InactiveAccountError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive"
        ) from None
    await session.commit()
    token = create_access_token(
        str(investigator.id),
        extra_claims={"role": investigator.role, "token_version": investigator.token_version},
    )
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(investigator: OptionalInvestigatorDep) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=InvestigatorRead)
async def me(investigator: CurrentInvestigatorDep, session: SessionDep) -> InvestigatorRead:
    row = await svc.get_by_id(session, UUID(investigator.id))
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Investigator not found"
        )
    return InvestigatorRead.model_validate(row)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    investigator: CurrentInvestigatorDep,
    session: SessionDep,
) -> Response:
    row = await svc.get_by_id(session, UUID(investigator.id))
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Investigator not found"
        )
    try:
        await svc.change_own_password(session, row, payload.current_password, payload.new_password)
    except svc.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        ) from None
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    payload: PasswordResetRequest, session: SessionDep
) -> PasswordResetRequestResponse:
    raw = await svc.issue_password_reset(session, str(payload.email))
    await session.commit()
    return PasswordResetRequestResponse(
        detail="If the account exists, a reset token has been issued", reset_token=raw
    )


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(payload: PasswordResetConfirm, session: SessionDep) -> Response:
    try:
        await svc.consume_password_reset(session, payload.token, payload.new_password)
    except svc.InvalidResetTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        ) from None
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
