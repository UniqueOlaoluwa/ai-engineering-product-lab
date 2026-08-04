"""Tests for persisted outbound WhatsApp delivery attempts."""

from unittest.mock import Mock

import pytest

import app.outbound_delivery_service as service_module
from app.outbound_deliveries import (
    DELIVERY_STATUS_PENDING,
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OUTBOUND_PROVIDER,
    OutboundDeliveryStorageError,
)
from app.outbound_delivery_service import (
    persist_and_deliver_reply,
)
from app.whatsapp_delivery_service import (
    WhatsAppReplyDelivery,
)


def create_sent_delivery() -> WhatsAppReplyDelivery:
    """Create a successful synthetic delivery result."""
    return WhatsAppReplyDelivery(
        status="sent",
        recipient_phone="2348012345678",
        provider="MockWhatsAppSender",
        outbound_message_id="mock-wamid-out-000001",
        message="The clinic opens at 8 a.m.",
        error=None,
    )


def create_failed_delivery() -> WhatsAppReplyDelivery:
    """Create a failed synthetic delivery result."""
    return WhatsAppReplyDelivery(
        status="failed",
        recipient_phone="2348012345678",
        provider=None,
        outbound_message_id=None,
        message="The clinic opens at 8 a.m.",
        error="Temporary delivery failure.",
    )


def test_successful_delivery_is_persisted_as_sent(
    monkeypatch,
) -> None:
    """A successful send should create and update one record."""
    get_mock = Mock(return_value=None)
    create_mock = Mock(return_value=7)
    deliver_mock = Mock(
        return_value=create_sent_delivery()
    )
    mark_sent_mock = Mock(return_value=True)
    mark_failed_mock = Mock()

    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        get_mock,
    )
    monkeypatch.setattr(
        service_module,
        "create_outbound_delivery",
        create_mock,
    )
    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        deliver_mock,
    )
    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_sent",
        mark_sent_mock,
    )
    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_failed",
        mark_failed_mock,
    )

    result = persist_and_deliver_reply(
        inbound_message_id="wamid.inbound-001",
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
    )

    assert result.status == DELIVERY_STATUS_SENT
    assert result.delivery_record_id == 7
    assert result.attempt_count == 1
    assert result.delivery_provider == (
        "MockWhatsAppSender"
    )
    assert result.outbound_message_id == (
        "mock-wamid-out-000001"
    )
    assert result.error is None

    create_mock.assert_called_once_with(
        inbound_message_id="wamid.inbound-001",
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
        provider=OUTBOUND_PROVIDER,
    )

    deliver_mock.assert_called_once_with(
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
        sender=None,
    )

    mark_sent_mock.assert_called_once_with(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.inbound-001",
        delivery_provider="MockWhatsAppSender",
        outbound_message_id="mock-wamid-out-000001",
    )

    mark_failed_mock.assert_not_called()


def test_failed_delivery_is_marked_retry_pending(
    monkeypatch,
) -> None:
    """A failed send should be saved for a future retry."""
    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        service_module,
        "create_outbound_delivery",
        Mock(return_value=8),
    )
    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        Mock(return_value=create_failed_delivery()),
    )

    mark_failed_mock = Mock(return_value=True)

    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_failed",
        mark_failed_mock,
    )
    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_sent",
        Mock(),
    )

    result = persist_and_deliver_reply(
        inbound_message_id="wamid.inbound-002",
        recipient_phone="2348012345678",
        message="The clinic opens at 8 a.m.",
    )

    assert result.status == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert result.delivery_record_id == 8
    assert result.attempt_count == 1
    assert result.delivery_provider is None
    assert result.outbound_message_id is None
    assert result.error == (
        "Temporary delivery failure."
    )

    mark_failed_mock.assert_called_once_with(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.inbound-002",
        error_message="Temporary delivery failure.",
    )


def test_existing_sent_record_is_not_sent_again(
    monkeypatch,
) -> None:
    """An existing sent record should protect against duplicates."""
    existing_record = {
        "id": 12,
        "provider": OUTBOUND_PROVIDER,
        "inbound_message_id": "wamid.existing-001",
        "recipient_phone": "2348012345678",
        "message": "Saved reply",
        "status": DELIVERY_STATUS_SENT,
        "delivery_provider": "MockWhatsAppSender",
        "outbound_message_id": "mock-out-existing",
        "error": None,
        "attempt_count": 1,
    }

    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=existing_record),
    )

    create_mock = Mock()
    deliver_mock = Mock()

    monkeypatch.setattr(
        service_module,
        "create_outbound_delivery",
        create_mock,
    )
    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        deliver_mock,
    )

    result = persist_and_deliver_reply(
        inbound_message_id="wamid.existing-001",
        recipient_phone="2348012345678",
        message="New reply should not send",
    )

    assert result.status == DELIVERY_STATUS_SENT
    assert result.delivery_record_id == 12
    assert result.attempt_count == 1
    assert result.outbound_message_id == (
        "mock-out-existing"
    )

    create_mock.assert_not_called()
    deliver_mock.assert_not_called()


