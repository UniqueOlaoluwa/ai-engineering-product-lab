"""Focused tests for the idempotent mock WhatsApp webhook."""

from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.api as api_module
from app.chat_service import ChatServiceResult
from app.exceptions import ProviderError

client = TestClient(api_module.app)


def create_whatsapp_result() -> ChatServiceResult:
    """Create a reusable synthetic WhatsApp service result."""
    return ChatServiceResult(
        message_id=8,
        session_id="whatsapp-2348012345678",
        role="clinic_admin",
        role_name="Clinic Administrative Assistant",
        reply="The clinic is open.",
        provider="MockLLMProvider",
    )


def test_first_delivery_calls_chat_service_and_saves_event(
    monkeypatch,
) -> None:
    """A new event should be processed and recorded."""
    service_mock = Mock(
        return_value=create_whatsapp_result()
    )

    event_lookup_mock = Mock(return_value=None)
    event_save_mock = Mock(return_value=1)

    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )
    monkeypatch.setattr(
        api_module,
        "get_webhook_event",
        event_lookup_mock,
    )
    monkeypatch.setattr(
        api_module,
        "save_webhook_event",
        event_save_mock,
    )

    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348012345678",
            "message": "What time does the clinic open?",
            "message_id": "wamid.mock-001",
            "role": "clinic_admin",
            "history_limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    event_lookup_mock.assert_called_once_with(
        provider="whatsapp",
        inbound_message_id="wamid.mock-001",
    )

    service_mock.assert_called_once_with(
        message="What time does the clinic open?",
        role="clinic_admin",
        session_id="whatsapp-2348012345678",
        history_limit=5,
    )

    event_save_mock.assert_called_once_with(
        provider="whatsapp",
        inbound_message_id="wamid.mock-001",
        session_id="whatsapp-2348012345678",
        stored_message_id=8,
        reply="The clinic is open.",
        response_provider="MockLLMProvider",
    )


def test_duplicate_delivery_returns_saved_result(
    monkeypatch,
) -> None:
    """A duplicate event should return the original stored result."""
    existing_event = {
        "id": 1,
        "provider": "whatsapp",
        "inbound_message_id": "wamid.duplicate",
        "session_id": "whatsapp-2348012345678",
        "stored_message_id": 8,
        "reply": "Previously generated reply.",
        "response_provider": "MockLLMProvider",
        "created_at": "2026-08-01 12:00:00",
    }

    service_mock = Mock()
    event_save_mock = Mock()

    monkeypatch.setattr(
        api_module,
        "get_webhook_event",
        Mock(return_value=existing_event),
    )
    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )
    monkeypatch.setattr(
        api_module,
        "save_webhook_event",
        event_save_mock,
    )

    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348012345678",
            "message": "Repeated message.",
            "message_id": "wamid.duplicate",
            "role": "clinic_admin",
            "history_limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "duplicate",
        "inbound_message_id": "wamid.duplicate",
        "session_id": "whatsapp-2348012345678",
        "sender_phone": "+2348012345678",
        "reply": "Previously generated reply.",
        "provider": "MockLLMProvider",
        "stored_message_id": 8,
    }

    service_mock.assert_not_called()
    event_save_mock.assert_not_called()


def test_new_delivery_returns_processed_response(
    monkeypatch,
) -> None:
    """A new event should return the generated result."""
    monkeypatch.setattr(
        api_module,
        "get_webhook_event",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        Mock(return_value=create_whatsapp_result()),
    )
    monkeypatch.setattr(
        api_module,
        "save_webhook_event",
        Mock(return_value=1),
    )

    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348012345678",
            "message": "What time does the clinic open?",
            "message_id": "wamid.new-delivery",
            "role": "clinic_admin",
            "history_limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processed",
        "inbound_message_id": "wamid.new-delivery",
        "session_id": "whatsapp-2348012345678",
        "sender_phone": "+2348012345678",
        "reply": "The clinic is open.",
        "provider": "MockLLMProvider",
        "stored_message_id": 8,
    }


def test_mock_whatsapp_webhook_uses_defaults(
    monkeypatch,
) -> None:
    """The webhook should use support and history limit five."""
    result = ChatServiceResult(
        message_id=9,
        session_id="whatsapp-2348099999999",
        role="support",
        role_name="Customer Support Assistant",
        reply="How may I help you?",
        provider="MockLLMProvider",
    )

    service_mock = Mock(return_value=result)

    monkeypatch.setattr(
        api_module,
        "get_webhook_event",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        service_mock,
    )
    monkeypatch.setattr(
        api_module,
        "save_webhook_event",
        Mock(return_value=1),
    )

    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348099999999",
            "message": "Hello",
            "message_id": "wamid.mock-002",
        },
    )

    assert response.status_code == 200

    service_mock.assert_called_once_with(
        message="Hello",
        role="support",
        session_id="whatsapp-2348099999999",
        history_limit=5,
    )


def test_mock_whatsapp_webhook_rejects_invalid_phone() -> None:
    """Invalid phone numbers should fail schema validation."""
    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+234-801-234-5678",
            "message": "Hello",
            "message_id": "wamid.invalid-phone",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Request validation failed."


def test_mock_whatsapp_webhook_rejects_empty_message() -> None:
    """An empty incoming message should fail validation."""
    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348012345678",
            "message": "",
            "message_id": "wamid.empty-message",
        },
    )

    assert response.status_code == 422


def test_mock_whatsapp_webhook_rejects_missing_message_id() -> None:
    """A provider message ID should be required."""
    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348012345678",
            "message": "Hello",
        },
    )

    assert response.status_code == 422


def test_mock_whatsapp_webhook_maps_provider_error(
    monkeypatch,
) -> None:
    """Provider failures should become structured 503 responses."""
    monkeypatch.setattr(
        api_module,
        "get_webhook_event",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        api_module,
        "process_chat_message",
        Mock(
            side_effect=ProviderError(
                "Provider temporarily unavailable."
            )
        ),
    )

    response = client.post(
        "/webhooks/whatsapp/mock",
        json={
            "sender_phone": "+2348012345678",
            "message": "Hello",
            "message_id": "wamid.provider-error",
        },
        headers={
            "X-Request-ID": "whatsapp-provider-error",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "error": (
            "AI provider error: "
            "Provider temporarily unavailable."
        ),
        "status_code": 503,
        "request_id": "whatsapp-provider-error",
    }