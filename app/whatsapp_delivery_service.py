"""Coordinate outbound WhatsApp reply delivery."""

from dataclasses import dataclass

from app.whatsapp_sender import (
    WhatsAppDeliveryError,
    WhatsAppDeliveryResult,
    WhatsAppSender,
)
from app.whatsapp_sender_factory import create_whatsapp_sender


@dataclass(frozen=True)
class WhatsAppReplyDelivery:
    """Represent the application-level outcome of reply delivery."""

    status: str
    recipient_phone: str
    provider: str | None
    outbound_message_id: str | None
    message: str
    error: str | None = None


def build_successful_delivery(
    result: WhatsAppDeliveryResult,
) -> WhatsAppReplyDelivery:
    """Convert a sender result into an application delivery result."""
    return WhatsAppReplyDelivery(
        status=result.status,
        recipient_phone=result.recipient_phone,
        provider=result.provider,
        outbound_message_id=result.outbound_message_id,
        message=result.message,
        error=None,
    )


def build_failed_delivery(
    recipient_phone: str,
    message: str,
    error: Exception,
) -> WhatsAppReplyDelivery:
    """Create a failed delivery result without raising further."""
    return WhatsAppReplyDelivery(
        status="failed",
        recipient_phone=recipient_phone,
        provider=None,
        outbound_message_id=None,
        message=message,
        error=str(error),
    )


def deliver_whatsapp_reply(
    recipient_phone: str,
    message: str,
    sender: WhatsAppSender | None = None,
    raise_on_error: bool = False,
) -> WhatsAppReplyDelivery:
    """Deliver one generated reply through a configured sender.

    When ``raise_on_error`` is false, delivery failures are converted
    into structured results so webhook processing can continue.
    """
    selected_sender = sender

    try:
        if selected_sender is None:
            selected_sender = create_whatsapp_sender()

        result = selected_sender.send_text_message(
            recipient_phone=recipient_phone,
            message=message,
        )

        return build_successful_delivery(result)

    except WhatsAppDeliveryError as error:
        if raise_on_error:
            raise

        return build_failed_delivery(
            recipient_phone=recipient_phone,
            message=message,
            error=error,
        )

    except Exception as error:
        wrapped_error = WhatsAppDeliveryError(
            f"Unexpected WhatsApp delivery failure: {error}"
        )

        if raise_on_error:
            raise wrapped_error from error

        return build_failed_delivery(
            recipient_phone=recipient_phone,
            message=message,
            error=wrapped_error,
        )