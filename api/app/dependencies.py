"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.security import AuthenticatedInvestigator, require_role
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


async def get_current_investigator_stub() -> AuthenticatedInvestigator:
    """Placeholder until Phase 25 auth is implemented.

    The real implementation will validate a JWT and load the investigator.
    """
    return AuthenticatedInvestigator(
        id="00000000-0000-0000-0000-000000000000",
        email="scaffold@example.com",
        role="analyst",
    )


CurrentInvestigatorDep = Annotated[
    AuthenticatedInvestigator, Depends(get_current_investigator_stub)
]


def require_role_stub(role: str):
    """Factory that returns a dependency enforcing a role."""
    return require_role(role)


__all__ = [
    "SettingsDep",
    "SessionDep",
    "RedisDep",
    "ProviderRegistryDep",
    "CurrentInvestigatorDep",
    "require_role_stub",
    "get_provider_for_chain",
]
