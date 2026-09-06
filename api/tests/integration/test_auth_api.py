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
    reset: bool = True,
) -> None:
    # Module-scoped auth_db persists across tests, so reset the schema first to
    # give each test a clean DB before seeding the shared alice account.
    if reset:
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
        header, payload, signature = token.split(".")
        flipped = signature[:10] + ("A" if signature[10] != "A" else "B") + signature[11:]
        tampered = f"{header}.{payload}.{flipped}"
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


def _admin(auth_db) -> None:
    _seed(auth_db, email="admin@example.com", role="admin")
    _seed(auth_db, email="analyst@example.com", role="investigator", reset=False)


def test_admin_can_create_and_list(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        admin_token = _login(c, "admin@example.com", "secret123")
        r = c.post(
            "/api/v1/admin/investigators",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "new@example.com",
                "full_name": "New",
                "password": "secret123",
                "role": "reviewer",
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["role"] == "reviewer"
        listed = c.get(
            "/api/v1/admin/investigators?page=1&page_size=50",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert listed.status_code == 200
        emails = {i["email"] for i in listed.json()["items"]}
        assert {"admin@example.com", "analyst@example.com", "new@example.com"}.issubset(emails)


def test_non_admin_cannot_access_admin_routes(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        analyst_token = _login(c, "analyst@example.com", "secret123")
        r = c.get(
            "/api/v1/admin/investigators", headers={"Authorization": f"Bearer {analyst_token}"}
        )
    assert r.status_code == 403
    assert r.json()["detail"]


def test_admin_create_duplicate_email_409(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        admin_token = _login(c, "admin@example.com", "secret123")
        r = c.post(
            "/api/v1/admin/investigators",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "analyst@example.com", "full_name": "Again", "password": "secret123"},
        )
    assert r.status_code == 409


def test_admin_patch_invalidates_role_tokens(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        admin_token = _login(c, "admin@example.com", "secret123")
        analyst_token = _login(c, "analyst@example.com", "secret123")
        listed = c.get(
            "/api/v1/admin/investigators?page=1&page_size=50",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()
        analyst_id = next(i["id"] for i in listed["items"] if i["email"] == "analyst@example.com")
        patched = c.patch(
            f"/api/v1/admin/investigators/{analyst_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"role": "reviewer"},
        )
        assert patched.status_code == 200
        assert patched.json()["role"] == "reviewer"
        stale = c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {analyst_token}"})
        assert stale.status_code == 401


def test_password_reset_flow(auth_db) -> None:
    _seed(auth_db, email="forgot@example.com")
    with _client() as c:
        r = c.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "forgot@example.com"},
        )
        assert r.status_code == 202, r.text
        raw = r.json().get("reset_token")
        assert raw, "demo echo enabled -> token returned"
        done = c.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw, "new_password": "afterreset1"},
        )
        assert done.status_code == 204
        token = _login(c, "forgot@example.com", "afterreset1")
        assert (
            c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code
            == 200
        )


def test_password_reset_invalid_token_400(auth_db) -> None:
    _seed(auth_db, email="forgot2@example.com")
    with _client() as c:
        r = c.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": "bogus", "new_password": "afterreset1"},
        )
    assert r.status_code == 400


def test_admin_reset_password_generates_temp_password(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        admin_token = _login(c, "admin@example.com", "secret123")
        listed = c.get(
            "/api/v1/admin/investigators?page=1&page_size=50",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()
        analyst_id = next(i["id"] for i in listed["items"] if i["email"] == "analyst@example.com")
        r = c.post(
            f"/api/v1/admin/investigators/{analyst_id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={},
        )
        assert r.status_code == 200
        temp = r.json().get("temp_password")
        assert temp
        assert _login(c, "analyst@example.com", temp)  # temp password works


def test_admin_routes_unauthenticated_401(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        r = c.get("/api/v1/admin/investigators")
    assert r.status_code == 401


def test_admin_get_unknown_investigator_404(auth_db) -> None:
    _admin(auth_db)
    with _client() as c:
        admin_token = _login(c, "admin@example.com", "secret123")
        r = c.get(
            f"/api/v1/admin/investigators/{uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert r.status_code == 404


def test_password_reset_unknown_email_no_enumeration(auth_db) -> None:
    _seed(auth_db, email="known@example.com")
    with _client() as c:
        known = c.post("/api/v1/auth/password-reset/request", json={"email": "known@example.com"})
        unknown = c.post(
            "/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}
        )
    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json()["detail"] == unknown.json()["detail"]
    assert unknown.json().get("reset_token") is None


def test_password_reset_token_consumed_once(auth_db) -> None:
    _seed(auth_db, email="onetimedue@example.com")
    with _client() as c:
        raw = c.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "onetimedue@example.com"},
        ).json()["reset_token"]
        first = c.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw, "new_password": "afterreset1"},
        )
        again = c.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": raw, "new_password": "afterreset2"},
        )
    assert first.status_code == 204
    assert again.status_code == 400
