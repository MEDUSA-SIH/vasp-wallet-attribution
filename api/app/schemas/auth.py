"""Auth and investigator schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

InvestigatorRole = Literal["investigator", "reviewer", "admin"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InvestigatorCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: InvestigatorRole = "investigator"
    agency: str | None = Field(default=None, max_length=120)


class InvestigatorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    agency: str | None = Field(default=None, max_length=120)
    role: InvestigatorRole | None = None
    is_active: bool | None = None


class InvestigatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    role: InvestigatorRole
    agency: str | None
    is_active: bool
    created_at: datetime


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequestResponse(BaseModel):
    detail: str
    reset_token: str | None = None


class AdminResetPasswordResponse(BaseModel):
    temp_password: str | None = None


__all__ = [
    "InvestigatorRole",
    "LoginRequest",
    "TokenResponse",
    "InvestigatorCreate",
    "InvestigatorUpdate",
    "InvestigatorRead",
    "PasswordChangeRequest",
    "PasswordResetRequest",
    "PasswordResetConfirm",
    "PasswordResetRequestResponse",
    "AdminResetPasswordResponse",
]
