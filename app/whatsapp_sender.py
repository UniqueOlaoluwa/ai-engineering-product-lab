"""Outbound WhatsApp message delivery abstractions."""

from dataclasses import dataclass
from typing import Protocol


class WhatsAppDeliveryError(RuntimeError):
    """Represent an outbound WhatsApp delivery failure."""


@dataclass(frozen=True)
class WhatsAppDeliveryResult:
    """Represent the result of sending one WhatsApp message."""

    status: str
    recipient_phone: str
    provider: str
    outbound_message_id: str
    message: str


class WhatsAppSender(Protocol):
    """Define the interface implemented by WhatsApp senders."""

    def send_text_message(
        self,
        recipient_phone: str,
        message: str,
    ) -> WhatsAppDeliveryResult:
        """Send one text message to a WhatsApp recipient."""


def normalize_recipient_phone(
    recipient_phone: str,
) -> str:
    """Validate and normalize a WhatsApp recipient number."""
    if not isinstance(recipient_phone, str):
        raise WhatsAppDeliveryError(
            "Recipient phone must be a string."
        )

    normalized_phone = recipient_phone.strip()

    if normalized_phone.startswith("+"):
        normalized_phone = normalized_phone[1:]

    if not normalized_phone:
        raise WhatsAppDeliveryError(
            "Recipient phone cannot be empty."
        )

    if not normalized_phone.isdigit():
        raise WhatsAppDeliveryError(
            "Recipient phone must contain only digits."
        )

    if len(normalized_phone) < 7:
        raise WhatsAppDeliveryError(
            "Recipient phone is too short."
        )

    if len(normalized_phone) > 20:
        raise WhatsAppDeliveryError(
            "Recipient phone is too long."
        )

    return normalized_phone


def normalize_outbound_message(
    message: str,
) -> str:
    """Validate and normalize an outbound WhatsApp message."""
    if not isinstance(message, str):
        raise WhatsAppDeliveryError(
            "Outbound message must be a string."
        )

    normalized_message = message.strip()

    if not normalized_message:
        raise WhatsAppDeliveryError(
            "Outbound message cannot be empty."
        )

    if len(normalized_message) > 4096:
        raise WhatsAppDeliveryError(
            "Outbound message cannot exceed 4096 characters."
        )

    return normalized_message