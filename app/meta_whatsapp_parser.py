"""Parse incoming Meta WhatsApp Cloud API webhook payloads."""

from dataclasses import dataclass
from typing import Any

from app.schemas import WhatsAppWebhookRequest

META_WHATSAPP_OBJECT = "whatsapp_business_account"
META_MESSAGES_FIELD = "messages"
SUPPORTED_MESSAGE_TYPE = "text"


class MetaWhatsAppPayloadError(ValueError):
    """Represent an unsupported or malformed Meta webhook payload."""


class MetaWhatsAppNoMessageError(MetaWhatsAppPayloadError):
    """Represent a valid webhook that contains no incoming message."""


@dataclass(frozen=True)
class MetaWhatsAppParseResult:
    """Represent all useful items extracted from one Meta webhook."""

    messages: list[WhatsAppWebhookRequest]
    ignored_events: int
    unsupported_messages: int


def require_dictionary(
    value: Any,
    field_name: str,
) -> dict[str, Any]:
    """Return a dictionary or raise a descriptive payload error."""
    if not isinstance(value, dict):
        raise MetaWhatsAppPayloadError(
            f"{field_name} must be an object."
        )

    return value


def require_list(
    value: Any,
    field_name: str,
) -> list[Any]:
    """Return a list or raise a descriptive payload error."""
    if not isinstance(value, list):
        raise MetaWhatsAppPayloadError(
            f"{field_name} must be a list."
        )

    return value


def require_non_empty_list(
    value: Any,
    field_name: str,
) -> list[Any]:
    """Return a non-empty list or raise a payload error."""
    items = require_list(
        value,
        field_name,
    )

    if not items:
        raise MetaWhatsAppPayloadError(
            f"{field_name} cannot be empty."
        )

    return items


def require_non_empty_string(
    value: Any,
    field_name: str,
) -> str:
    """Return a cleaned non-empty string."""
    if not isinstance(value, str):
        raise MetaWhatsAppPayloadError(
            f"{field_name} must be a string."
        )

    cleaned_value = value.strip()

    if not cleaned_value:
        raise MetaWhatsAppPayloadError(
            f"{field_name} cannot be empty."
        )

    return cleaned_value


def validate_payload_object(
    payload: dict[str, Any],
) -> None:
    """Confirm that the payload belongs to WhatsApp Business."""
    payload_object = require_non_empty_string(
        payload.get("object"),
        "Payload object",
    )

    if payload_object != META_WHATSAPP_OBJECT:
        raise MetaWhatsAppPayloadError(
            "Payload object is not a WhatsApp business account."
        )


def build_internal_request(
    message: dict[str, Any],
    role: str,
    history_limit: int,
) -> WhatsAppWebhookRequest:
    """Convert one Meta text message into an internal request."""
    message_type = require_non_empty_string(
        message.get("type"),
        "Message type",
    )

    if message_type != SUPPORTED_MESSAGE_TYPE:
        raise MetaWhatsAppPayloadError(
            f"Unsupported WhatsApp message type: {message_type}."
        )

    sender_phone = require_non_empty_string(
        message.get("from"),
        "Message sender phone",
    )

    message_id = require_non_empty_string(
        message.get("id"),
        "Message ID",
    )

    text_data = require_dictionary(
        message.get("text"),
        "Message text",
    )

    message_body = require_non_empty_string(
        text_data.get("body"),
        "Message text body",
    )

    return WhatsAppWebhookRequest(
        sender_phone=sender_phone,
        message=message_body,
        message_id=message_id,
        role=role,
        history_limit=history_limit,
    )


def parse_message_collection(
    messages: Any,
    role: str,
    history_limit: int,
) -> tuple[
    list[WhatsAppWebhookRequest],
    int,
]:
    """Parse all supported messages from one Meta change value."""
    message_items = require_non_empty_list(
        messages,
        "Payload messages",
    )

    parsed_messages: list[WhatsAppWebhookRequest] = []
    unsupported_messages = 0

    for index, raw_message in enumerate(
        message_items
    ):
        message = require_dictionary(
            raw_message,
            f"Payload message item {index}",
        )

        message_type = require_non_empty_string(
            message.get("type"),
            "Message type",
        )

        if message_type != SUPPORTED_MESSAGE_TYPE:
            unsupported_messages += 1
            continue

        parsed_messages.append(
            build_internal_request(
                message=message,
                role=role,
                history_limit=history_limit,
            )
        )

    return (
        parsed_messages,
        unsupported_messages,
    )


def parse_meta_whatsapp_batch(
    payload: dict[str, Any],
    role: str = "support",
    history_limit: int = 5,
) -> MetaWhatsAppParseResult:
    """Parse all supported messages from one Meta webhook payload."""
    payload_data = require_dictionary(
        payload,
        "Payload",
    )

    validate_payload_object(
        payload_data
    )

    entries = require_non_empty_list(
        payload_data.get("entry"),
        "Payload entry",
    )

    parsed_messages: list[WhatsAppWebhookRequest] = []
    ignored_events = 0
    unsupported_messages = 0

    for entry_index, raw_entry in enumerate(
        entries
    ):
        entry = require_dictionary(
            raw_entry,
            f"Payload entry item {entry_index}",
        )

        changes = require_non_empty_list(
            entry.get("changes"),
            f"Payload changes for entry {entry_index}",
        )

        for change_index, raw_change in enumerate(
            changes
        ):
            change = require_dictionary(
                raw_change,
                (
                    "Payload change item "
                    f"{entry_index}:{change_index}"
                ),
            )

            field_name = require_non_empty_string(
                change.get("field"),
                "Payload change field",
            )

            if field_name != META_MESSAGES_FIELD:
                ignored_events += 1
                continue

            value = require_dictionary(
                change.get("value"),
                "Payload change value",
            )

            messages = value.get("messages")

            if messages is None:
                ignored_events += 1
                continue

            (
                change_messages,
                change_unsupported,
            ) = parse_message_collection(
                messages=messages,
                role=role,
                history_limit=history_limit,
            )

            parsed_messages.extend(
                change_messages
            )

            unsupported_messages += (
                change_unsupported
            )

    if (
        not parsed_messages
        and unsupported_messages == 0
    ):
        raise MetaWhatsAppNoMessageError(
            "Payload does not contain an incoming message."
        )

    return MetaWhatsAppParseResult(
        messages=parsed_messages,
        ignored_events=ignored_events,
        unsupported_messages=unsupported_messages,
    )


def parse_meta_whatsapp_payload(
    payload: dict[str, Any],
    role: str = "support",
    history_limit: int = 5,
) -> WhatsAppWebhookRequest:
    """Parse the first supported message for compatibility."""
    result = parse_meta_whatsapp_batch(
        payload=payload,
        role=role,
        history_limit=history_limit,
    )

    if not result.messages:
        raise MetaWhatsAppPayloadError(
            "Payload contains no supported text messages."
        )

    return result.messages[0]