"""Tests for the local mock WhatsApp sender."""

from app.mock_whatsapp_sender import MockWhatsAppSender


def test_mock_sender_returns_successful_result() -> None:
    """The mock sender should simulate a successful delivery."""
    sender = MockWhatsAppSender()

    result = sender.send_text_message(
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
    )

    assert result.status == "sent"
    assert result.recipient_phone == "2348012345678"
    assert result.provider == "MockWhatsAppSender"
    assert result.outbound_message_id.startswith(
        "mock-wamid-out-"
    )
    assert result.message == (
        "The clinic opens at 8 a.m."
    )


def test_mock_sender_creates_unique_message_ids() -> None:
    """Separate deliveries should receive separate identifiers."""
    sender = MockWhatsAppSender()

    first_result = sender.send_text_message(
        recipient_phone="2348012345678",
        message="First reply",
    )

    second_result = sender.send_text_message(
        recipient_phone="2348012345678",
        message="Second reply",
    )

    assert (
        first_result.outbound_message_id
        != second_result.outbound_message_id
    )