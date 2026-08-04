"""Tests for outbound WhatsApp reply delivery."""

from unittest.mock import Mock

import pytest

import app.whatsapp_delivery_service as service_module
from app.whatsapp_delivery_service import (
    deliver_whatsapp_reply,
)
from app.whatsapp_sender import (
    WhatsAppDeliveryError,
    WhatsAppDeliveryResult,
)


def create_successful_sender() -> Mock:
    """Create a sender that reports successful delivery."""
    sender = Mock()

    sender.send_text_message.return_value = (
        WhatsAppDeliveryResult(
            status="sent",
            recipient_phone="2348012345678",
            provider="MockWhatsAppSender",
            outbound_message_id="mock-wamid-out-000001",
            message="The clinic opens at 8 a.m.",
        )
    )

    return sender


def test_delivery_uses_supplied_sender() -> None:
    """A supplied sender should receive the generated reply."""
    sender = create_successful_sender()

    result = deliver_whatsapp_reply(
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
        sender=sender,
    )

    assert result.status == "sent"
    assert result.recipient_phone == "2348012345678"
    assert result.provider == "MockWhatsAppSender"
    assert result.outbound_message_id == (
        "mock-wamid-out-000001"
    )
    assert result.message == "The clinic opens at 8 a.m."
    assert result.error is None

    sender.send_text_message.assert_called_once_with(
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
    )


def test_delivery_creates_configured_sender(
    monkeypatch,
) -> None:
    """The configured sender should be created when none is supplied."""
    sender = create_successful_sender()

    factory_mock = Mock(
        return_value=sender
    )

    monkeypatch.setattr(
        service_module,
        "create_whatsapp_sender",
        factory_mock,
    )

    result = deliver_whatsapp_reply(
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
    )

    assert result.status == "sent"

    factory_mock.assert_called_once_with()

    sender.send_text_message.assert_called_once_with(
        recipient_phone="+2348012345678",
        message="The clinic opens at 8 a.m.",
    )


def test_delivery_failure_returns_structured_result() -> None:
    """A sender failure should become a failed delivery result."""
    sender = Mock()

    sender.send_text_message.side_effect = (
        WhatsAppDeliveryError(
            "Temporary delivery failure."
        )
    )

    result = deliver_whatsapp_reply(
        recipient_phone="2348012345678",
        message="Your appointment is confirmed.",
        sender=sender,
    )

    assert result.status == "failed"
    assert result.recipient_phone == "2348012345678"
    assert result.provider is None
    assert result.outbound_message_id is None
    assert result.message == "Your appointment is confirmed."
    assert result.error == "Temporary delivery failure."


def test_delivery_can_raise_known_error() -> None:
    """Strict mode should re-raise a known delivery error."""
    sender = Mock()

    sender.send_text_message.side_effect = (
        WhatsAppDeliveryError(
            "Temporary delivery failure."
        )
    )

    with pytest.raises(
        WhatsAppDeliveryError,
        match="Temporary delivery failure",
    ):
        deliver_whatsapp_reply(
            recipient_phone="2348012345678",
            message="Your appointment is confirmed.",
            sender=sender,
            raise_on_error=True,
        )


def test_unexpected_error_returns_failed_result() -> None:
    """Unexpected sender errors should be wrapped safely."""
    sender = Mock()

    sender.send_text_message.side_effect = RuntimeError(
        "Network socket closed."
    )

    result = deliver_whatsapp_reply(
        recipient_phone="2348012345678",
        message="Your appointment is confirmed.",
        sender=sender,
    )

    assert result.status == "failed"
    assert result.provider is None
    assert result.outbound_message_id is None
    assert result.error == (
        "Unexpected WhatsApp delivery failure: "
        "Network socket closed."
    )


def test_unexpected_error_can_be_raised() -> None:
    """Strict mode should wrap and raise unexpected errors."""
    sender = Mock()

    sender.send_text_message.side_effect = RuntimeError(
        "Network socket closed."
    )

    with pytest.raises(
        WhatsAppDeliveryError,
        match=(
            "Unexpected WhatsApp delivery failure: "
            "Network socket closed"
        ),
    ):
        deliver_whatsapp_reply(
            recipient_phone="2348012345678",
            message="Your appointment is confirmed.",
            sender=sender,
            raise_on_error=True,
        )