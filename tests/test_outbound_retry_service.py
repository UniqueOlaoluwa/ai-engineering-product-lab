"""Tests for retrying persisted outbound deliveries."""

from unittest.mock import Mock

import pytest

import app.outbound_retry_service as retry_module
from app.outbound_deliveries import (
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OUTBOUND_PROVIDER,
    OutboundDeliveryStorageError,
)
from app.outbound_retry_service import (
    OutboundDeliveryRetryError,
    retry_outbound_delivery,
    retry_pending_deliveries,
)
from app.whatsapp_delivery_service import (
    WhatsAppReplyDelivery,
)


def create_retry_record(
    inbound_message_id: str = "wamid.retry-001",
    attempt_count: int = 1,
) -> dict[str, object]:
    """Create one synthetic retry-pending storage record."""
    return {
        "id": 1,
        "provider": OUTBOUND_PROVIDER,
        "inbound_message_id": inbound_message_id,
        "recipient_phone": "2348012345678",
        "message": "Your appointment is confirmed.",
        "status": DELIVERY_STATUS_RETRY_PENDING,
        "delivery_provider": None,
        "outbound_message_id": None,
        "error": "Temporary delivery failure.",
        "attempt_count": attempt_count,
    }


def create_sent_delivery() -> WhatsAppReplyDelivery:
    """Create a successful retry-delivery result."""
    return WhatsAppReplyDelivery(
        status="sent",
        recipient_phone="2348012345678",
        provider="MockWhatsAppSender",
        outbound_message_id="mock-wamid-out-retry-001",
        message="Your appointment is confirmed.",
        error=None,
    )


def create_failed_delivery() -> WhatsAppReplyDelivery:
    """Create a failed retry-delivery result."""
    return WhatsAppReplyDelivery(
        status="failed",
        recipient_phone="2348012345678",
        provider=None,
        outbound_message_id=None,
        message="Your appointment is confirmed.",
        error="Provider still unavailable.",
    )


def test_successful_retry_is_marked_sent(
    monkeypatch,
) -> None:
    """A successful retry should update storage and attempts."""
    record = create_retry_record(
        attempt_count=1
    )

    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=record),
    )

    delivery_mock = Mock(
        return_value=create_sent_delivery()
    )

    monkeypatch.setattr(
        retry_module,
        "deliver_whatsapp_reply",
        delivery_mock,
    )

    mark_sent_mock = Mock(return_value=True)

    monkeypatch.setattr(
        retry_module,
        "mark_outbound_delivery_sent",
        mark_sent_mock,
    )

    monkeypatch.setattr(
        retry_module,
        "mark_outbound_delivery_failed",
        Mock(),
    )

    result = retry_outbound_delivery(
        inbound_message_id="wamid.retry-001"
    )

    assert result.status == DELIVERY_STATUS_SENT
    assert result.attempt_count == 2
    assert result.delivery_provider == (
        "MockWhatsAppSender"
    )
    assert result.outbound_message_id == (
        "mock-wamid-out-retry-001"
    )
    assert result.error is None

    delivery_mock.assert_called_once_with(
        recipient_phone="2348012345678",
        message="Your appointment is confirmed.",
        sender=None,
    )

    mark_sent_mock.assert_called_once_with(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.retry-001",
        delivery_provider="MockWhatsAppSender",
        outbound_message_id=(
            "mock-wamid-out-retry-001"
        ),
    )


def test_failed_retry_remains_retry_pending(
    monkeypatch,
) -> None:
    """A failed retry should remain available for another attempt."""
    record = create_retry_record(
        attempt_count=2
    )

    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=record),
    )

    monkeypatch.setattr(
        retry_module,
        "deliver_whatsapp_reply",
        Mock(return_value=create_failed_delivery()),
    )

    mark_failed_mock = Mock(return_value=True)

    monkeypatch.setattr(
        retry_module,
        "mark_outbound_delivery_failed",
        mark_failed_mock,
    )

    result = retry_outbound_delivery(
        inbound_message_id="wamid.retry-001"
    )

    assert result.status == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert result.attempt_count == 3
    assert result.delivery_provider is None
    assert result.outbound_message_id is None
    assert result.error == (
        "Provider still unavailable."
    )

    mark_failed_mock.assert_called_once_with(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.retry-001",
        error_message="Provider still unavailable.",
    )


def test_missing_record_is_rejected(
    monkeypatch,
) -> None:
    """A missing delivery cannot be retried."""
    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=None),
    )

    with pytest.raises(
        OutboundDeliveryRetryError,
        match="was not found",
    ):
        retry_outbound_delivery(
            inbound_message_id="wamid.missing"
        )


def test_sent_record_is_not_retryable(
    monkeypatch,
) -> None:
    """A delivery already marked sent should not be retried."""
    record = create_retry_record()
    record["status"] = DELIVERY_STATUS_SENT

    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=record),
    )

    delivery_mock = Mock()

    monkeypatch.setattr(
        retry_module,
        "deliver_whatsapp_reply",
        delivery_mock,
    )

    with pytest.raises(
        OutboundDeliveryRetryError,
        match="not waiting for retry",
    ):
        retry_outbound_delivery(
            inbound_message_id="wamid.retry-001"
        )

    delivery_mock.assert_not_called()


