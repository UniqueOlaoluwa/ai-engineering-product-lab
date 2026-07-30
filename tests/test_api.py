"""Tests for the FastAPI application."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import app
from app.database import initialize_database

client = TestClient(app)


def create_unique_session(prefix: str) -> str:
    """Create a unique session ID for an API integration test."""
    return f"{prefix}-{uuid4()}"


def test_root_endpoint_returns_api_information() -> None:
    """The root endpoint should describe the running API."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "application": "AI Engineering Product Lab",
        "version": "0.9.0",
        "status": "running",
        "documentation": "/docs",
        "health": "/health",
    }
    assert "X-Request-ID" in response.headers


def test_health_endpoint_returns_ok() -> None:
    """The health endpoint should report a successful state."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "AI Engineering Product Lab",
        "version": "0.9.0",
    }


def test_chat_endpoint_returns_business_response() -> None:
    """A valid business request should return a stored response."""
    session_id = create_unique_session("api-business")

    response = client.post(
        "/chat",
        json={
            "message": "Help me improve customer support.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["message_id"] >= 1
    assert response_data["session_id"] == session_id
    assert response_data["role"] == "business"
    assert response_data["role_name"] == "Business Assistant"
    assert response_data["provider"] == "MockLLMProvider"
    assert "Help me improve customer support." in response_data["reply"]


def test_chat_endpoint_uses_request_defaults() -> None:
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
    assert response_data["role_name"] == (
        "Customer Support Assistant"
    )


def test_chat_endpoint_falls_back_for_unknown_role() -> None:
    """An unknown role should safely use the default role."""
    session_id = create_unique_session("fallback")

    response = client.post(
        "/chat",
        json={
            "message": "What time do you close?",
            "role": "doctor",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["role"] == "support"
    assert response_data["session_id"] == session_id


def test_chat_endpoint_rejects_empty_message() -> None:
    """An empty message should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "message": "",
            "role": "support",
            "session_id": "validation-session",
            "history_limit": 5,
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
            "history_limit": 5,
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
            "history_limit": 5,
        },
    )

    assert response.status_code == 422


def test_chat_endpoint_rejects_negative_history_limit() -> None:
    """A negative history limit should fail request validation."""
    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "role": "support",
            "session_id": create_unique_session("negative-limit"),
            "history_limit": -1,
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert "request_id" in response_data
    assert isinstance(response_data["details"], list)


def test_chat_endpoint_rejects_history_limit_above_maximum() -> None:
    """A history limit above 20 should fail validation."""
    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "role": "support",
            "session_id": create_unique_session("high-limit"),
            "history_limit": 21,
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert "request_id" in response_data
    assert isinstance(response_data["details"], list)


