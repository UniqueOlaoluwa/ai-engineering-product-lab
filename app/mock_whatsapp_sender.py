"""Local mock provider for outbound WhatsApp delivery."""

from itertools import count

from app.whatsapp_sender import (
    WhatsAppDeliveryResult,
    normalize_outbound_message,
    normalize_recipient_phone,
)

_message_counter = count(start=1)


class MockWhatsAppSender:
    """Simulate outbound WhatsApp delivery without external APIs."""

    provider_name = "MockWhatsAppSender"

    def send_text_message(
        self,
        recipient_phone: str,
        message: str,
    ) -> WhatsAppDeliveryResult:
        """Return a synthetic successful delivery result."""
        normalized_phone = normalize_recipient_phone(
            recipient_phone
        )

        normalized_message = normalize_outbound_message(
            message
        )

        outbound_message_id = (
            f"mock-wamid-out-{next(_message_counter):06d}"
        )

        return WhatsAppDeliveryResult(
            status="sent",
            recipient_phone=normalized_phone,
            provider=self.provider_name,
            outbound_message_id=outbound_message_id,
            message=normalized_message,
        )