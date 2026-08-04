"""Retry persisted outbound WhatsApp deliveries."""

from dataclasses import dataclass

from app.outbound_deliveries import (
    DELIVERY_STATUS_RETRY_PENDING,
    DELIVERY_STATUS_SENT,
    OUTBOUND_PROVIDER,
    OutboundDeliveryStorageError,
    get_outbound_delivery,
    list_retry_pending_deliveries,
    mark_outbound_delivery_failed,
    mark_outbound_delivery_sent,
)
from app.whatsapp_delivery_service import (
    WhatsAppReplyDelivery,
    deliver_whatsapp_reply,
)
from app.whatsapp_sender import WhatsAppSender


class OutboundDeliveryRetryError(RuntimeError):
    """Represent an invalid outbound-delivery retry request."""


@dataclass(frozen=True)
class OutboundRetryResult:
    """Represent the outcome of retrying one stored delivery."""

    status: str
    inbound_message_id: str
    recipient_phone: str
    message: str
    attempt_count: int
    delivery_provider: str | None
    outbound_message_id: str | None
    error: str | None


@dataclass(frozen=True)
class OutboundRetryBatchResult:
    """Summarize a batch of outbound-delivery retries."""

    requested: int
    attempted: int
    sent: int
    failed: int
    results: list[OutboundRetryResult]


def require_retry_pending_record(
    record: dict[str, object] | None,
    inbound_message_id: str,
) -> dict[str, object]:
    """Return a retryable record or raise a descriptive error."""
    if record is None:
        raise OutboundDeliveryRetryError(
            "Outbound delivery was not found."
        )

    record_status = str(record["status"])

    if record_status != DELIVERY_STATUS_RETRY_PENDING:
        raise OutboundDeliveryRetryError(
            "Outbound delivery is not waiting for retry."
        )

    stored_message_id = str(
        record["inbound_message_id"]
    )

    if stored_message_id != inbound_message_id:
        raise OutboundDeliveryRetryError(
            "Outbound delivery message ID does not match."
        )

    return record


def build_retry_result(
    record: dict[str, object],
    delivery: WhatsAppReplyDelivery,
) -> OutboundRetryResult:
    """Build one retry result from storage and delivery data."""
    previous_attempt_count = int(
        record["attempt_count"]
    )

    if delivery.status == "sent":
        status_value = DELIVERY_STATUS_SENT
    else:
        status_value = DELIVERY_STATUS_RETRY_PENDING

    return OutboundRetryResult(
        status=status_value,
        inbound_message_id=str(
            record["inbound_message_id"]
        ),
        recipient_phone=delivery.recipient_phone,
        message=delivery.message,
        attempt_count=previous_attempt_count + 1,
        delivery_provider=delivery.provider,
        outbound_message_id=delivery.outbound_message_id,
        error=delivery.error,
    )


def retry_outbound_delivery(
    inbound_message_id: str,
    sender: WhatsAppSender | None = None,
) -> OutboundRetryResult:
    """Retry one stored outbound WhatsApp delivery."""
    record = get_outbound_delivery(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id=inbound_message_id,
    )

    retry_record = require_retry_pending_record(
        record=record,
        inbound_message_id=inbound_message_id,
    )

    recipient_phone = str(
        retry_record["recipient_phone"]
    )

    message = str(
        retry_record["message"]
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
                "Successful retry is missing provider metadata."
            )

            updated = mark_outbound_delivery_failed(
                provider=OUTBOUND_PROVIDER,
                inbound_message_id=inbound_message_id,
                error_message=error_message,
            )

            if not updated:
                raise OutboundDeliveryStorageError(
                    "Unable to update the incomplete retry."
                )

            failed_delivery = WhatsAppReplyDelivery(
                status="failed",
                recipient_phone=delivery.recipient_phone,
                provider=None,
                outbound_message_id=None,
                message=delivery.message,
                error=error_message,
            )

            return build_retry_result(
                record=retry_record,
                delivery=failed_delivery,
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
                "Unable to mark the retry as sent."
            )

        return build_retry_result(
            record=retry_record,
            delivery=delivery,
        )

    error_message = (
        delivery.error
        or "Outbound WhatsApp retry failed."
    )

    updated = mark_outbound_delivery_failed(
        provider=OUTBOUND_PROVIDER,
        inbound_message_id=inbound_message_id,
        error_message=error_message,
    )

    if not updated:
        raise OutboundDeliveryStorageError(
            "Unable to update the failed retry."
        )

    failed_delivery = WhatsAppReplyDelivery(
        status="failed",
        recipient_phone=delivery.recipient_phone,
        provider=delivery.provider,
        outbound_message_id=delivery.outbound_message_id,
        message=delivery.message,
        error=error_message,
    )

    return build_retry_result(
        record=retry_record,
        delivery=failed_delivery,
    )


def retry_pending_deliveries(
    limit: int = 20,
    sender: WhatsAppSender | None = None,
) -> OutboundRetryBatchResult:
    """Retry a limited batch of pending outbound deliveries."""
    records = list_retry_pending_deliveries(
        limit=limit
    )

    results: list[OutboundRetryResult] = []

    sent_count = 0
    failed_count = 0

    for record in records:
        inbound_message_id = str(
            record["inbound_message_id"]
        )

        try:
            result = retry_outbound_delivery(
                inbound_message_id=inbound_message_id,
                sender=sender,
            )
        except (
            OutboundDeliveryRetryError,
            OutboundDeliveryStorageError,
        ) as error:
            failed_count += 1

            results.append(
                OutboundRetryResult(
                    status=DELIVERY_STATUS_RETRY_PENDING,
                    inbound_message_id=inbound_message_id,
                    recipient_phone=str(
                        record["recipient_phone"]
                    ),
                    message=str(
                        record["message"]
                    ),
                    attempt_count=int(
                        record["attempt_count"]
                    ),
                    delivery_provider=None,
                    outbound_message_id=None,
                    error=str(error),
                )
            )

            continue

        results.append(result)

        if result.status == DELIVERY_STATUS_SENT:
            sent_count += 1
        else:
            failed_count += 1

    return OutboundRetryBatchResult(
        requested=limit,
        attempted=len(records),
        sent=sent_count,
        failed=failed_count,
        results=results,
    )