def test_chat_endpoint_accepts_maximum_history_limit() -> None:
    """The maximum allowed history limit should be accepted."""
    session_id = create_unique_session("maximum-limit")

    response = client.post(
        "/chat",
        json={
            "message": "Explain workflow automation.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 20,
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id


def test_get_conversation_returns_saved_messages() -> None:
    """A known session should return stored conversation history."""
    initialize_database()

    session_id = create_unique_session("conversation-history")

    first_response = client.post(
        "/chat",
        json={
            "message": "What is workflow automation?",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    second_response = client.post(
        "/chat",
        json={
            "message": "Give me one practical example.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    response = client.get(f"/conversations/{session_id}")
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["session_id"] == session_id
    assert response_data["message_count"] == 2
    assert len(response_data["messages"]) == 2


def test_default_history_limit_uses_previous_context() -> None:
    """The default history limit should enable conversation memory."""
    session_id = create_unique_session("default-memory")

    first_response = client.post(
        "/chat",
        json={
            "message": "What is workflow automation?",
            "role": "business",
            "session_id": session_id,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/chat",
        json={
            "message": "Give me an example for a clinic.",
            "role": "business",
            "session_id": session_id,
        },
    )

    reply = second_response.json()["reply"]

    assert second_response.status_code == 200
    assert "Previous conversation context:" in reply
    assert "User: What is workflow automation?" in reply
    assert "Current user message:" in reply


def test_history_limit_zero_disables_previous_context() -> None:
    """A zero history limit should disable memory for one request."""
    session_id = create_unique_session("disabled-memory")

    first_response = client.post(
        "/chat",
        json={
            "message": "Remember this earlier discussion.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/chat",
        json={
            "message": "Answer without using earlier context.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 0,
        },
    )

    reply = second_response.json()["reply"]

    assert second_response.status_code == 200
    assert "Previous conversation context:" not in reply
    assert "Remember this earlier discussion." not in reply


def test_history_limit_zero_still_saves_new_exchange() -> None:
    """Disabling prompt memory should not disable message storage."""
    session_id = create_unique_session("disabled-memory-storage")

    first_response = client.post(
        "/chat",
        json={
            "message": "First saved message.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    second_response = client.post(
        "/chat",
        json={
            "message": "Second saved message without context.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 0,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    conversation_response = client.get(
        f"/conversations/{session_id}"
    )
    conversation_data = conversation_response.json()

    assert conversation_response.status_code == 200
    assert conversation_data["message_count"] == 2


def test_new_session_does_not_include_previous_context() -> None:
    """A new session should not inherit another session's history."""
    first_session = create_unique_session("isolated-first")
    second_session = create_unique_session("isolated-second")

    first_response = client.post(
        "/chat",
        json={
            "message": "Private first-session question.",
            "role": "business",
            "session_id": first_session,
            "history_limit": 5,
        },
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/chat",
        json={
            "message": "Start a separate conversation.",
            "role": "business",
            "session_id": second_session,
            "history_limit": 5,
        },
    )

    second_reply = second_response.json()["reply"]

    assert second_response.status_code == 200
    assert "Private first-session question." not in second_reply
    assert "Previous conversation context:" not in second_reply


def test_delete_conversation_removes_all_saved_messages() -> None:
    """Deleting a conversation should remove all session messages."""
    session_id = create_unique_session("delete-conversation")

    first_response = client.post(
        "/chat",
        json={
            "message": "First message to delete.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    second_response = client.post(
        "/chat",
        json={
            "message": "Second message to delete.",
            "role": "business",
            "session_id": session_id,
            "history_limit": 5,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    delete_response = client.delete(
        f"/conversations/{session_id}"
    )
    delete_data = delete_response.json()

    assert delete_response.status_code == 200
    assert delete_data == {
        "session_id": session_id,
        "deleted_count": 2,
        "message": "Conversation deleted successfully.",
    }

    retrieval_response = client.get(
        f"/conversations/{session_id}"
    )

    assert retrieval_response.status_code == 404


def test_delete_conversation_does_not_affect_other_session() -> None:
    """Deleting one conversation should preserve another."""
    deleted_session = create_unique_session("deleted-session")
    retained_session = create_unique_session("retained-session")

    deleted_response = client.post(
        "/chat",
        json={
            "message": "Delete this conversation.",
            "role": "business",
            "session_id": deleted_session,
            "history_limit": 5,
        },
    )

    retained_response = client.post(
        "/chat",
        json={
            "message": "Keep this conversation.",
            "role": "support",
            "session_id": retained_session,
            "history_limit": 5,
        },
    )

    assert deleted_response.status_code == 200
    assert retained_response.status_code == 200

    delete_response = client.delete(
        f"/conversations/{deleted_session}"
    )

    retained_history = client.get(
        f"/conversations/{retained_session}"
    )

    assert delete_response.status_code == 200
    assert retained_history.status_code == 200
    assert retained_history.json()["message_count"] == 1


def test_delete_unknown_conversation_returns_404() -> None:
    """Deleting an unknown session should return a structured 404."""
    request_id = "delete-missing-conversation"
    session_id = create_unique_session("missing-delete")

    response = client.delete(
        f"/conversations/{session_id}",
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


def test_get_conversation_returns_404_for_unknown_session() -> None:
    """An unknown session should return a structured response."""
    request_id = "unknown-conversation-test"
    unknown_session = create_unique_session("missing")

    response = client.get(
        f"/conversations/{unknown_session}",
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