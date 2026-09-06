"""Auth API integration tests (needs Postgres)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.auth import InvestigatorCreate
from app.services import investigator_service as svc


def _seed(
    db,
    email: str = "alice@example.com",
    password: str = "secret123",
    *,
    role: str = "investigator",
    active: bool = True,
) -> None:
    # Module-scoped auth_db persists across tests, so reset the schema first to
    # give each test a clean DB before seeding the shared alice account.
    db.teardown()
    db.setup()

    async def _run() -> None:
        factory, engine = db.session_factory()
        try:
            async with factory() as session:
                inv = await svc.create_investigator(
                    session,
                    InvestigatorCreate(
                        email=email, full_name="Alice", password=password, role=role
                    ),
                )
                if not active:
                    inv.is_active = False
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_run())


def _client() -> TestClient:
    return TestClient(create_app())


def _login(c: TestClient, email: str, password: str) -> str:
    r = c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_login_ok_and_me(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        token = _login(c, "alice@example.com", "secret123")
        me = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "investigator"
    assert body["is_active"] is True


def test_login_wrong_password_401(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        r = c.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "nope"})
    assert r.status_code == 401


def test_login_inactive_403(auth_db) -> None:
    _seed(auth_db, active=False)
    with _client() as c:
        r = c.post(
            "/api/v1/auth/login", json={"email": "alice@example.com", "password": "secret123"}
        )
    assert r.status_code == 403


def test_me_without_token_401(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        r = c.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_with_tampered_token_401(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        token = _login(c, "alice@example.com", "secret123")
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401


def test_me_with_invalid_uuid_subject_401(auth_db) -> None:
    # No seed needed; token with a bad subject must 401.
    from app.core.security import create_access_token

    token = create_access_token("not-a-uuid")
    with _client() as c:
        r = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_change_password_invalidates_old_token(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        token = _login(c, "alice@example.com", "secret123")
        r = c.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "secret123", "new_password": "newsecret1"},
        )
        assert r.status_code == 204
        stale = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert stale.status_code == 401
        fresh = _login(c, "alice@example.com", "newsecret1")
        assert (
            c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fresh}"}).status_code
            == 200
        )


def test_change_password_wrong_current_400(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        token = _login(c, "alice@example.com", "secret123")
        r = c.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "wrong", "new_password": "newsecret1"},
        )
    assert r.status_code == 400


def test_logout_is_safe_noop(auth_db) -> None:
    _seed(auth_db)
    with _client() as c:
        token = _login(c, "alice@example.com", "secret123")
        r = c.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204
