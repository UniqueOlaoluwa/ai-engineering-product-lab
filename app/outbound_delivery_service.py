"""Persist and execute outbound WhatsApp delivery attempts."""

from dataclasses import dataclass

from app.outbound_deliveries import (
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OUTBOUND_PROVIDER,
    OutboundDeliveryStorageError,
    create_outbound_delivery,
    get_outbound_delivery,
    mark_outbound_delivery_failed,
    mark_outbound_delivery_sent,
)
from app.whatsapp_delivery_service import (
    WhatsAppReplyDelivery,
    deliver_whatsapp_reply,
)
from app.whatsapp_sender import WhatsAppSender


@dataclass(frozen=True)
class OutboundDeliveryAttemptResult:
    """Represent one persisted outbound-delivery attempt."""

    status: str
    inbound_message_id: str
    recipient_phone: str
    message: str
    delivery_record_id: int | None
    attempt_count: int
    delivery_provider: str | None
    outbound_message_id: str | None
    error: str | None


def build_existing_attempt_result(
    record: dict[str, object],
) -> OutboundDeliveryAttemptResult:
    """Convert an existing storage record into a service result."""
    return OutboundDeliveryAttemptResult(
        status=str(record["status"]),
        inbound_message_id=str(
            record["inbound_message_id"]
        ),
        recipient_phone=str(
            record["recipient_phone"]
        ),
        message=str(record["message"]),
        delivery_record_id=int(record["id"]),
        attempt_count=int(record["attempt_count"]),
        delivery_provider=(
            str(record["delivery_provider"])
            if record["delivery_provider"] is not None
            else None
        ),
        outbound_message_id=(
            str(record["outbound_message_id"])
            if record["outbound_message_id"] is not None
            else None
        ),
        error=(
            str(record["error"])
            if record["error"] is not None
            else None
        ),
    )


def build_attempt_result(
    inbound_message_id: str,
    delivery_record_id: int,
    delivery: WhatsAppReplyDelivery,
) -> OutboundDeliveryAttemptResult:
    """Convert a delivery result into a persisted service result."""
    if delivery.status == "sent":
        status_value = DELIVERY_STATUS_SENT
    else:
        status_value = DELIVERY_STATUS_RETRY_PENDING

    return OutboundDeliveryAttemptResult(
        status=status_value,
        inbound_message_id=inbound_message_id,
        recipient_phone=delivery.recipient_phone,
        message=delivery.message,
        delivery_record_id=delivery_record_id,
        attempt_count=1,
        delivery_provider=delivery.provider,
        outbound_message_id=delivery.outbound_message_id,
        error=delivery.error,
    )


def persist_and_deliver_reply(
    inbound_message_id: str,
    recipient_phone: str,
    message: str,
    sender: WhatsAppSender | None = None,
) -> OutboundDeliveryAttemptResult:
    """Persist and attempt delivery of one generated WhatsApp reply.

    Existing records are returned without sending again. This protects
    the system from duplicate outbound delivery if the same inbound
    message is processed more than once.
    """
    existing_record = get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id=inbound_message_id,
    )

    if existing_record is not None:
        return build_existing_attempt_result(
            existing_record
        )

    delivery_record_id = create_outbound_delivery(
        inbound_message_id=inbound_message_id,
        recipient_phone=recipient_phone,
        message=message,
        provider=OUTBOUND_PROVIDER,
    )

    delivery = deliver_whatsapp_reply(
        recipient_phone=recipient_phone,
        message=message,
        sender=sender,
    )

    if delivery.status == "sent":
        if (
            delivery.provider is None
            or delivery.outbound_message_id is None
        ):
            error_message = (
                "Successful delivery is missing provider metadata."
            )

            mark_outbound_delivery_failed(
                provider=OUTBOUND_PROVIDER,
                inbound_message_id=inbound_message_id,
                error_message=error_message,
            )

            return OutboundDeliveryAttemptResult(
                status=DELIVERY_STATUS_RETRY_PENDING,
                inbound_message_id=inbound_message_id,
                recipient_phone=delivery.recipient_phone,
                message=delivery.message,
                delivery_record_id=delivery_record_id,
                attempt_count=1,
                delivery_provider=None,
                outbound_message_id=None,
                error=error_message,
            )

        updated = mark_outbound_delivery_sent(
            provider=OUTBOUND_PROVIDER,
            inbound_message_id=inbound_message_id,
            delivery_provider=delivery.provider,
            outbound_message_id=(
                delivery.outbound_message_id
            ),
        )

        if not updated:
            raise OutboundDeliveryStorageError(
                "Unable to update the stored outbound delivery."
            )

        return build_attempt_result(
            inbound_message_id=inbound_message_id,
            delivery_record_id=delivery_record_id,
            delivery=delivery,
        )

    error_message = (
        delivery.error
        or "Outbound WhatsApp delivery failed."
    )

    updated = mark_outbound_delivery_failed(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id=inbound_message_id,
        error_message=error_message,
    )

    if not updated:
        raise OutboundDeliveryStorageError(
            "Unable to update the failed outbound delivery."
        )

    return build_attempt_result(
        inbound_message_id=inbound_message_id,
        delivery_record_id=delivery_record_id,
        delivery=delivery,
    )