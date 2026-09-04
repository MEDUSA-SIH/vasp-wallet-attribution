"""App errors — custom exceptions and handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AttributionError(Exception):
    """Raised by the attribution engine when an analysis cannot proceed."""


class ProviderError(Exception):
    """Raised by BlockchainProvider implementations on upstream failure."""


class NotFoundError(Exception):
    """Raised when a domain entity cannot be located."""


class AuthorizationError(Exception):
    """Raised on RBAC / authorization failures."""


class ValidationError(Exception):
    """Raised when an input fails business validation (not Pydantic validation)."""


async def attribution_error_handler(request: Request, exc: AttributionError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": "attribution_error", "message": str(exc)},
    )


async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": "provider_error", "message": str(exc)},
    )


async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": str(exc)},
    )


async def authorization_error_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": "authorization_error", "message": str(exc)},
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "validation_error", "message": str(exc)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to a FastAPI app."""
    app.add_exception_handler(AttributionError, attribution_error_handler)
    app.add_exception_handler(ProviderError, provider_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)


__all__ = [
    "AttributionError",
    "ProviderError",
    "NotFoundError",
    "AuthorizationError",
    "ValidationError",
    "register_exception_handlers",
]
