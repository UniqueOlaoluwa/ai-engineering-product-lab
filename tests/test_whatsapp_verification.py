"""Tests for WhatsApp webhook-verification utilities."""

import pytest

from app.whatsapp_verification import (
    WhatsAppVerificationConfigurationError,
    WhatsAppVerificationError,
    get_configured_whatsapp_verify_token,
    normalize_verification_value,
    verify_whatsapp_webhook,
)


def test_normalize_verification_value_trims_spaces() -> None:
    """Surrounding whitespace should be removed."""
    result = normalize_verification_value(
        "  subscribe  ",
        "Verification mode",
    )

    assert result == "subscribe"


def test_normalize_verification_value_rejects_none() -> None:
    """Missing verification values should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Verification mode is required",
    ):
        normalize_verification_value(
            None,
            "Verification mode",
        )


def test_normalize_verification_value_rejects_blank_value() -> None:
    """Blank verification values should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Verification token cannot be empty",
    ):
        normalize_verification_value(
            "   ",
            "Verification token",
        )


def test_get_configured_token_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The private verification token should load from the environment."""
    monkeypatch.setenv(
        "WHATSAPP_VERIFY_TOKEN",
        "local-secret-token",
    )

    result = get_configured_whatsapp_verify_token()

    assert result == "local-secret-token"


def test_get_configured_token_trims_spaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Surrounding spaces should not form part of the token."""
    monkeypatch.setenv(
        "WHATSAPP_VERIFY_TOKEN",
        "  local-secret-token  ",
    )

    result = get_configured_whatsapp_verify_token()

    assert result == "local-secret-token"


def test_get_configured_token_rejects_missing_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing application configuration should be reported."""
    monkeypatch.delenv(
        "WHATSAPP_VERIFY_TOKEN",
        raising=False,
    )

    with pytest.raises(
        WhatsAppVerificationConfigurationError,
        match="WHATSAPP_VERIFY_TOKEN is not configured",
    ):
        get_configured_whatsapp_verify_token()


def test_get_configured_token_rejects_blank_environment_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A blank configured token should be rejected."""
    monkeypatch.setenv(
        "WHATSAPP_VERIFY_TOKEN",
        "   ",
    )

    with pytest.raises(
        WhatsAppVerificationConfigurationError,
        match="WHATSAPP_VERIFY_TOKEN cannot be empty",
    ):
        get_configured_whatsapp_verify_token()


def test_verify_whatsapp_webhook_returns_challenge() -> None:
    """A valid subscription request should return the challenge."""
    result = verify_whatsapp_webhook(
        mode="subscribe",
        verify_token="local-secret-token",
        challenge="123456789",
        expected_token="local-secret-token",
    )

    assert result == "123456789"


def test_verify_whatsapp_webhook_trims_values() -> None:
    """Verification values should be normalized before comparison."""
    result = verify_whatsapp_webhook(
        mode="  subscribe  ",
        verify_token="  local-secret-token  ",
        challenge="  challenge-value  ",
        expected_token="  local-secret-token  ",
    )

    assert result == "challenge-value"


def test_verify_whatsapp_webhook_rejects_wrong_mode() -> None:
    """Only subscribe-mode verification should be accepted."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Unsupported verification mode",
    ):
        verify_whatsapp_webhook(
            mode="unsubscribe",
            verify_token="local-secret-token",
            challenge="123456789",
            expected_token="local-secret-token",
        )


def test_verify_whatsapp_webhook_rejects_wrong_token() -> None:
    """An incorrect verification token should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Invalid verification token",
    ):
        verify_whatsapp_webhook(
            mode="subscribe",
            verify_token="wrong-token",
            challenge="123456789",
            expected_token="local-secret-token",
        )


def test_verify_whatsapp_webhook_rejects_missing_mode() -> None:
    """A missing mode should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Verification mode is required",
    ):
        verify_whatsapp_webhook(
            mode=None,
            verify_token="local-secret-token",
            challenge="123456789",
            expected_token="local-secret-token",
        )


def test_verify_whatsapp_webhook_rejects_missing_token() -> None:
    """A missing incoming token should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Verification token is required",
    ):
        verify_whatsapp_webhook(
            mode="subscribe",
            verify_token=None,
            challenge="123456789",
            expected_token="local-secret-token",
        )


def test_verify_whatsapp_webhook_rejects_missing_challenge() -> None:
    """A missing challenge should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Verification challenge is required",
    ):
        verify_whatsapp_webhook(
            mode="subscribe",
            verify_token="local-secret-token",
            challenge=None,
            expected_token="local-secret-token",
        )


def test_verify_whatsapp_webhook_rejects_missing_expected_token() -> None:
    """A missing expected token should be rejected."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Configured verification token is required",
    ):
        verify_whatsapp_webhook(
            mode="subscribe",
            verify_token="local-secret-token",
            challenge="123456789",
            expected_token=None,
        )


def test_verify_whatsapp_webhook_rejects_blank_expected_token() -> None:
    """A blank expected token should not disable verification."""
    with pytest.raises(
        WhatsAppVerificationError,
        match="Configured verification token cannot be empty",
    ):
        verify_whatsapp_webhook(
            mode="subscribe",
            verify_token="local-secret-token",
            challenge="123456789",
            expected_token="   ",
        )