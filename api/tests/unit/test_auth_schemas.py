"""Auth schema validation tests."""

from __future__ import annotations

from datetime import datetime

from pydantic import ValidationError
from pytest import raises

from app.schemas.auth import (
    InvestigatorCreate,
    InvestigatorRead,
    PasswordResetConfirm,
)


def test_create_rejects_unknown_role() -> None:
    with raises(ValidationError):
        InvestigatorCreate(email="a@b.c", full_name="Alice", password="secret123", role="superuser")


def test_create_rejects_bad_email() -> None:
    with raises(ValidationError):
        InvestigatorCreate(email="not-an-email", full_name="Alice", password="secret123")


def test_create_rejects_short_password() -> None:
    with raises(ValidationError):
        InvestigatorCreate(email="a@b.c", full_name="Alice", password="short")


def test_create_valid_minimal() -> None:
    inv = InvestigatorCreate(email="a@b.c", full_name="Alice", password="secret123")
    assert inv.role == "investigator"
    assert inv.agency is None


def test_create_valid_all_fields() -> None:
    inv = InvestigatorCreate(
        email="a@b.c", full_name="Alice", password="secret123", role="reviewer", agency="I4C"
    )
    assert inv.role == "reviewer"
    assert inv.agency == "I4C"


def test_reset_confirm_rejects_short_password() -> None:
    with raises(ValidationError):
        PasswordResetConfirm(token="tok", new_password="short")


def test_investigator_read_from_attributes() -> None:
    row = type(
        "Row",
        (),
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "a@b.c",
            "full_name": "Alice",
            "role": "investigator",
            "agency": None,
            "is_active": True,
            "created_at": datetime(2026, 1, 1, 0, 0, 0),
        },
    )()
    read = InvestigatorRead.model_validate(row)
    assert read.role == "investigator"
