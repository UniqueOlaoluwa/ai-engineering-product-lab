"""Tests for outbound WhatsApp message validation."""

import pytest

from app.whatsapp_sender import (
    WhatsAppDeliveryError,
    normalize_outbound_message,
    normalize_recipient_phone,
)


def test_normalize_phone_accepts_digits() -> None:
    """A digit-only phone number should remain unchanged."""
    assert normalize_recipient_phone(
        "2348012345678"
    ) == "2348012345678"


def test_normalize_phone_removes_leading_plus() -> None:
    """A leading plus sign should be removed."""
    assert normalize_recipient_phone(
        "+2348012345678"
    ) == "2348012345678"


def test_normalize_phone_removes_outer_spaces() -> None:
    """Outer whitespace should be removed."""
    assert normalize_recipient_phone(
        "  +2348012345678  "
    ) == "2348012345678"


def test_normalize_phone_rejects_empty_value() -> None:
    """An empty recipient should be rejected."""
    with pytest.raises(
        WhatsAppDeliveryError,
        match="cannot be empty",
    ):
        normalize_recipient_phone("   ")


def test_normalize_phone_rejects_letters() -> None:
    """Phone numbers containing letters should be rejected."""
    with pytest.raises(
        WhatsAppDeliveryError,
        match="only digits",
    ):
        normalize_recipient_phone(
            "23480ABC45678"
        )


def test_normalize_phone_rejects_short_number() -> None:
    """Very short recipient numbers should be rejected."""
    with pytest.raises(
        WhatsAppDeliveryError,
        match="too short",
    ):
        normalize_recipient_phone("123456")


def test_normalize_phone_rejects_long_number() -> None:
    """Very long recipient numbers should be rejected."""
    with pytest.raises(
        WhatsAppDeliveryError,
        match="too long",
    ):
        normalize_recipient_phone(
            "1" * 21
        )


def test_normalize_outbound_message() -> None:
    """Outer whitespace should be removed from a message."""
    assert normalize_outbound_message(
        "  Hello there  "
    ) == "Hello there"


def test_normalize_message_rejects_empty_value() -> None:
    """An empty outbound message should be rejected."""
    with pytest.raises(
        WhatsAppDeliveryError,
        match="cannot be empty",
    ):
        normalize_outbound_message("   ")


def test_normalize_message_rejects_long_value() -> None:
    """Messages above the limit should be rejected."""
    with pytest.raises(
        WhatsAppDeliveryError,
        match="cannot exceed 4096",
    ):
        normalize_outbound_message(
            "a" * 4097
        )