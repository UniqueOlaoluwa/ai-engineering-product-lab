"""API tests for persisted outbound-delivery retries."""

from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.api as api_module
from app.outbound_deliveries import (
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OutboundDeliveryStorageError,
)
from app.outbound_retry_service import (
    OutboundDeliveryRetryError,
    OutboundRetryBatchResult,
    OutboundRetryResult,
)

client = TestClient(api_module.app)


def create_retry_record() -> dict[str, object]:
    """Create one retry-pending delivery record."""
    return {
        "id": 1,
        "provider": "whatsapp",
        "inbound_message_id": "wamid.retry-api-001",
        "recipient_phone": "2348012345678",
        "message": "Your appointment is confirmed.",
        "status": DELIVERY_STATUS_RETRY_PENDING,
        "delivery_provider": None,
        "outbound_message_id": None,
        "error": "Temporary failure.",
        "attempt_count": 1,
        "created_at": "2026-08-04T01:00:00+00:00",
        "updated_at": "2026-08-04T01:01:00+00:00",
        "sent_at": None,
    }


def create_sent_retry_result() -> OutboundRetryResult:
    """Create one successful retry result."""
    return OutboundRetryResult(
        status=DELIVERY_STATUS_SENT,
        inbound_message_id="wamid.retry-api-001",
        recipient_phone="2348012345678",
        message="Your appointment is confirmed.",
        attempt_count=2,
        delivery_provider="MockWhatsAppSender",
        outbound_message_id="mock-out-retry-api-001",
        error=None,
    )


def test_list_retry_pending_deliveries(
    monkeypatch,
) -> None:
    """The API should return persisted retry records."""
    list_mock = Mock(
        return_value=[
            create_retry_record()
        ]
    )

    monkeypatch.setattr(
        api_module,
        "list_retry_pending_deliveries",
        list_mock,
    )

    response = client.get(
        "/deliveries/retry-pending?limit=10"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["limit"] == 10

    item = response.json()["deliveries"][0]

    assert item["status"] == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert item["attempt_count"] == 1

    list_mock.assert_called_once_with(
        limit=10
    )


def test_list_retry_pending_deliveries_empty(
    monkeypatch,
) -> None:
    """An empty retry queue should return a valid response."""
    monkeypatch.setattr(
        api_module,
        "list_retry_pending_deliveries",
        Mock(return_value=[]),
    )

    response = client.get(
        "/deliveries/retry-pending"
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["deliveries"] == []


def test_retry_one_delivery(
    monkeypatch,
) -> None:
    """The API should retry one stored delivery."""
    retry_mock = Mock(
        return_value=create_sent_retry_result()
    )

    monkeypatch.setattr(
        api_module,
        "retry_outbound_delivery",
        retry_mock,
    )

    response = client.post(
        "/deliveries/wamid.retry-api-001/retry"
    )

    assert response.status_code == 200
    assert response.json()["status"] == (
        DELIVERY_STATUS_SENT
    )
    assert response.json()["attempt_count"] == 2
    assert response.json()["outbound_message_id"] == (
        "mock-out-retry-api-001"
    )

    retry_mock.assert_called_once_with(
        inbound_message_id="wamid.retry-api-001"
    )


def test_retry_missing_delivery_returns_409(
    monkeypatch,
) -> None:
    """A missing or non-retryable record should return conflict."""
    monkeypatch.setattr(
        api_module,
        "retry_outbound_delivery",
        Mock(
            side_effect=OutboundDeliveryRetryError(
                "Outbound delivery was not found."
            )
        ),
    )

    response = client.post(
        "/deliveries/wamid.missing/retry"
    )

    assert response.status_code == 409
    assert response.json()["error"] == (
        "Outbound delivery was not found."
    )


def test_retry_storage_failure_returns_500(
    monkeypatch,
) -> None:
    """A retry-storage failure should be reported as server error."""
    monkeypatch.setattr(
        api_module,
        "retry_outbound_delivery",
        Mock(
            side_effect=OutboundDeliveryStorageError(
                "Unable to mark the retry as sent."
            )
        ),
    )

    response = client.post(
        "/deliveries/wamid.retry-api-001/retry"
    )

    assert response.status_code == 500
    assert response.json()["error"] == (
        "Unable to mark the retry as sent."
    )


def test_retry_pending_batch(
    monkeypatch,
) -> None:
    """The API should return one batch retry summary."""
    batch_result = OutboundRetryBatchResult(
        requested=10,
        attempted=2,
        sent=1,
        failed=1,
        results=[
            create_sent_retry_result(),
            OutboundRetryResult(
                status=DELIVERY_STATUS_RETRY_PENDING,
                inbound_message_id="wamid.retry-api-002",
                recipient_phone="2348022222222",
                message="Second reply",
                attempt_count=3,
                delivery_provider=None,
                outbound_message_id=None,
                error="Provider still unavailable.",
            ),
        ],
    )

    retry_mock = Mock(
        return_value=batch_result
    )

    monkeypatch.setattr(
        api_module,
        "retry_pending_deliveries",
        retry_mock,
    )

    response = client.post(
        "/deliveries/retry-pending?limit=10"
    )

    assert response.status_code == 200
    assert response.json()["requested"] == 10
    assert response.json()["attempted"] == 2
    assert response.json()["sent"] == 1
    assert response.json()["failed"] == 1
    assert len(response.json()["results"]) == 2

    retry_mock.assert_called_once_with(
        limit=10
    )


def test_retry_pending_limit_validation() -> None:
    """FastAPI should reject an unsafe retry limit."""
    response = client.post(
        "/deliveries/retry-pending?limit=101"
    )

    assert response.status_code == 422


def test_list_retry_storage_error_returns_400(
    monkeypatch,
) -> None:
    """Listing failures should return a client-readable error."""
    monkeypatch.setattr(
        api_module,
        "list_retry_pending_deliveries",
        Mock(
            side_effect=OutboundDeliveryStorageError(
                "Unable to list retry deliveries."
            )
        ),
    )

    response = client.get(
        "/deliveries/retry-pending"
    )

    assert response.status_code == 400
    assert response.json()["error"] == (
        "Unable to list retry deliveries."
    )