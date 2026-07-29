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
        "version": "0.3.0",
    }


def test_chat_endpoint_returns_business_response() -> None:
    """A valid business request should return a structured response."""
    response = client.post(
        "/chat",
        json={
            "message": "Help me improve customer support.",
            "role": "business",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["role"] == "business"
    assert response_data["role_name"] == "Business Assistant"
    assert response_data["provider"] == "MockLLMProvider"
    assert "Help me improve customer support." in response_data["reply"]


def test_chat_endpoint_uses_default_role() -> None:
    """A request without a role should use customer support."""
    response = client.post(
        "/chat",
        json={
            "message": "How can I speak with someone?",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["role"] == "support"
    assert response_data["role_name"] == "Customer Support Assistant"


def test_chat_endpoint_falls_back_for_unknown_role() -> None:
    """An unknown role should safely use the configured default role."""
    response = client.post(
        "/chat",
        json={
            "message": "What time do you close?",
            "role": "doctor",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["role"] == "support"


def test_chat_endpoint_rejects_empty_message() -> None:
    """An empty message should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "message": "",
            "role": "support",
        },
    )

    assert response.status_code == 422


def test_chat_endpoint_rejects_missing_message() -> None:
    """A missing message should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "role": "business",
        },
    )

    assert response.status_code == 422


def test_chat_endpoint_rejects_wrong_message_type() -> None:
    """A non-string message should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "message": ["invalid", "message"],
            "role": "support",
        },
    )

    assert response.status_code == 422