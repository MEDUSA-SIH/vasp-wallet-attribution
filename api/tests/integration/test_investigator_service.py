"""Investigator service integration tests (needs Postgres)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from pytest import raises
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.db.models.investigator import Investigator
from app.schemas.auth import InvestigatorCreate, InvestigatorUpdate
from app.services import investigator_service as svc


def _seed(
    db, email: str, password: str = "secret123", role: str = "investigator", *, active: bool = True
) -> None:
    async def _run() -> None:
        factory, engine = db.session_factory()
        try:
            async with factory() as session:  # type: ignore[arg-type]
                inv = await svc.create_investigator(
                    session,
                    InvestigatorCreate(email=email, full_name="Seed", password=password, role=role),
                )
                if not active:
                    inv.is_active = False
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_create_and_authenticate(auth_db) -> None:
    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                inv = await svc.authenticate(session, "alice@example.com", "secret123")
                assert inv.email == "alice@example.com"
                assert inv.is_active is True

            async with factory() as session:
                with raises(svc.InvalidCredentialsError):
                    await svc.authenticate(session, "alice@example.com", "wrong")

            async with factory() as session:
                with raises(svc.InvalidCredentialsError):
                    await svc.authenticate(session, "ghost@example.com", "whatever")
        finally:
            await engine.dispose()

    _seed(auth_db, "alice@example.com")
    asyncio.run(_run())


def test_duplicate_email_raises(auth_db) -> None:
    _seed(auth_db, "dup@example.com")

    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                try:
                    await svc.create_investigator(
                        session,
                        InvestigatorCreate(
                            email="dup@example.com", full_name="Dup", password="secret123"
                        ),
                    )
                    raise AssertionError("duplicate must raise")
                except svc.DuplicateEmailError:
                    pass
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_change_password_bumps_token_version(auth_db) -> None:
    _seed(auth_db, "pwd@example.com")

    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                inv = await svc.get_by_email(session, "pwd@example.com")
                assert inv is not None
                version_before = inv.token_version
                await svc.change_own_password(session, inv, "secret123", "newsecret1")
                assert inv.token_version == version_before + 1
                await session.commit()

            async with factory() as session:
                after = await svc.authenticate(session, "pwd@example.com", "newsecret1")
                assert after is not None
                assert verify_password("newsecret1", after.hashed_password)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_update_role_bumps_token_version(auth_db) -> None:
    _seed(auth_db, "role@example.com")

    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                inv = await svc.get_by_email(session, "role@example.com")
                assert inv is not None
                version_before = inv.token_version
                await svc.update_investigator(session, inv, InvestigatorUpdate(role="reviewer"))
                assert inv.role == "reviewer"
                assert inv.token_version == version_before + 1
                await session.commit()
            async with factory() as session:
                inv = await svc.get_by_email(session, "role@example.com")
                assert inv is not None
                assert inv.role == "reviewer"
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_password_reset_issue_and_consume(auth_db) -> None:
    _seed(auth_db, "reset@example.com")

    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                raw = await svc.issue_password_reset(session, "reset@example.com")
                assert raw is not None, "demo echo enabled -> raw token returned"
                await session.commit()

            async with factory() as session:
                inv = await svc.consume_password_reset(session, raw, "afterreset1")
                assert inv is not None
                await session.commit()

            async with factory() as session:
                after = await svc.authenticate(session, "reset@example.com", "afterreset1")
                assert after is not None
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_issue_reset_for_unknown_email_returns_none(auth_db) -> None:
    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                raw = await svc.issue_password_reset(session, "ghost@example.com")
                assert raw is None
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_inactive_account_authenticate_fails(auth_db) -> None:
    _seed(auth_db, "off@example.com", active=False)

    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                with raises(svc.InactiveAccountError):
                    await svc.authenticate(session, "off@example.com", "secret123")
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_consume_reset_invalid_token_raises(auth_db) -> None:
    async def _run() -> None:
        factory, engine = auth_db.session_factory()
        try:
            async with factory() as session:
                with raises(svc.InvalidResetTokenError):
                    await svc.consume_password_reset(session, "bogus-token", "newsecret1")
        finally:
            await engine.dispose()

    asyncio.run(_run())
