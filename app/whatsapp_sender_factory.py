"""Create configured outbound WhatsApp sender implementations."""

import os

from dotenv import load_dotenv

from app.mock_whatsapp_sender import MockWhatsAppSender
from app.whatsapp_sender import WhatsAppDeliveryError, WhatsAppSender

load_dotenv()

DEFAULT_WHATSAPP_SENDER = "mock"


def get_whatsapp_sender_name() -> str:
    """Return the configured outbound sender name."""
    sender_name = os.getenv(
        "WHATSAPP_SENDER",
        DEFAULT_WHATSAPP_SENDER,
    )

    normalized_name = sender_name.strip().lower()

    if not normalized_name:
        return DEFAULT_WHATSAPP_SENDER

    return normalized_name


def create_whatsapp_sender() -> WhatsAppSender:
    """Create the configured outbound WhatsApp sender."""
    sender_name = get_whatsapp_sender_name()

    if sender_name == "mock":
        return MockWhatsAppSender()

    raise WhatsAppDeliveryError(
        f"Unsupported WhatsApp sender: {sender_name}."
    )