def test_existing_retry_record_is_not_immediately_resent(
    monkeypatch,
) -> None:
    """Retry-pending records should wait for the retry service."""
    existing_record = {
        "id": 13,
        "provider": OUTBOUND_PROVIDER,
        "inbound_message_id": "wamid.retry-001",
        "recipient_phone": "2348012345678",
        "message": "Saved retry reply",
        "status": DELIVERY_STATUS_RETRY_PENDING,
        "delivery_provider": None,
        "outbound_message_id": None,
        "error": "Temporary failure.",
        "attempt_count": 1,
    }

    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=existing_record),
    )

    deliver_mock = Mock()

    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        deliver_mock,
    )

    result = persist_and_deliver_reply(
        inbound_message_id="wamid.retry-001",
        recipient_phone="2348012345678",
        message="Do not send yet",
    )

    assert result.status == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert result.error == "Temporary failure."
    assert result.attempt_count == 1

    deliver_mock.assert_not_called()


def test_sent_result_without_provider_metadata_is_retryable(
    monkeypatch,
) -> None:
    """Incomplete success metadata should become retry-pending."""
    incomplete_delivery = WhatsAppReplyDelivery(
        status="sent",
        recipient_phone="2348012345678",
        provider=None,
        outbound_message_id=None,
        message="The clinic opens at 8 a.m.",
        error=None,
    )

    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        service_module,
        "create_outbound_delivery",
        Mock(return_value=14),
    )
    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        Mock(return_value=incomplete_delivery),
    )

    mark_failed_mock = Mock(return_value=True)

    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_failed",
        mark_failed_mock,
    )

    result = persist_and_deliver_reply(
        inbound_message_id="wamid.incomplete-001",
        recipient_phone="2348012345678",
        message="The clinic opens at 8 a.m.",
    )

    assert result.status == (
        DELIVERY_STATUS_RETRY_PENDING
    )
    assert result.error == (
        "Successful delivery is missing provider metadata."
    )

    mark_failed_mock.assert_called_once_with(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id="wamid.incomplete-001",
        error_message=(
            "Successful delivery is missing provider metadata."
        ),
    )


def test_missing_sent_update_raises_storage_error(
    monkeypatch,
) -> None:
    """Failure to update a sent record should be explicit."""
    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        service_module,
        "create_outbound_delivery",
        Mock(return_value=15),
    )
    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        Mock(return_value=create_sent_delivery()),
    )
    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_sent",
        Mock(return_value=False),
    )

    with pytest.raises(
        OutboundDeliveryStorageError,
        match="Unable to update the stored outbound delivery",
    ):
        persist_and_deliver_reply(
            inbound_message_id="wamid.update-missing",
            recipient_phone="2348012345678",
            message="The clinic opens at 8 a.m.",
        )


def test_missing_failed_update_raises_storage_error(
    monkeypatch,
) -> None:
    """Failure to update a failed record should be explicit."""
    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        service_module,
        "create_outbound_delivery",
        Mock(return_value=16),
    )
    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        Mock(return_value=create_failed_delivery()),
    )
    monkeypatch.setattr(
        service_module,
        "mark_outbound_delivery_failed",
        Mock(return_value=False),
    )

    with pytest.raises(
        OutboundDeliveryStorageError,
        match="Unable to update the failed outbound delivery",
    ):
        persist_and_deliver_reply(
            inbound_message_id="wamid.failed-update-missing",
            recipient_phone="2348012345678",
            message="The clinic opens at 8 a.m.",
        )


def test_pending_existing_record_is_returned(
    monkeypatch,
) -> None:
    """A pending record should be returned without duplicate sending."""
    existing_record = {
        "id": 17,
        "provider": OUTBOUND_PROVIDER,
        "inbound_message_id": "wamid.pending-001",
        "recipient_phone": "2348012345678",
        "message": "Pending reply",
        "status": DELIVERY_STATUS_PENDING,
        "delivery_provider": None,
        "outbound_message_id": None,
        "error": None,
        "attempt_count": 0,
    }

    monkeypatch.setattr(
        service_module,
        "get_outbound_delivery",
        Mock(return_value=existing_record),
    )

    deliver_mock = Mock()

    monkeypatch.setattr(
        service_module,
        "deliver_whatsapp_reply",
        deliver_mock,
    )

    result = persist_and_deliver_reply(
        inbound_message_id="wamid.pending-001",
        recipient_phone="2348012345678",
        message="Pending reply",
    )

    assert result.status == DELIVERY_STATUS_PENDING
    assert result.attempt_count == 0

    deliver_mock.assert_not_called()