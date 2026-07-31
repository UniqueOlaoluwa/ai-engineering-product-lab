"""Tests for the FastAPI application."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import app
from app.database import initialize_database

client = TestClient(app)


def create_unique_session(prefix: str) -> str:
    """Create a unique session ID for an API integration test."""
    return f"{prefix}-{uuid4()}"


def create_chat_message(
    session_id: str,
    message: str,
    role: str = "business",
    history_limit: int = 5,
):
    """Create one stored chat exchange through the API."""
    return client.post(
        "/chat",
        json={
            "message": message,
            "role": role,
            "session_id": session_id,
            "history_limit": history_limit,
        },
    )


def test_root_endpoint_returns_api_information() -> None:
    """The root endpoint should describe the running API."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "application": "AI Engineering Product Lab",
        "version": "0.12.0",
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
        "version": "0.12.0",
    }


def test_chat_endpoint_returns_business_response() -> None:
    """A valid business request should return a stored response."""
    session_id = create_unique_session("api-business")

    response = create_chat_message(
        session_id=session_id,
        message="Help me improve customer support.",
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

    response = create_chat_message(
        session_id=session_id,
        message="What time do you close?",
        role="doctor",
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

    response = create_chat_message(
        session_id=session_id,
        message="Explain workflow automation.",
        history_limit=20,
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id


def test_get_conversation_returns_saved_messages() -> None:
    """A known session should return stored conversation history."""
    initialize_database()

    session_id = create_unique_session("conversation-history")

    first_response = create_chat_message(
        session_id=session_id,
        message="What is workflow automation?",
    )

    second_response = create_chat_message(
        session_id=session_id,
        message="Give me one practical example.",
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

    first_response = create_chat_message(
        session_id=session_id,
        message="What is workflow automation?",
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

    first_response = create_chat_message(
        session_id=session_id,
        message="Remember this earlier discussion.",
    )

    assert first_response.status_code == 200

    second_response = create_chat_message(
        session_id=session_id,
        message="Answer without using earlier context.",
        history_limit=0,
    )

    reply = second_response.json()["reply"]

    assert second_response.status_code == 200
    assert "Previous conversation context:" not in reply
    assert "Remember this earlier discussion." not in reply


def test_history_limit_zero_still_saves_new_exchange() -> None:
    """Disabling prompt memory should not disable message storage."""
    session_id = create_unique_session("disabled-memory-storage")

    first_response = create_chat_message(
        session_id=session_id,
        message="First saved message.",
    )

    second_response = create_chat_message(
        session_id=session_id,
        message="Second saved message without context.",
        history_limit=0,
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

    first_response = create_chat_message(
        session_id=first_session,
        message="Private first-session question.",
    )

    assert first_response.status_code == 200

    second_response = create_chat_message(
        session_id=second_session,
        message="Start a separate conversation.",
    )

    second_reply = second_response.json()["reply"]

    assert second_response.status_code == 200
    assert "Private first-session question." not in second_reply
    assert "Previous conversation context:" not in second_reply


def test_list_conversations_returns_session_summaries() -> None:
    """The listing endpoint should return grouped conversation data."""
    first_session = create_unique_session("list-first")
    second_session = create_unique_session("list-second")

    first_response = create_chat_message(
        session_id=first_session,
        message="First session, first message.",
    )

    second_response = create_chat_message(
        session_id=first_session,
        message="First session, second message.",
    )

    third_response = create_chat_message(
        session_id=second_session,
        message="Second session message.",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 200

    response = client.get(
        "/conversations",
        params={
            "limit": 100,
            "offset": 0,
        },
    )

    response_data = response.json()
    summaries = {
        item["session_id"]: item
        for item in response_data["conversations"]
    }

    assert response.status_code == 200
    assert response_data["total"] >= 2
    assert response_data["limit"] == 100
    assert response_data["offset"] == 0
    assert first_session in summaries
    assert second_session in summaries
    assert summaries[first_session]["message_count"] == 2
    assert summaries[second_session]["message_count"] == 1
    assert "first_created_at" in summaries[first_session]
    assert "last_created_at" in summaries[first_session]


def test_list_conversations_respects_limit_and_offset() -> None:
    """The listing endpoint should apply pagination parameters."""
    for number in range(3):
        session_id = create_unique_session(f"pagination-{number}")

        response = create_chat_message(
            session_id=session_id,
            message=f"Pagination message {number}",
        )

        assert response.status_code == 200

    first_page = client.get(
        "/conversations",
        params={
            "limit": 2,
            "offset": 0,
        },
    )

    second_page = client.get(
        "/conversations",
        params={
            "limit": 2,
            "offset": 2,
        },
    )

    first_data = first_page.json()
    second_data = second_page.json()

    first_sessions = {
        item["session_id"]
        for item in first_data["conversations"]
    }

    second_sessions = {
        item["session_id"]
        for item in second_data["conversations"]
    }

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_data["limit"] == 2
    assert first_data["offset"] == 0
    assert second_data["limit"] == 2
    assert second_data["offset"] == 2
    assert len(first_data["conversations"]) <= 2
    assert len(second_data["conversations"]) <= 2
    assert first_sessions.isdisjoint(second_sessions)


def test_list_conversations_uses_default_pagination() -> None:
    """Omitted query parameters should use the configured defaults."""
    response = client.get("/conversations")
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["limit"] == 20
    assert response_data["offset"] == 0
    assert isinstance(response_data["total"], int)
    assert isinstance(response_data["conversations"], list)


def test_search_filters_conversations_case_insensitively() -> None:
    """Search should match session IDs regardless of case."""
    search_token = uuid4().hex[:8]

    first_session = f"clinic-{search_token}-one"
    second_session = f"CLINIC-{search_token}-two"
    unrelated_session = f"retail-{search_token}-three"

    first_response = create_chat_message(
        session_id=first_session,
        message="First clinic message.",
    )

    second_response = create_chat_message(
        session_id=second_session,
        message="Second clinic message.",
    )

    unrelated_response = create_chat_message(
        session_id=unrelated_session,
        message="Retail message.",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert unrelated_response.status_code == 200

    response = client.get(
        "/conversations",
        params={
            "search": f"clinic-{search_token}",
            "limit": 20,
            "offset": 0,
        },
    )

    response_data = response.json()

    session_ids = {
        item["session_id"]
        for item in response_data["conversations"]
    }

    assert response.status_code == 200
    assert response_data["total"] == 2
    assert first_session in session_ids
    assert second_session in session_ids
    assert unrelated_session not in session_ids


def test_search_supports_partial_session_matches() -> None:
    """Search should match text within a session identifier."""
    search_token = uuid4().hex[:8]

    matching_session = (
        f"customer-clinic-{search_token}-support"
    )
    unrelated_session = (
        f"customer-retail-{search_token}-support"
    )

    matching_response = create_chat_message(
        session_id=matching_session,
        message="Clinic support message.",
    )

    unrelated_response = create_chat_message(
        session_id=unrelated_session,
        message="Retail support message.",
    )

    assert matching_response.status_code == 200
    assert unrelated_response.status_code == 200

    response = client.get(
        "/conversations",
        params={
            "search": f"clinic-{search_token}",
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["total"] == 1
    assert len(response_data["conversations"]) == 1
    assert (
        response_data["conversations"][0]["session_id"]
        == matching_session
    )


def test_search_combines_with_pagination() -> None:
    """Filtered conversations should support limit and offset."""
    search_token = uuid4().hex[:8]
    matching_sessions = []

    for number in range(3):
        session_id = f"clinic-{search_token}-{number}"
        matching_sessions.append(session_id)

        response = create_chat_message(
            session_id=session_id,
            message=f"Clinic pagination message {number}.",
        )

        assert response.status_code == 200

    unrelated_response = create_chat_message(
        session_id=f"retail-{search_token}",
        message="Retail pagination message.",
    )

    assert unrelated_response.status_code == 200

    first_page = client.get(
        "/conversations",
        params={
            "search": f"clinic-{search_token}",
            "limit": 2,
            "offset": 0,
        },
    )

    second_page = client.get(
        "/conversations",
        params={
            "search": f"clinic-{search_token}",
            "limit": 2,
            "offset": 2,
        },
    )

    first_data = first_page.json()
    second_data = second_page.json()

    first_ids = {
        item["session_id"]
        for item in first_data["conversations"]
    }

    second_ids = {
        item["session_id"]
        for item in second_data["conversations"]
    }

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert first_data["total"] == 3
    assert second_data["total"] == 3
    assert len(first_data["conversations"]) == 2
    assert len(second_data["conversations"]) == 1
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == set(matching_sessions)


def test_search_returns_empty_result_for_no_matches() -> None:
    """A valid unmatched search should return an empty page."""
    search_token = uuid4().hex

    response = client.get(
        "/conversations",
        params={
            "search": f"missing-{search_token}",
            "limit": 20,
            "offset": 0,
        },
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data == {
        "total": 0,
        "limit": 20,
        "offset": 0,
        "conversations": [],
    }


def test_search_rejects_blank_value() -> None:
    """A whitespace-only search should return a validation error."""
    response = client.get(
        "/conversations",
        params={
            "search": "   ",
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert isinstance(response_data["details"], list)


def test_search_rejects_value_above_maximum_length() -> None:
    """A search longer than 100 characters should fail validation."""
    response = client.get(
        "/conversations",
        params={
            "search": "a" * 101,
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert isinstance(response_data["details"], list)


def test_list_conversations_rejects_zero_limit() -> None:
    """A zero page limit should return a validation error."""
    response = client.get(
        "/conversations",
        params={
            "limit": 0,
            "offset": 0,
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert isinstance(response_data["details"], list)


def test_list_conversations_rejects_limit_above_maximum() -> None:
    """A limit above 100 should return a validation error."""
    response = client.get(
        "/conversations",
        params={
            "limit": 101,
            "offset": 0,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Request validation failed."


def test_list_conversations_rejects_negative_offset() -> None:
    """A negative offset should return a validation error."""
    response = client.get(
        "/conversations",
        params={
            "limit": 20,
            "offset": -1,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Request validation failed."


def test_delete_conversation_removes_all_saved_messages() -> None:
    """Deleting a conversation should remove all session messages."""
    session_id = create_unique_session("delete-conversation")

    first_response = create_chat_message(
        session_id=session_id,
        message="First message to delete.",
    )

    second_response = create_chat_message(
        session_id=session_id,
        message="Second message to delete.",
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

    deleted_response = create_chat_message(
        session_id=deleted_session,
        message="Delete this conversation.",
    )

    retained_response = create_chat_message(
        session_id=retained_session,
        message="Keep this conversation.",
        role="support",
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