def test_sent_retry_without_metadata_remains_retryable(
    monkeypatch,
) -> None:
    """Incomplete success metadata should stay retry-pending."""
    record = create_retry_record(
        attempt_count=1
    )

    incomplete_delivery = WhatsAppReplyDelivery(
        status="sent",
        recipient_phone="2348012345678",
        provider=None,
        outbound_message_id=None,
        message="Your appointment is confirmed.",
        error=None,
    )

    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=record),
    )

    monkeypatch.setattr(
        retry_module,
        "deliver_whatsapp_reply",
        Mock(return_value=incomplete_delivery),
    )

    mark_failed_mock = Mock(return_value=True)

    monkeypatch.setattr(
        retry_module,
        "mark_outbound_delivery_failed",
        mark_failed_mock,
    )

    result = retry_outbound_delivery(
        inbound_message_id="wamid.retry-001"
    )

    assert result.status == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert result.attempt_count == 2
    assert result.error == (
        "Successful retry is missing provider metadata."
    )

    mark_failed_mock.assert_called_once_with(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.retry-001",
        error_message=(
            "Successful retry is missing provider metadata."
        ),
    )


def test_failed_sent_update_raises_storage_error(
    monkeypatch,
) -> None:
    """A missing sent update should be explicit."""
    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=create_retry_record()),
    )

    monkeypatch.setattr(
        retry_module,
        "deliver_whatsapp_reply",
        Mock(return_value=create_sent_delivery()),
    )

    monkeypatch.setattr(
        retry_module,
        "mark_outbound_delivery_sent",
        Mock(return_value=False),
    )

    with pytest.raises(
        OutboundDeliveryStorageError,
        match="Unable to mark the retry as sent",
    ):
        retry_outbound_delivery(
            inbound_message_id="wamid.retry-001"
        )


def test_failed_retry_update_raises_storage_error(
    monkeypatch,
) -> None:
    """A missing failed update should be explicit."""
    monkeypatch.setattr(
        retry_module,
        "get_outbound_delivery",
        Mock(return_value=create_retry_record()),
    )

    monkeypatch.setattr(
        retry_module,
        "deliver_whatsapp_reply",
        Mock(return_value=create_failed_delivery()),
    )

    monkeypatch.setattr(
        retry_module,
        "mark_outbound_delivery_failed",
        Mock(return_value=False),
    )

    with pytest.raises(
        OutboundDeliveryStorageError,
        match="Unable to update the failed retry",
    ):
        retry_outbound_delivery(
            inbound_message_id="wamid.retry-001"
        )


def test_retry_batch_counts_sent_and_failed(
    monkeypatch,
) -> None:
    """Batch retry should summarize sent and failed outcomes."""
    records = [
        create_retry_record(
            inbound_message_id="wamid.retry-001"
        ),
        create_retry_record(
            inbound_message_id="wamid.retry-002"
        ),
    ]

    monkeypatch.setattr(
        retry_module,
        "list_retry_pending_deliveries",
        Mock(return_value=records),
    )

    retry_mock = Mock(
        side_effect=[
            retry_module.OutboundRetryResult(
                status=DELIVERY_STATUS_SENT,
                inbound_message_id="wamid.retry-001",
                recipient_phone="2348012345678",
                message="First reply",
                attempt_count=2,
                delivery_provider="MockWhatsAppSender",
                outbound_message_id="mock-out-001",
                error=None,
            ),
            retry_module.OutboundRetryResult(
                status=DELIVERY_STATUS_RETRY_PENDING,
                inbound_message_id="wamid.retry-002",
                recipient_phone="2348012345678",
                message="Second reply",
                attempt_count=2,
                delivery_provider=None,
                outbound_message_id=None,
                error="Still unavailable.",
            ),
        ]
    )

    monkeypatch.setattr(
        retry_module,
        "retry_outbound_delivery",
        retry_mock,
    )

    result = retry_pending_deliveries(
        limit=10
    )

    assert result.requested == 10
    assert result.attempted == 2
    assert result.sent == 1
    assert result.failed == 1
    assert len(result.results) == 2
    assert retry_mock.call_count == 2


def test_retry_batch_handles_service_error(
    monkeypatch,
) -> None:
    """One retry-service error should not stop the batch."""
    records = [
        create_retry_record(
            inbound_message_id="wamid.retry-001",
            attempt_count=3,
        )
    ]

    monkeypatch.setattr(
        retry_module,
        "list_retry_pending_deliveries",
        Mock(return_value=records),
    )

    monkeypatch.setattr(
        retry_module,
        "retry_outbound_delivery",
        Mock(
            side_effect=OutboundDeliveryRetryError(
                "Retry unavailable."
            )
        ),
    )

    result = retry_pending_deliveries(
        limit=5
    )

    assert result.requested == 5
    assert result.attempted == 1
    assert result.sent == 0
    assert result.failed == 1

    item = result.results[0]

    assert item.status == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert item.attempt_count == 3
    assert item.error == "Retry unavailable."


def test_empty_retry_batch_returns_zero_counts(
    monkeypatch,
) -> None:
    """An empty queue should return a valid zero summary."""
    monkeypatch.setattr(
        retry_module,
        "list_retry_pending_deliveries",
        Mock(return_value=[]),
    )

    result = retry_pending_deliveries(
        limit=20
    )

    assert result.requested == 20
    assert result.attempted == 0
    assert result.sent == 0
    assert result.failed == 0
    assert result.results == []