"""Utilities for validating WhatsApp webhook verification requests."""

import os
from secrets import compare_digest

from dotenv import load_dotenv

WHATSAPP_SUBSCRIBE_MODE = "subscribe"
WHATSAPP_VERIFY_TOKEN_ENV = "WHATSAPP_VERIFY_TOKEN"

# Load local environment variables once when this module is imported.
load_dotenv()


class WhatsAppVerificationError(ValueError):
    """Represent an invalid WhatsApp verification request."""


class WhatsAppVerificationConfigurationError(RuntimeError):
    """Represent missing WhatsApp verification configuration."""


def normalize_verification_value(
    value: str | None,
    field_name: str,
) -> str:
    """Validate and normalize one webhook-verification value."""
    if value is None:
        raise WhatsAppVerificationError(
            f"{field_name} is required."
        )

    cleaned_value = value.strip()

    if not cleaned_value:
        raise WhatsAppVerificationError(
            f"{field_name} cannot be empty."
        )

    return cleaned_value


def get_configured_whatsapp_verify_token() -> str:
    """Return the private WhatsApp verification token."""
    configured_token = os.getenv(
        WHATSAPP_VERIFY_TOKEN_ENV
    )

    if configured_token is None:
        raise WhatsAppVerificationConfigurationError(
            "WHATSAPP_VERIFY_TOKEN is not configured."
        )

    cleaned_token = configured_token.strip()

    if not cleaned_token:
        raise WhatsAppVerificationConfigurationError(
            "WHATSAPP_VERIFY_TOKEN cannot be empty."
        )

    return cleaned_token


def verify_whatsapp_webhook(
    mode: str | None,
    verify_token: str | None,
    challenge: str | None,
    expected_token: str | None,
) -> str:
    """Validate a WhatsApp webhook request and return its challenge."""
    cleaned_mode = normalize_verification_value(
        mode,
        "Verification mode",
    )

    cleaned_token = normalize_verification_value(
        verify_token,
        "Verification token",
    )

    cleaned_challenge = normalize_verification_value(
        challenge,
        "Verification challenge",
    )

    cleaned_expected_token = normalize_verification_value(
        expected_token,
        "Configured verification token",
    )

    if cleaned_mode != WHATSAPP_SUBSCRIBE_MODE:
        raise WhatsAppVerificationError(
            "Unsupported verification mode."
        )

    if not compare_digest(
        cleaned_token,
        cleaned_expected_token,
    ):
        raise WhatsAppVerificationError(
            "Invalid verification token."
        )

    return cleaned_challenge