"""Security primitives (Phase 25).

This module provides:
- Password hashing helpers (passlib bcrypt).
- JWT helpers (python-jose).
- FastAPI dependency stubs for `get_current_investigator` and `require_role`.

Real authentication flows will be wired in Stage 1+; the helpers below are
kept minimal so subsequent phases can plug in concrete handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext

from app.config import Settings, get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True, slots=True)
class AuthenticatedInvestigator:
    """Lightweight DTO returned by `get_current_investigator`."""

    id: str
    email: str
    role: str
    agency: str | None = None


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    *,
    settings: Settings | None = None,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT for the given subject."""
    settings = settings or get_settings()
    now = datetime.now(tz=UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_expires_minutes))
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Decode a JWT and return its claims, raising on failure."""
    settings = settings or get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


def require_role(role: str):
    """Build a dependency that enforces the given role (Phase 25 RBAC)."""

    async def _dep(investigator: AuthenticatedInvestigator) -> AuthenticatedInvestigator:
        if investigator.role != role and investigator.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return investigator

    return _dep


__all__ = [
    "AuthenticatedInvestigator",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "require_role",
]
