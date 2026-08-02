"""Utilities for processing simplified WhatsApp-style messages."""

import re

WHATSAPP_SESSION_PREFIX = "whatsapp"

PHONE_PATTERN = re.compile(r"^\+?[0-9]+$")


def normalize_phone_number(phone_number: str) -> str:
    """Validate and normalize a sender phone number."""
    cleaned_phone = phone_number.strip()

    if not cleaned_phone:
        raise ValueError("Sender phone number cannot be empty.")

    if not PHONE_PATTERN.fullmatch(cleaned_phone):
        raise ValueError(
            "Sender phone number must contain only digits "
            "and an optional leading plus sign."
        )

    digits_only = cleaned_phone.lstrip("+")

    if len(digits_only) < 7:
        raise ValueError(
            "Sender phone number must contain at least 7 digits."
        )

    if len(digits_only) > 15:
        raise ValueError(
            "Sender phone number cannot exceed 15 digits."
        )

    return digits_only


def build_whatsapp_session_id(phone_number: str) -> str:
    """Create a stable conversation session ID from a phone number."""
    normalized_phone = normalize_phone_number(phone_number)

    return f"{WHATSAPP_SESSION_PREFIX}-{normalized_phone}"