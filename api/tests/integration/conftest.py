"""Shared fixtures for DB-backed integration tests (skip if Postgres is down)."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.base import BaseModel


@dataclass
class DBSync:
    """Handle to a disposable schema, usable from sync test bodies."""

    connection_string: str

    async def _engine(self):
        return create_async_engine(self.connection_string, future=True)

    async def _ddl(self, create: bool) -> None:
        engine = await self._engine()
        try:
            async with engine.begin() as conn:
                if create:
                    await conn.run_sync(BaseModel.metadata.create_all)
                else:
                    await conn.run_sync(BaseModel.metadata.drop_all)
        finally:
            await engine.dispose()

    def setup(self) -> None:
        asyncio.run(self._ddl(True))

    def teardown(self) -> None:
        with contextlib.suppress(Exception):
            asyncio.run(self._ddl(False))

    def session_factory(self):
        engine = create_async_engine(self.connection_string, future=True)
        return async_sessionmaker(bind=engine, expire_on_commit=False), engine


@pytest.fixture(scope="module")
def auth_db():
    """Create a disposable Postgres schema; skip the whole module if unreachable."""
    settings = get_settings()
    db = DBSync(settings.database_url)
    try:
        db.setup()
    except Exception as exc:  # noqa: BLE001 – reachability probe
        pytest.skip(f"Postgres unreachable: {exc}")
    yield db
    db.teardown()
