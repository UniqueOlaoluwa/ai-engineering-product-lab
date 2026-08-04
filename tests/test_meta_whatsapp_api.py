"""API tests for Meta WhatsApp processing and persisted delivery."""

import json
from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.api as api_module
from app.exceptions import ProviderError
from app.outbound_deliveries import (
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OutboundDeliveryStorageError,
)
from app.outbound_delivery_service import (
    OutboundDeliveryAttemptResult,
)
from app.schemas import WhatsAppWebhookResponse
from app.whatsapp_signature import (
    WhatsAppSignatureConfigurationError,
    generate_whatsapp_signature,
)

client = TestClient(api_module.app)

TEST_SECRET = "local-meta-secret"


def create_text_message(
    sender_phone: str,
    message_id: str,
    body: str,
) -> dict[str, object]:
    """Create one Meta text-message item."""
    return {
        "from": sender_phone,
        "id": message_id,
        "timestamp": "1785798000",
        "type": "text",
        "text": {
            "body": body,
        },
    }


def create_meta_payload() -> dict[str, object]:
    """Create a Meta payload containing one text message."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-one",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                create_text_message(
                                    sender_phone="2348012345678",
                                    message_id="wamid.meta-api-001",
                                    body=(
                                        "What time does the clinic open?"
                                    ),
                                )
                            ],
                        },
                    }
                ],
            }
        ],
    }


def encode_payload(
    payload: object,
) -> bytes:
    """Encode JSON deterministically for signing."""
    return json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_payload(
    payload_bytes: bytes,
) -> str:
    """Sign exact payload bytes."""
    return generate_whatsapp_signature(
        payload=payload_bytes,
        app_secret=TEST_SECRET,
    )


def create_webhook_result(
    message_id: str,
    sender_phone: str,
    status_value: str = "processed",
    stored_message_id: int = 1,
) -> WhatsAppWebhookResponse:
    """Create a synthetic message-processing result."""
    return WhatsAppWebhookResponse(
        status=status_value,
        inbound_message_id=message_id,
        session_id=f"whatsapp-{sender_phone}",
        sender_phone=sender_phone,
        reply=f"Reply for {message_id}",
        provider="MockLLMProvider",
        stored_message_id=stored_message_id,
    )


def create_sent_delivery_result(
    message_id: str,
    sender_phone: str,
    delivery_record_id: int = 1,
    attempt_count: int = 1,
) -> OutboundDeliveryAttemptResult:
    """Create a successful persisted delivery result."""
    return OutboundDeliveryAttemptResult(
        status=DELIVERY_STATUS_SENT,
        inbound_message_id=message_id,
        recipient_phone=sender_phone,
        message=f"Reply for {message_id}",
        delivery_record_id=delivery_record_id,
        attempt_count=attempt_count,
        delivery_provider="MockWhatsAppSender",
        outbound_message_id=f"mock-out-{message_id}",
        error=None,
    )


def create_retry_pending_delivery_result(
    message_id: str,
    sender_phone: str,
    delivery_record_id: int = 1,
    attempt_count: int = 1,
) -> OutboundDeliveryAttemptResult:
    """Create a failed persisted delivery result."""
    return OutboundDeliveryAttemptResult(
        status=DELIVERY_STATUS_RETRY_PENDING,
        inbound_message_id=message_id,
        recipient_phone=sender_phone,
        message=f"Reply for {message_id}",
        delivery_record_id=delivery_record_id,
        attempt_count=attempt_count,
        delivery_provider=None,
        outbound_message_id=None,
        error="Temporary delivery failure.",
    )


def configure_secret(
    monkeypatch,
) -> None:
    """Configure the synthetic Meta secret."""
    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(return_value=TEST_SECRET),
    )


def post_payload(
    payload: object,
):
    """Send one correctly signed Meta payload."""
    payload_bytes = encode_payload(payload)

    return client.post(
        "/webhooks/whatsapp/meta",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign_payload(
                payload_bytes
            ),
        },
    )


def test_processed_message_is_persisted_and_delivered(
    monkeypatch,
) -> None:
    """A newly processed reply should be stored and delivered."""
    configure_secret(monkeypatch)

    process_mock = Mock(
        return_value=create_webhook_result(
            message_id="wamid.meta-api-001",
            sender_phone="2348012345678",
        )
    )

    delivery_mock = Mock(
        return_value=create_sent_delivery_result(
            message_id="wamid.meta-api-001",
            sender_phone="2348012345678",
            delivery_record_id=7,
        )
    )

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(
        create_meta_payload()
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["received"] == 1
    assert response_data["processed"] == 1
    assert response_data["duplicates"] == 0
    assert response_data["failed"] == 0
    assert response_data["deliveries_sent"] == 1
    assert response_data["deliveries_failed"] == 0
    assert response_data["deliveries_skipped"] == 0

    item = response_data["results"][0]

    assert item["status"] == "processed"
    assert item["delivery_status"] == (
        DELIVERY_STATUS_SENT
    )
    assert item["delivery_provider"] == (
        "MockWhatsAppSender"
    )
    assert item["outbound_message_id"] == (
        "mock-out-wamid.meta-api-001"
    )
    assert item["delivery_error"] is None
    assert item["delivery_attempt_count"] == 1

    delivery_mock.assert_called_once_with(
        inbound_message_id="wamid.meta-api-001",
        recipient_phone="2348012345678",
        message="Reply for wamid.meta-api-001",
    )


def test_duplicate_message_skips_persisted_delivery(
    monkeypatch,
) -> None:
    """A duplicate inbound message should not send again."""
    configure_secret(monkeypatch)

    process_mock = Mock(
        return_value=create_webhook_result(
            message_id="wamid.meta-api-001",
            sender_phone="2348012345678",
            status_value="duplicate",
        )
    )

    delivery_mock = Mock()

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(
        create_meta_payload()
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["processed"] == 0
    assert response_data["duplicates"] == 1
    assert response_data["deliveries_sent"] == 0
    assert response_data["deliveries_failed"] == 0
    assert response_data["deliveries_skipped"] == 1

    item = response_data["results"][0]

    assert item["status"] == "duplicate"
    assert item["delivery_status"] == "skipped"
    assert item["delivery_attempt_count"] is None

    delivery_mock.assert_not_called()


def test_failed_delivery_is_saved_for_retry(
    monkeypatch,
) -> None:
    """A failed delivery should be reported as retry-pending."""
    configure_secret(monkeypatch)

    process_mock = Mock(
        return_value=create_webhook_result(
            message_id="wamid.meta-api-001",
            sender_phone="2348012345678",
        )
    )

    delivery_mock = Mock(
        return_value=create_retry_pending_delivery_result(
            message_id="wamid.meta-api-001",
            sender_phone="2348012345678",
            delivery_record_id=8,
        )
    )

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(
        create_meta_payload()
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["processed"] == 1
    assert response_data["failed"] == 0
    assert response_data["deliveries_sent"] == 0
    assert response_data["deliveries_failed"] == 1
    assert response_data["deliveries_skipped"] == 0

    item = response_data["results"][0]

    assert item["status"] == "processed"
    assert item["delivery_status"] == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert item["delivery_error"] == (
        "Temporary delivery failure."
    )
    assert item["delivery_attempt_count"] == 1


def test_multiple_messages_are_persisted_and_delivered(
    monkeypatch,
) -> None:
    """Each supported message should use persisted delivery."""
    configure_secret(monkeypatch)

    payload = create_meta_payload()

    value = payload["entry"][0]["changes"][0]["value"]

    value["messages"].append(
        create_text_message(
            sender_phone="2348022222222",
            message_id="wamid.meta-api-002",
            body="Do you open on weekends?",
        )
    )

    process_mock = Mock(
        side_effect=[
            create_webhook_result(
                message_id="wamid.meta-api-001",
                sender_phone="2348012345678",
                stored_message_id=1,
            ),
            create_webhook_result(
                message_id="wamid.meta-api-002",
                sender_phone="2348022222222",
                stored_message_id=2,
            ),
        ]
    )

    delivery_mock = Mock(
        side_effect=[
            create_sent_delivery_result(
                message_id="wamid.meta-api-001",
                sender_phone="2348012345678",
                delivery_record_id=10,
            ),
            create_sent_delivery_result(
                message_id="wamid.meta-api-002",
                sender_phone="2348022222222",
                delivery_record_id=11,
            ),
        ]
    )

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(payload)
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["received"] == 2
    assert response_data["processed"] == 2
    assert response_data["deliveries_sent"] == 2
    assert response_data["deliveries_failed"] == 0
    assert response_data["deliveries_skipped"] == 0

    assert process_mock.call_count == 2
    assert delivery_mock.call_count == 2


def test_mixed_processed_and_duplicate_counts(
    monkeypatch,
) -> None:
    """A mixed batch should deliver only the new reply."""
    configure_secret(monkeypatch)

    payload = create_meta_payload()

    value = payload["entry"][0]["changes"][0]["value"]

    value["messages"].append(
        create_text_message(
            sender_phone="2348022222222",
            message_id="wamid.meta-api-002",
            body="Second question",
        )
    )

    process_mock = Mock(
        side_effect=[
            create_webhook_result(
                message_id="wamid.meta-api-001",
                sender_phone="2348012345678",
                status_value="duplicate",
            ),
            create_webhook_result(
                message_id="wamid.meta-api-002",
                sender_phone="2348022222222",
            ),
        ]
    )

    delivery_mock = Mock(
        return_value=create_sent_delivery_result(
            message_id="wamid.meta-api-002",
            sender_phone="2348022222222",
        )
    )

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(payload)
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["processed"] == 1
    assert response_data["duplicates"] == 1
    assert response_data["deliveries_sent"] == 1
    assert response_data["deliveries_skipped"] == 1

    delivery_mock.assert_called_once()


def test_processing_failure_skips_delivery(
    monkeypatch,
) -> None:
    """A processing failure should not create a delivery record."""
    configure_secret(monkeypatch)

    process_mock = Mock(
        side_effect=ProviderError(
            "Provider temporarily unavailable."
        )
    )

    delivery_mock = Mock()

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(
        create_meta_payload()
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["processed"] == 0
    assert response_data["failed"] == 1
    assert response_data["deliveries_sent"] == 0
    assert response_data["deliveries_failed"] == 0
    assert response_data["deliveries_skipped"] == 1

    item = response_data["results"][0]

    assert item["status"] == "failed"
    assert item["delivery_status"] == "skipped"
    assert item["error"] == (
        "Provider temporarily unavailable."
    )

    delivery_mock.assert_not_called()


def test_delivery_storage_failure_is_reported(
    monkeypatch,
) -> None:
    """A delivery-storage failure should not crash the batch."""
    configure_secret(monkeypatch)

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        Mock(
            return_value=create_webhook_result(
                message_id="wamid.meta-api-001",
                sender_phone="2348012345678",
            )
        ),
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        Mock(
            side_effect=OutboundDeliveryStorageError(
                "Unable to create outbound delivery."
            )
        ),
    )

    response = post_payload(
        create_meta_payload()
    )

    response_data = response.json()

    assert response.status_code == 200
    assert response_data["failed"] == 1
    assert response_data["deliveries_skipped"] == 1

    item = response_data["results"][0]

    assert item["status"] == "failed"
    assert item["error"] == (
        "Unable to create outbound delivery."
    )
    assert item["delivery_status"] == "skipped"


def test_unsupported_message_is_counted(
    monkeypatch,
) -> None:
    """Unsupported items should not block supported delivery."""
    configure_secret(monkeypatch)

    payload = create_meta_payload()

    value = payload["entry"][0]["changes"][0]["value"]

    value["messages"].append(
        {
            "from": "2348033333333",
            "id": "wamid.image-001",
            "timestamp": "1785798001",
            "type": "image",
            "image": {
                "id": "media-image-001",
            },
        }
    )

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        Mock(
            return_value=create_webhook_result(
                message_id="wamid.meta-api-001",
                sender_phone="2348012345678",
            )
        ),
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        Mock(
            return_value=create_sent_delivery_result(
                message_id="wamid.meta-api-001",
                sender_phone="2348012345678",
            )
        ),
    )

    response = post_payload(payload)
    response_data = response.json()

    assert response.status_code == 200
    assert response_data["received"] == 1
    assert response_data["unsupported"] == 1
    assert response_data["processed"] == 1
    assert response_data["deliveries_sent"] == 1


def test_status_only_event_is_ignored(
    monkeypatch,
) -> None:
    """A delivery-status event should be acknowledged safely."""
    configure_secret(monkeypatch)

    payload = create_meta_payload()

    value = payload["entry"][0]["changes"][0]["value"]
    value.pop("messages")

    value["statuses"] = [
        {
            "id": "wamid.status-001",
            "status": "delivered",
        }
    ]

    process_mock = Mock()
    delivery_mock = Mock()

    monkeypatch.setattr(
        api_module,
        "process_whatsapp_request",
        process_mock,
    )

    monkeypatch.setattr(
        api_module,
        "persist_and_deliver_reply",
        delivery_mock,
    )

    response = post_payload(payload)

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "received": 0,
        "processed": 0,
        "duplicates": 0,
        "ignored": 1,
        "unsupported": 0,
        "failed": 0,
        "deliveries_sent": 0,
        "deliveries_failed": 0,
        "deliveries_skipped": 0,
        "results": [],
    }

    process_mock.assert_not_called()
    delivery_mock.assert_not_called()


def test_invalid_signature_returns_403(
    monkeypatch,
) -> None:
    """An invalid signature should reject the full batch."""
    configure_secret(monkeypatch)

    payload_bytes = encode_payload(
        create_meta_payload()
    )

    response = client.post(
        "/webhooks/whatsapp/meta",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": (
                "sha256="
                + ("a" * 64)
            ),
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Invalid webhook signature."
    )


def test_signed_invalid_json_returns_400(
    monkeypatch,
) -> None:
    """Authenticated malformed JSON should return HTTP 400."""
    configure_secret(monkeypatch)

    payload_bytes = b'{"object":'

    response = client.post(
        "/webhooks/whatsapp/meta",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign_payload(
                payload_bytes
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == (
        "Webhook payload must be valid JSON."
    )


def test_non_object_json_returns_422(
    monkeypatch,
) -> None:
    """A signed JSON list should be rejected."""
    configure_secret(monkeypatch)

    response = post_payload(
        ["invalid"]
    )

    assert response.status_code == 422
    assert response.json()["error"] == (
        "Meta webhook payload must be a JSON object."
    )


def test_missing_meta_secret_returns_500(
    monkeypatch,
) -> None:
    """Missing server configuration should return HTTP 500."""
    monkeypatch.setattr(
        api_module,
        "get_configured_meta_app_secret",
        Mock(
            side_effect=WhatsAppSignatureConfigurationError(
                "META_APP_SECRET is not configured."
            )
        ),
    )

    payload_bytes = encode_payload(
        create_meta_payload()
    )

    response = client.post(
        "/webhooks/whatsapp/meta",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": (
                "sha256="
                + ("a" * 64)
            ),
            "X-Request-ID": "meta-secret-missing",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "META_APP_SECRET is not configured.",
        "status_code": 500,
        "request_id": "meta-secret-missing",
    }