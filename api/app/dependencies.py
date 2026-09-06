"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose.exceptions import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import AuthenticatedInvestigator, decode_access_token
from app.db.models.investigator import Investigator
from app.providers.base import BlockchainProvider, ProviderRegistry

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession bound to the request's engine."""
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_redis(request: Request):
    """Return the Redis client stored on app.state."""
    return request.app.state.redis


RedisDep = Annotated[object, Depends(get_redis)]


async def get_provider_registry(request: Request) -> ProviderRegistry:
    """Return the active :class:`ProviderRegistry`."""
    return request.app.state.provider_registry


ProviderRegistryDep = Annotated[ProviderRegistry, Depends(get_provider_registry)]


async def get_provider_for_chain(
    chain: str,
    registry: ProviderRegistry = Depends(get_provider_registry),
) -> BlockchainProvider:
    """Resolve a provider by chain code or 400 if unknown."""
    try:
        return registry.get(chain)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown or unsupported chain '{chain}'",
        ) from exc


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{get_settings().api_prefix}/auth/login")


async def _investigator_from_token(
    token: str, session: AsyncSession
) -> AuthenticatedInvestigator | None:
    """Decode a JWT and load the matching active investigator, or return None."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    subject = payload.get("sub")
    token_version = payload.get("token_version")
    if subject is None or token_version is None:
        return None
    try:
        investigator_id = UUID(subject)
    except ValueError:
        return None
    result = await session.execute(select(Investigator).where(Investigator.id == investigator_id))
    inv = result.scalar_one_or_none()
    if inv is None or not inv.is_active:
        return None
    if int(inv.token_version) != int(token_version):
        return None
    return AuthenticatedInvestigator(
        id=str(inv.id),
        email=inv.email,
        role=inv.role,
        agency=inv.agency,
    )


async def get_current_investigator(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> AuthenticatedInvestigator:
    """Resolve the Bearer JWT to a live, active investigator or 401."""
    auth = await _investigator_from_token(token, session)
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


async def get_optional_current_investigator(
    request: Request, session: SessionDep
) -> AuthenticatedInvestigator | None:
    """Like get_current_investigator but returns None when no valid token is present."""
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    if not token:
        return None
    return await _investigator_from_token(token, session)


CurrentInvestigatorDep = Annotated[AuthenticatedInvestigator, Depends(get_current_investigator)]
OptionalInvestigatorDep = Annotated[
    AuthenticatedInvestigator | None, Depends(get_optional_current_investigator)
]


__all__ = [
    "SettingsDep",
    "SessionDep",
    "RedisDep",
    "ProviderRegistryDep",
    "CurrentInvestigatorDep",
    "OptionalInvestigatorDep",
    "get_provider_for_chain",
]
