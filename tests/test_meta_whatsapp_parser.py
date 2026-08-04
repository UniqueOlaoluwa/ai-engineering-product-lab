"""Tests for parsing Meta WhatsApp Cloud API payloads."""

import pytest

from app.meta_whatsapp_parser import (
    MetaWhatsAppNoMessageError,
    MetaWhatsAppPayloadError,
    parse_meta_whatsapp_batch,
    parse_meta_whatsapp_payload,
)


def create_meta_text_payload() -> dict[str, object]:
    """Create a realistic Meta text-message webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789012345",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "987654321098765",
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": "2348012345678",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "2348012345678",
                                    "id": "wamid.meta-text-001",
                                    "timestamp": "1785798000",
                                    "text": {
                                        "body": (
                                            "What time does the clinic open?"
                                        )
                                    },
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def create_text_message(
    sender_phone: str,
    message_id: str,
    body: str,
) -> dict[str, object]:
    """Create one Meta text-message item."""
    return {
        "from": sender_phone,
        "id": message_id,
        "timestamp": "1785798000",
        "text": {
            "body": body,
        },
        "type": "text",
    }


def test_parse_meta_text_payload() -> None:
    """A valid Meta text message should become an internal request."""
    result = parse_meta_whatsapp_payload(
        create_meta_text_payload()
    )

    assert result.sender_phone == "2348012345678"
    assert result.message == "What time does the clinic open?"
    assert result.message_id == "wamid.meta-text-001"
    assert result.role == "support"
    assert result.history_limit == 5


def test_parse_meta_payload_accepts_custom_role_and_history() -> None:
    """The adapter should accept caller-selected processing options."""
    result = parse_meta_whatsapp_payload(
        create_meta_text_payload(),
        role="clinic_admin",
        history_limit=3,
    )

    assert result.role == "clinic_admin"
    assert result.history_limit == 3


def test_parse_batch_returns_one_message() -> None:
    """A standard payload should return one parsed message."""
    result = parse_meta_whatsapp_batch(
        create_meta_text_payload()
    )

    assert len(result.messages) == 1
    assert result.ignored_events == 0
    assert result.unsupported_messages == 0


def test_parse_batch_handles_multiple_messages() -> None:
    """Multiple text messages in one change should all be parsed."""
    payload = create_meta_text_payload()

    value = payload["entry"][0]["changes"][0]["value"]

    value["messages"] = [
        create_text_message(
            sender_phone="2348011111111",
            message_id="wamid.batch-001",
            body="First message",
        ),
        create_text_message(
            sender_phone="2348022222222",
            message_id="wamid.batch-002",
            body="Second message",
        ),
    ]

    result = parse_meta_whatsapp_batch(
        payload,
        role="clinic_admin",
        history_limit=4,
    )

    assert len(result.messages) == 2

    assert result.messages[0].message_id == (
        "wamid.batch-001"
    )
    assert result.messages[1].message_id == (
        "wamid.batch-002"
    )

    assert result.messages[0].role == "clinic_admin"
    assert result.messages[1].history_limit == 4


def test_parse_batch_handles_multiple_entries() -> None:
    """Messages from separate entries should all be returned."""
    payload = create_meta_text_payload()

    payload["entry"].append(
        {
            "id": "second-entry",
            "changes": [
                {
                    "field": "messages",
                    "value": {
                        "messaging_product": "whatsapp",
                        "messages": [
                            create_text_message(
                                sender_phone="2348033333333",
                                message_id="wamid.entry-002",
                                body="Second entry message",
                            )
                        ],
                    },
                }
            ],
        }
    )

    result = parse_meta_whatsapp_batch(
        payload
    )

    assert len(result.messages) == 2
    assert result.messages[1].message_id == (
        "wamid.entry-002"
    )


def test_parse_batch_handles_multiple_changes() -> None:
    """Messages from separate changes should all be returned."""
    payload = create_meta_text_payload()

    payload["entry"][0]["changes"].append(
        {
            "field": "messages",
            "value": {
                "messaging_product": "whatsapp",
                "messages": [
                    create_text_message(
                        sender_phone="2348044444444",
                        message_id="wamid.change-002",
                        body="Second change message",
                    )
                ],
            },
        }
    )

    result = parse_meta_whatsapp_batch(
        payload
    )

    assert len(result.messages) == 2
    assert result.messages[1].message_id == (
        "wamid.change-002"
    )


def test_parse_batch_counts_status_events_as_ignored() -> None:
    """Delivery statuses should be acknowledged but not parsed."""
    payload = create_meta_text_payload()

    value = payload["entry"][0]["changes"][0]["value"]
    value.pop("messages")

    value["statuses"] = [
        {
            "id": "wamid.status-001",
            "status": "delivered",
        }
    ]

    with pytest.raises(
        MetaWhatsAppNoMessageError,
        match="does not contain an incoming message",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_batch_mixes_message_and_status_change() -> None:
    """A payload may contain messages and ignored status events."""
    payload = create_meta_text_payload()

    payload["entry"][0]["changes"].append(
        {
            "field": "messages",
            "value": {
                "messaging_product": "whatsapp",
                "statuses": [
                    {
                        "id": "wamid.status-002",
                        "status": "read",
                    }
                ],
            },
        }
    )

    result = parse_meta_whatsapp_batch(
        payload
    )

    assert len(result.messages) == 1
    assert result.ignored_events == 1


def test_parse_batch_skips_unsupported_message_type() -> None:
    """Unsupported messages should be counted and skipped."""
    payload = create_meta_text_payload()

    value = payload["entry"][0]["changes"][0]["value"]

    value["messages"].append(
        {
            "from": "2348055555555",
            "id": "wamid.image-001",
            "timestamp": "1785798001",
            "type": "image",
            "image": {
                "id": "media-image-001",
            },
        }
    )

    result = parse_meta_whatsapp_batch(
        payload
    )

    assert len(result.messages) == 1
    assert result.unsupported_messages == 1


def test_first_message_parser_rejects_only_unsupported_items() -> None:
    """Compatibility parser should reject a batch without text."""
    payload = create_meta_text_payload()

    value = payload["entry"][0]["changes"][0]["value"]

    value["messages"] = [
        {
            "from": "2348055555555",
            "id": "wamid.image-only",
            "timestamp": "1785798001",
            "type": "image",
            "image": {
                "id": "media-image-only",
            },
        }
    ]

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="contains no supported text messages",
    ):
        parse_meta_whatsapp_payload(
            payload
        )


def test_parse_meta_payload_rejects_wrong_object() -> None:
    """A non-WhatsApp object should be rejected."""
    payload = create_meta_text_payload()
    payload["object"] = "instagram"

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="not a WhatsApp business account",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_missing_entry() -> None:
    """A payload without entry data should be rejected."""
    payload = create_meta_text_payload()
    payload.pop("entry")

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Payload entry must be a list",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_empty_entry() -> None:
    """An empty entry list should be rejected."""
    payload = create_meta_text_payload()
    payload["entry"] = []

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Payload entry cannot be empty",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_missing_changes() -> None:
    """An entry without changes should be rejected."""
    payload = create_meta_text_payload()
    entry = payload["entry"][0]
    entry.pop("changes")

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Payload changes for entry 0 must be a list",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_missing_sender() -> None:
    """The sender phone number is required."""
    payload = create_meta_text_payload()

    message = payload["entry"][0]["changes"][0]["value"][
        "messages"
    ][0]

    message.pop("from")

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Message sender phone must be a string",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_missing_message_id() -> None:
    """Every inbound message must have a provider message ID."""
    payload = create_meta_text_payload()

    message = payload["entry"][0]["changes"][0]["value"][
        "messages"
    ][0]

    message.pop("id")

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Message ID must be a string",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_missing_text_body() -> None:
    """A text message must contain a body."""
    payload = create_meta_text_payload()

    message = payload["entry"][0]["changes"][0]["value"][
        "messages"
    ][0]

    message["text"] = {}

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Message text body must be a string",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_blank_text_body() -> None:
    """Blank incoming text should be rejected."""
    payload = create_meta_text_payload()

    message = payload["entry"][0]["changes"][0]["value"][
        "messages"
    ][0]

    message["text"]["body"] = "   "

    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Message text body cannot be empty",
    ):
        parse_meta_whatsapp_batch(
            payload
        )


def test_parse_meta_payload_rejects_non_dictionary_payload() -> None:
    """The top-level payload must be a JSON object."""
    with pytest.raises(
        MetaWhatsAppPayloadError,
        match="Payload must be an object",
    ):
        parse_meta_whatsapp_batch(  # type: ignore[arg-type]
            ["invalid"]
        )