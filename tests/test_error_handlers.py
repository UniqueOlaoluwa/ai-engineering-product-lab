"""Tests for centralized API error handling."""

from uuid import UUID

from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def assert_valid_uuid(value: str) -> None:
    """Confirm that a value contains a canonical UUID."""
    parsed_value = UUID(value)

    assert str(parsed_value) == value


def test_http_error_contains_client_request_id() -> None:
    """A controlled error should preserve a safe client request ID."""
    request_id = "error-handler-test-001"

    response = client.get(
        "/conversations/unknown-error-session",
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


def test_http_error_contains_generated_request_id() -> None:
    """An error without a client ID should contain a generated UUID."""
    response = client.get(
        "/conversations/another-unknown-session"
    )

    response_data = response.json()
    request_id = response_data["request_id"]

    assert response.status_code == 404
    assert response_data["error"] == (
        "Conversation session not found."
    )
    assert response_data["status_code"] == 404
    assert response.headers["X-Request-ID"] == request_id

    assert_valid_uuid(request_id)

def test_unsafe_request_id_is_replaced_in_error_response() -> None:
    """An unsafe request ID should not appear in an error response."""
    unsafe_request_id = "unsafe request id"

    response = client.get(
        "/conversations/unsafe-request-id-session",
        headers={
            "X-Request-ID": unsafe_request_id,
        },
    )

    response_data = response.json()
    returned_request_id = response_data["request_id"]

    assert response.status_code == 404
    assert returned_request_id != unsafe_request_id
    assert response.headers["X-Request-ID"] == returned_request_id

    assert_valid_uuid(returned_request_id)

def test_validation_error_uses_standard_response() -> None:
    """An invalid request should return a structured validation error."""
    request_id = "validation-error-test"

    response = client.post(
        "/chat",
        json={
            "message": "",
            "role": "business",
            "session_id": "validation-session",
        },
        headers={
            "X-Request-ID": request_id,
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert response_data["request_id"] == request_id
    assert isinstance(response_data["details"], list)
    assert response.headers["X-Request-ID"] == request_id


def test_missing_message_returns_structured_validation_error() -> None:
    """A missing required field should use the standard error format."""
    response = client.post(
        "/chat",
        json={
            "role": "support",
            "session_id": "missing-message-session",
        },
    )

    response_data = response.json()

    assert response.status_code == 422
    assert response_data["error"] == "Request validation failed."
    assert response_data["status_code"] == 422
    assert "request_id" in response_data
    assert isinstance(response_data["details"], list)