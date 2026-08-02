"""Focused API tests for chat-service integration."""

from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.api as api_module
from app.chat_service import ChatServiceResult
from app.exceptions import PromptTemplateError, ProviderError

client = TestClient(api_module.app)


def create_service_result() -> ChatServiceResult:
    """Create a reusable synthetic chat-service result."""
    return ChatServiceResult(
        message_id=42,
        session_id="service-api-session",
        role="business",
        role_name="Business Assistant",
        reply="Synthetic service response.",
        provider="MockLLMProvider",
    )


def test_chat_endpoint_calls_reusable_service(
    monkeypatch,
) -> None:
    """The endpoint should pass request data to the chat service."""
    service_mock = Mock(
        return_value=create_service_result()
    )

    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )

    response = client.post(
        "/chat",
        json={
            "message": "Help my business.",
            "role": "business",
            "session_id": "service-api-session",
            "history_limit": 4,
        },
    )

    assert response.status_code == 200

    service_mock.assert_called_once_with(
        message="Help my business.",
        role="business",
        session_id="service-api-session",
        history_limit=4,
    )


def test_chat_endpoint_maps_service_result_to_response(
    monkeypatch,
) -> None:
    """The endpoint should return the service result as JSON."""
    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        Mock(return_value=create_service_result()),
    )

    response = client.post(
        "/chat",
        json={
            "message": "Test message.",
            "role": "business",
            "session_id": "service-api-session",
            "history_limit": 0,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message_id": 42,
        "session_id": "service-api-session",
        "role": "business",
        "role_name": "Business Assistant",
        "reply": "Synthetic service response.",
        "provider": "MockLLMProvider",
    }


def test_chat_endpoint_returns_400_for_service_value_error(
    monkeypatch,
) -> None:
    """Service input errors should become structured HTTP 400 errors."""
    service_mock = Mock(
        side_effect=ValueError("Session ID cannot be empty.")
    )

    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )

    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "role": "support",
            "session_id": "valid-at-schema-level",
            "history_limit": 5,
        },
        headers={
            "X-Request-ID": "service-value-error",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Session ID cannot be empty.",
        "status_code": 400,
        "request_id": "service-value-error",
    }


def test_chat_endpoint_returns_500_for_prompt_error(
    monkeypatch,
) -> None:
    """Prompt configuration errors should become HTTP 500 errors."""
    service_mock = Mock(
        side_effect=PromptTemplateError(
            "Missing business template."
        )
    )

    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )

    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "role": "business",
            "session_id": "prompt-error-session",
            "history_limit": 5,
        },
    )

    response_data = response.json()

    assert response.status_code == 500
    assert response_data["error"] == (
        "Prompt configuration error: Missing business template."
    )
    assert response_data["status_code"] == 500


def test_chat_endpoint_returns_503_for_provider_error(
    monkeypatch,
) -> None:
    """Provider failures should become HTTP 503 responses."""
    service_mock = Mock(
        side_effect=ProviderError(
            "Provider temporarily unavailable."
        )
    )

    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )

    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "role": "support",
            "session_id": "provider-error-session",
            "history_limit": 5,
        },
    )

    response_data = response.json()

    assert response.status_code == 503
    assert response_data["error"] == (
        "AI provider error: Provider temporarily unavailable."
    )
    assert response_data["status_code"] == 503


def test_schema_validation_happens_before_chat_service(
    monkeypatch,
) -> None:
    """Invalid request bodies should not call the service."""
    service_mock = Mock()

    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )

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
    service_mock.assert_not_called()