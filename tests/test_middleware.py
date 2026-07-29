"""Tests for request tracing middleware."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.api import app
from app.middleware import create_request_id

client = TestClient(app)


def assert_valid_uuid(value: str) -> None:
    """Confirm that a value contains a valid canonical UUID."""
    parsed_value = UUID(value)

    assert str(parsed_value) == value


def test_create_request_id_preserves_safe_value() -> None:
    """A safe client-provided identifier should be preserved."""
    request_id = create_request_id("client-request_123.test")

    assert request_id == "client-request_123.test"


def test_create_request_id_generates_uuid_when_missing() -> None:
    """A missing client identifier should produce a UUID."""
    request_id = create_request_id(None)

    assert_valid_uuid(request_id)


def test_create_request_id_replaces_value_with_spaces() -> None:
    """An identifier containing spaces should be replaced."""
    request_id = create_request_id("unsafe request id")

    assert_valid_uuid(request_id)


def test_create_request_id_replaces_overlong_value() -> None:
    """An identifier longer than 64 characters should be replaced."""
    request_id = create_request_id("a" * 65)

    assert_valid_uuid(request_id)


def test_response_contains_generated_request_id() -> None:
    """A request without an ID should receive a generated UUID."""
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    assert_valid_uuid(response.headers["X-Request-ID"])


def test_response_preserves_safe_client_request_id() -> None:
    """A safe client-provided request ID should be preserved."""
    request_id = "client-request-123"

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_response_replaces_unsafe_client_request_id() -> None:
    """An unsafe client-provided request ID should be replaced."""
    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "unsafe request identifier",
        },
    )

    assert response.status_code == 200

    returned_request_id = response.headers["X-Request-ID"]

    assert returned_request_id != "unsafe request identifier"
    assert_valid_uuid(returned_request_id)


def test_chat_response_contains_request_id() -> None:
    """The middleware should also apply to chatbot requests."""
    response = client.post(
        "/chat",
        json={
            "message": "Explain customer support automation.",
            "role": "business",
            "session_id": "middleware-chat-test",
        },
    )

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_not_found_response_contains_request_id() -> None:
    """Middleware should add an ID to controlled 404 responses."""
    response = client.get(
        "/conversations/middleware-session-that-does-not-exist"
    )

    assert response.status_code == 404
    assert "X-Request-ID" in response.headers