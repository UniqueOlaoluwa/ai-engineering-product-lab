"""Utilities for authenticating incoming WhatsApp webhook payloads."""

import hashlib
import hmac
import os

from dotenv import load_dotenv

META_APP_SECRET_ENV = "META_APP_SECRET"
SIGNATURE_PREFIX = "sha256="

# Load local environment values once when this module is imported.
load_dotenv()


class WhatsAppSignatureError(ValueError):
    """Represent an invalid webhook signature or payload."""


class WhatsAppSignatureConfigurationError(RuntimeError):
    """Represent missing webhook-signature configuration."""


def get_configured_meta_app_secret() -> str:
    """Return the private Meta application secret."""
    configured_secret = os.getenv(
        META_APP_SECRET_ENV
    )

    if configured_secret is None:
        raise WhatsAppSignatureConfigurationError(
            "META_APP_SECRET is not configured."
        )

    cleaned_secret = configured_secret.strip()

    if not cleaned_secret:
        raise WhatsAppSignatureConfigurationError(
            "META_APP_SECRET cannot be empty."
        )

    return cleaned_secret


def normalize_signature_header(
    signature_header: str | None,
) -> str:
    """Validate and normalize an incoming signature header."""
    if signature_header is None:
        raise WhatsAppSignatureError(
            "Webhook signature is required."
        )

    cleaned_signature = signature_header.strip()

    if not cleaned_signature:
        raise WhatsAppSignatureError(
            "Webhook signature cannot be empty."
        )

    if not cleaned_signature.startswith(
        SIGNATURE_PREFIX
    ):
        raise WhatsAppSignatureError(
            "Webhook signature must use the sha256 prefix."
        )

    hexadecimal_signature = cleaned_signature[
        len(SIGNATURE_PREFIX):
    ]

    if len(hexadecimal_signature) != 64:
        raise WhatsAppSignatureError(
            "Webhook signature must contain a "
            "64-character SHA-256 digest."
        )

    try:
        bytes.fromhex(hexadecimal_signature)
    except ValueError as error:
        raise WhatsAppSignatureError(
            "Webhook signature must contain hexadecimal characters."
        ) from error

    return cleaned_signature


def generate_whatsapp_signature(
    payload: bytes,
    app_secret: str,
) -> str:
    """Generate the expected SHA-256 webhook signature."""
    if not isinstance(payload, bytes):
        raise WhatsAppSignatureError(
            "Webhook payload must be raw bytes."
        )

    cleaned_secret = app_secret.strip()

    if not cleaned_secret:
        raise WhatsAppSignatureError(
            "Meta app secret cannot be empty."
        )

    digest = hmac.new(
        key=cleaned_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return f"{SIGNATURE_PREFIX}{digest}"


def verify_whatsapp_signature(
    payload: bytes,
    signature_header: str | None,
    app_secret: str,
) -> None:
    """Verify that a webhook payload has a valid signature."""
    cleaned_signature = normalize_signature_header(
        signature_header
    )

    expected_signature = generate_whatsapp_signature(
        payload=payload,
        app_secret=app_secret,
    )

    if not hmac.compare_digest(
        cleaned_signature,
        expected_signature,
    ):
        raise WhatsAppSignatureError(
            "Invalid webhook signature."
        )