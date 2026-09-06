"""Security helper tests — bcrypt, JWT, reset tokens, RBAC."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose.exceptions import JWTError
from pytest import raises

from app.core.security import (
    AuthenticatedInvestigator,
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    hash_password,
    hash_reset_token,
    require_role,
    verify_password,
    verify_reset_token,
)


def test_hash_verify_roundtrip() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip() -> None:
    token = create_access_token(
        "11111111-1111-1111-1111-111111111111",
        extra_claims={"role": "admin", "token_version": 3},
    )
    claims = decode_access_token(token)
    assert claims["sub"] == "11111111-1111-1111-1111-111111111111"
    assert claims["role"] == "admin"
    assert claims["token_version"] == 3
    assert claims["exp"] > claims["iat"]


def test_access_token_expired_rejected() -> None:
    token = create_access_token(
        "11111111-1111-1111-1111-111111111111",
        expires_delta=timedelta(seconds=-10),
    )
    with raises(JWTError):
        decode_access_token(token)


def test_access_token_tampered_rejected() -> None:
    token = create_access_token("11111111-1111-1111-1111-111111111111")
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with raises(JWTError):
        decode_access_token(tampered)


def test_password_reset_token_helpers() -> None:
    raw, hashed = create_password_reset_token()
    assert len(raw) >= 40
    assert hashed != raw
    assert verify_reset_token(raw, hashed)
    assert not verify_reset_token("not-the-token", hashed)


@pytest.mark.parametrize("role", ["investigator", "reviewer", "admin"])
def test_require_role_admin_passes_any(role: str) -> None:
    dep = require_role(role)
    result = dep(AuthenticatedInvestigator(id="1", email="a@b.c", role="admin"))
    assert result.role == "admin"


def test_require_role_matching_role_passes() -> None:
    dep = require_role("reviewer")
    result = dep(AuthenticatedInvestigator(id="1", email="a@b.c", role="reviewer"))
    assert result.role == "reviewer"


def test_require_role_mismatch_is_forbidden() -> None:
    dep = require_role("reviewer")
    inv = AuthenticatedInvestigator(id="1", email="a@b.c", role="investigator")
    with raises(HTTPException) as excinfo:
        dep(inv)
    assert excinfo.value.status_code == 403
