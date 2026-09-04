"""Health endpoint test."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_create_app() -> None:
    app = create_app()
    assert app.title.startswith("SIH26182")


def test_health_endpoint() -> None:
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["demo_mode"] is True
        assert "version" in body
