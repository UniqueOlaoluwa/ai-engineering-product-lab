"""API tests for signature-authenticated WhatsApp webhooks."""

import json
from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.api as api_module
from app.chat_service import ChatServiceResult
from app.whatsapp_signature import (
    WhatsAppSignatureConfigurationError,
    generate_whatsapp_signature,
)

client = TestClient(api_module.app)

TEST_SECRET = "local-meta-secret"


def create_payload() -> dict[str, object]:
    """Create one valid WhatsApp-style webhook payload."""
    return {
        "sender_phone": "+2348012345678",
        "message": "What time does the clinic open?",
        "message_id": "wamid.signed-001",
        "role": "clinic_admin",
        "history_limit": 5,
    }


def encode_payload(
    payload: dict[str, object],
) -> bytes:
    """Encode payload deterministically for signature tests."""
    return json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")


def create_service_result() -> ChatServiceResult:
    """Create a synthetic chatbot result."""
    return ChatServiceResult(
        message_id=12,
        session_id="whatsapp-2348012345678",
        role="clinic_admin",
        role_name="Clinic Administrative Assistant",
        reply="The clinic is open.",
        provider="MockLLMProvider",
    )


def test_valid_signature_processes_payload(
    monkeypatch,
) -> None:
    """A correctly signed payload should be processed."""
    payload_bytes = encode_payload(create_payload())

    signature = generate_whatsapp_signature(
        payload=payload_bytes,
        app_secret=TEST_SECRET,
    )

    service_mock = Mock(
        return_value=create_service_result()
    )

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )
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
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["stored_message_id"] == 12

    service_mock.assert_called_once_with(
        message="What time does the clinic open?",
        role="clinic_admin",
        session_id="whatsapp-2348012345678",
        history_limit=5,
    )


def test_valid_signature_returns_duplicate_result(
    monkeypatch,
) -> None:
    """A signed duplicate should return its saved response."""
    payload = create_payload()
    payload["message_id"] = "wamid.signed-duplicate"

    payload_bytes = encode_payload(payload)

    signature = generate_whatsapp_signature(
        payload=payload_bytes,
        app_secret=TEST_SECRET,
    )

    existing_event = {
        "id": 1,
        "provider": "whatsapp",
        "inbound_message_id": "wamid.signed-duplicate",
        "session_id": "whatsapp-2348012345678",
        "stored_message_id": 12,
        "reply": "Saved duplicate reply.",
        "response_provider": "MockLLMProvider",
        "created_at": "2026-08-03 20:00:00",
    }

    service_mock = Mock()

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )
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

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "duplicate"
    assert response.json()["reply"] == "Saved duplicate reply."

    service_mock.assert_not_called()


def test_missing_signature_returns_403(
    monkeypatch,
) -> None:
    """A request without a signature should be rejected."""
    payload_bytes = encode_payload(create_payload())

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": "missing-signature",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": "Webhook signature is required.",
        "status_code": 403,
        "request_id": "missing-signature",
    }


def test_invalid_signature_returns_403(
    monkeypatch,
) -> None:
    """An incorrectly signed request should be rejected."""
    payload_bytes = encode_payload(create_payload())

    invalid_signature = (
        "sha256="
        + ("a" * 64)
    )

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": invalid_signature,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Invalid webhook signature."
    )


def test_modified_payload_returns_403(
    monkeypatch,
) -> None:
    """Changing bytes after signing should invalidate the request."""
    original_payload = encode_payload(
        create_payload()
    )

    signature = generate_whatsapp_signature(
        payload=original_payload,
        app_secret=TEST_SECRET,
    )

    modified_payload = create_payload()
    modified_payload["message"] = "Modified message."

    modified_bytes = encode_payload(
        modified_payload
    )

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=modified_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Invalid webhook signature."
    )


def test_valid_signature_with_invalid_json_returns_400(
    monkeypatch,
) -> None:
    """Signed malformed JSON should return a client error."""
    payload_bytes = b'{"message":'

    signature = generate_whatsapp_signature(
        payload=payload_bytes,
        app_secret=TEST_SECRET,
    )

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == (
        "Webhook payload must be valid JSON."
    )


def test_valid_signature_with_invalid_payload_returns_422(
    monkeypatch,
) -> None:
    """Signed JSON that violates the schema should be rejected."""
    payload_bytes = encode_payload(
        {
            "message": "Hello",
            "message_id": "wamid.missing-phone",
        }
    )

    signature = generate_whatsapp_signature(
        payload=payload_bytes,
        app_secret=TEST_SECRET,
    )

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == (
        "Webhook payload validation failed."
    )


def test_missing_app_secret_configuration_returns_500(
    monkeypatch,
) -> None:
    """Missing private application configuration is a server error."""
    payload_bytes = encode_payload(create_payload())

    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(
            side_effect=WhatsAppSignatureConfigurationError(
                "META_APP_SECRET is not configured."
            )
        ),
    )

    response = client.post(
        "/webhooks/whatsapp/signed",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": (
                "sha256="
                + ("a" * 64)
            ),
            "X-Request-ID": "missing-meta-secret",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "META_APP_SECRET is not configured.",
        "status_code": 500,
        "request_id": "missing-meta-secret",
    }