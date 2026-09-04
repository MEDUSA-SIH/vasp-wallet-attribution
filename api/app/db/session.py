"""Async DB session helpers (Phase 8)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def make_engine(url: str | None = None) -> AsyncEngine:
    """Create the project's async SQLAlchemy engine (Phase 8)."""
    settings = get_settings()
    return create_async_engine(
        url or settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        echo=settings.db_echo,
        future=True,
    )


def get_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the configured ``async_sessionmaker`` (Phase 8)."""
    if engine is None:
        engine = make_engine()
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


async def healthcheck(engine: AsyncEngine) -> bool:
    """Return True if the DB responds to a trivial SELECT 1."""
    from sqlalchemy import text

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return result.scalar_one() == 1


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Context manager yielding a session and committing/rolling back on exit."""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "make_engine",
    "get_session_factory",
    "healthcheck",
    "session_scope",
]
