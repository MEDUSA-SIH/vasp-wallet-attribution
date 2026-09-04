"""FastAPI application — creates the app and wires dependencies.

Creates the app, wires lifespan (DB + Redis), CORS, exception handlers and
versioned routers. Currently exposes only the health router as a smoke
test; domain routers will be mounted by later stages.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis_asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import __version__
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.base import BaseModel

log = ""  # placeholder, real logger set in lifespan


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise DB engine, session factory, Redis and provider registry."""
    settings = app.state.settings

    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        echo=settings.db_echo,
        future=True,
    )
    app.state.db_engine = engine
    app.state.db_session_factory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    app.state.redis = redis_asyncio.from_url(
        settings.redis_url, encoding="utf-8", decode_responses=True
    )

    # Provider registry — picks the demo provider when DEMO_MODE is on,
    # otherwise uses the live chain providers. The demo provider serves
    # the local synthetic dataset so the app works without API keys.
    from app.providers.factory import build_default_provider_registry

    app.state.provider_registry = build_default_provider_registry(settings)

    structlog = get_logger("api.lifespan")
    structlog.info(
        "application.startup",
        version=__version__,
        demo_mode=settings.demo_mode,
        env=settings.app_env,
        chains=app.state.provider_registry.available(),
    )

    try:
        yield
    finally:
        structlog.info("application.shutdown")
        await app.state.redis.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""
    configure_logging()

    from app.api.v1 import api_v1_router

    app = FastAPI(
        title="SIH26182 VASP Wallet Attribution API",
        version=__version__,
        description=(
            "Backend API for the SIH26182 VASP Wallet Attribution system. "
            "Stage 1 – synthetic dataset + offline DemoBlockchainProvider."
        ),
        lifespan=lifespan,
    )

    from app.config import get_settings

    settings = get_settings()
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_prefix)

    # Ensure all SQLAlchemy models are imported before metadata creation.
    from app.db import models  # noqa: F401

    _ = BaseModel.metadata  # touch to silence linter

    return app


app = create_app()


__all__ = ["app", "create_app"]
break lint
