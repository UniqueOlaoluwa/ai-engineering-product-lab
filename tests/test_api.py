"""Tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app.api import app
from app.database import initialize_database

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    """The health endpoint should report a successful application state."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "AI Engineering Product Lab",
        "version": "0.5.0",
    }


def test_chat_endpoint_returns_business_response() -> None:
    """A valid business request should return a stored response."""
    response = client.post(
        "/chat",
        json={
            "message": "Help me improve customer support.",
            "role": "business",
            "session_id": "api-test-session",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["message_id"] >= 1
    assert response_data["session_id"] == "api-test-session"
    assert response_data["role"] == "business"
    assert response_data["role_name"] == "Business Assistant"
    assert response_data["provider"] == "MockLLMProvider"
    assert "Help me improve customer support." in response_data["reply"]


def test_chat_endpoint_uses_default_role_and_session() -> None:
    """Missing optional fields should use configured defaults."""
    response = client.post(
        "/chat",
        json={
            "message": "How can I speak with someone?",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["session_id"] == "default-session"
    assert response_data["role"] == "support"
    assert response_data["role_name"] == "Customer Support Assistant"


def test_chat_endpoint_falls_back_for_unknown_role() -> None:
    """An unknown role should safely use the configured default role."""
    response = client.post(
        "/chat",
        json={
            "message": "What time do you close?",
            "role": "doctor",
            "session_id": "fallback-test-session",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["role"] == "support"
    assert response_data["session_id"] == "fallback-test-session"


def test_chat_endpoint_rejects_empty_message() -> None:
    """An empty message should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "message": "",
            "role": "support",
            "session_id": "validation-session",
        },
    )

    assert response.status_code == 422


def test_chat_endpoint_rejects_missing_message() -> None:
    """A missing message should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "role": "business",
            "session_id": "validation-session",
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
            "session_id": "validation-session",
        },
    )

    assert response.status_code == 422


def test_get_conversation_returns_saved_messages() -> None:
    """A known session should return its stored conversation history."""
    initialize_database()

    session_id = "conversation-history-test"

    first_response = client.post(
        "/chat",
        json={
            "message": "What is workflow automation?",
            "role": "business",
            "session_id": session_id,
        },
    )

    second_response = client.post(
        "/chat",
        json={
            "message": "Give me one practical example.",
            "role": "business",
            "session_id": session_id,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get(f"/conversations/{session_id}")
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["session_id"] == session_id
    assert response_data["message_count"] >= 2
    assert len(response_data["messages"]) >= 2

    latest_messages = response_data["messages"][-2:]

    assert latest_messages[0]["role"] == "business"
    assert latest_messages[0]["user_message"] == "What is workflow automation?"
    assert latest_messages[0]["provider"] == "MockLLMProvider"
    assert "created_at" in latest_messages[0]

    assert latest_messages[1]["role"] == "business"
    assert latest_messages[1]["user_message"] == (
        "Give me one practical example."
    )


def test_get_conversation_returns_404_for_unknown_session() -> None:
    """An unknown session should return a structured not-found response."""
    request_id = "unknown-conversation-test"

    response = client.get(
        "/conversations/session-that-does-not-exist-987654",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "Conversation session not found.",
        "status_code": 404,
        "request_id": request_id,
    }
    assert response.headers["X-Request-ID"] == request_id