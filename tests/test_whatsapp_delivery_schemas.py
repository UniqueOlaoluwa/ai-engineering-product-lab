"""Tests for WhatsApp batch delivery response schemas."""

from app.schemas import (
    MetaWhatsAppBatchItemResponse,
    MetaWhatsAppBatchResponse,
)


def test_batch_item_accepts_successful_delivery() -> None:
    """A processed message may contain successful delivery data."""
    item = MetaWhatsAppBatchItemResponse(
        status="processed",
        inbound_message_id="wamid.inbound-001",
        sender_phone="2348012345678",
        session_id="whatsapp-2348012345678",
        reply="The clinic opens at 8 a.m.",
        provider="MockLLMProvider",
        stored_message_id=1,
        delivery_status="sent",
        delivery_provider="MockWhatsAppSender",
        outbound_message_id="mock-wamid-out-000001",
    )

    assert item.delivery_status == "sent"
    assert item.delivery_provider == "MockWhatsAppSender"
    assert item.outbound_message_id == (
        "mock-wamid-out-000001"
    )
    assert item.delivery_error is None


def test_batch_item_accepts_failed_delivery() -> None:
    """A processed reply may include a failed delivery outcome."""
    item = MetaWhatsAppBatchItemResponse(
        status="processed",
        inbound_message_id="wamid.inbound-001",
        sender_phone="2348012345678",
        session_id="whatsapp-2348012345678",
        reply="The clinic opens at 8 a.m.",
        provider="MockLLMProvider",
        stored_message_id=1,
        delivery_status="failed",
        delivery_error="Temporary delivery failure.",
    )

    assert item.status == "processed"
    assert item.delivery_status == "failed"
    assert item.delivery_provider is None
    assert item.outbound_message_id is None
    assert item.delivery_error == (
        "Temporary delivery failure."
    )


def test_batch_response_accepts_delivery_counters() -> None:
    """The batch summary should report delivery totals."""
    response = MetaWhatsAppBatchResponse(
        status="completed",
        received=2,
        processed=1,
        duplicates=1,
        ignored=0,
        unsupported=0,
        failed=0,
        deliveries_sent=1,
        deliveries_failed=0,
        deliveries_skipped=1,
        results=[],
    )

    assert response.deliveries_sent == 1
    assert response.deliveries_failed == 0
    assert response.deliveries_skipped == 1