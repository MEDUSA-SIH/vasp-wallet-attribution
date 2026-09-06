"""Investigator service — auth, user management, password reset.

All functions take an AsyncSession and mutate it; routers commit.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import (
    create_password_reset_token,
    hash_password,
    verify_password,
    verify_reset_token,
)
from app.db.models.investigator import Investigator
from app.db.models.password_reset_token import PasswordResetToken
from app.schemas.auth import InvestigatorCreate, InvestigatorUpdate


class DuplicateEmailError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


class InvalidResetTokenError(Exception):
    pass


async def authenticate(session: AsyncSession, email: str, password: str) -> Investigator:
    inv = await get_by_email(session, email)
    if inv is None or not verify_password(password, inv.hashed_password):
        raise InvalidCredentialsError
    if not inv.is_active:
        raise InactiveAccountError
    return inv


async def get_by_id(session: AsyncSession, investigator_id: UUID) -> Investigator | None:
    result = await session.execute(select(Investigator).where(Investigator.id == investigator_id))
    return result.scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> Investigator | None:
    result = await session.execute(select(Investigator).where(Investigator.email == email.lower()))
    return result.scalar_one_or_none()


async def list_investigators(
    session: AsyncSession, *, page: int = 1, page_size: int = 50
) -> tuple[list[Investigator], int]:
    total = await session.scalar(select(func.count()).select_from(Investigator))
    result = await session.execute(
        select(Investigator)
        .order_by(Investigator.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), int(total or 0)


async def create_investigator(session: AsyncSession, payload: InvestigatorCreate) -> Investigator:
    if await get_by_email(session, str(payload.email)):
        raise DuplicateEmailError
    inv = Investigator(
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        agency=payload.agency,
    )
    session.add(inv)
    return inv


async def update_investigator(
    session: AsyncSession, investigator: Investigator, payload: InvestigatorUpdate
) -> Investigator:
    data = payload.model_dump(exclude_unset=True)
    role_changed = "role" in data and data["role"] != investigator.role
    active_changed = "is_active" in data and data["is_active"] != investigator.is_active
    for field in ("full_name", "agency", "role", "is_active"):
        if field in data:
            setattr(investigator, field, data[field])
    if role_changed or active_changed:
        investigator.token_version += 1
    return investigator


async def change_own_password(
    session: AsyncSession, investigator: Investigator, current: str, new: str
) -> None:
    if not verify_password(current, investigator.hashed_password):
        raise InvalidCredentialsError
    investigator.hashed_password = hash_password(new)
    investigator.token_version += 1


async def issue_password_reset(session: AsyncSession, email: str) -> str | None:
    inv = await get_by_email(session, email)
    if inv is None:
        return None
    settings = get_settings()
    now = datetime.now(tz=UTC)
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.investigator_id == inv.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw, token_hash = create_password_reset_token()
    session.add(
        PasswordResetToken(
            investigator_id=inv.id,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=settings.password_reset_token_ttl_minutes),
        )
    )
    return raw if settings.demo_password_reset_echo else None


async def consume_password_reset(
    session: AsyncSession, raw_token: str, new_password: str
) -> Investigator:
    now = datetime.now(tz=UTC)
    result = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
    )
    for row in result.scalars().all():
        if not verify_reset_token(raw_token, row.token_hash):
            continue
        inv = await get_by_id(session, row.investigator_id)
        if inv is None or not inv.is_active:
            raise InvalidResetTokenError
        inv.hashed_password = hash_password(new_password)
        inv.token_version += 1
        row.used_at = now
        return inv
    raise InvalidResetTokenError


async def admin_reset_password(
    session: AsyncSession, investigator: Investigator, new_password: str | None
) -> str:
    password = new_password or secrets.token_urlsafe(12)
    investigator.hashed_password = hash_password(password)
    investigator.token_version += 1
    return password


__all__ = [
    "DuplicateEmailError",
    "InvalidCredentialsError",
    "InactiveAccountError",
    "InvalidResetTokenError",
    "authenticate",
    "get_by_id",
    "get_by_email",
    "list_investigators",
    "create_investigator",
    "update_investigator",
    "change_own_password",
    "issue_password_reset",
    "consume_password_reset",
    "admin_reset_password",
]
