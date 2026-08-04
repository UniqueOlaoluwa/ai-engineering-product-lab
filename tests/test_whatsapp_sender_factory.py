"""Tests for outbound WhatsApp sender selection."""

import pytest

from app.mock_whatsapp_sender import MockWhatsAppSender
from app.whatsapp_sender import WhatsAppDeliveryError
from app.whatsapp_sender_factory import (
    create_whatsapp_sender,
    get_whatsapp_sender_name,
)


def test_default_sender_name_is_mock(
    monkeypatch,
) -> None:
    """Mock mode should be the free local default."""
    monkeypatch.delenv(
        "WHATSAPP_SENDER",
        raising=False,
    )

    assert get_whatsapp_sender_name() == "mock"


def test_configured_sender_name_is_normalized(
    monkeypatch,
) -> None:
    """Configured sender names should be cleaned."""
    monkeypatch.setenv(
        "WHATSAPP_SENDER",
        "  MOCK  ",
    )

    assert get_whatsapp_sender_name() == "mock"


def test_create_mock_sender(
    monkeypatch,
) -> None:
    """The factory should create the local mock sender."""
    monkeypatch.setenv(
        "WHATSAPP_SENDER",
        "mock",
    )

    sender = create_whatsapp_sender()

    assert isinstance(
        sender,
        MockWhatsAppSender,
    )


def test_unsupported_sender_is_rejected(
    monkeypatch,
) -> None:
    """Unknown provider names should fail clearly."""
    monkeypatch.setenv(
        "WHATSAPP_SENDER",
        "unknown",
    )

    with pytest.raises(
        WhatsAppDeliveryError,
        match="Unsupported WhatsApp sender: unknown",
    ):
        create_whatsapp_sender()