"""Tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    """The health endpoint should report a successful application state."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "AI Engineering Product Lab",
        "version": "0.2.0",
    }