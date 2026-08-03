"""API tests for WhatsApp webhook verification."""

from unittest.mock import Mock

from fastapi.testclient import TestClient

import app.api as api_module
from app.whatsapp_verification import (
    WhatsAppVerificationConfigurationError,
)

client = TestClient(api_module.app)


def test_valid_verification_returns_plain_text_challenge(
    monkeypatch,
) -> None:
    """A valid Meta-style request should return its challenge."""
    token_mock = Mock(
        return_value="local-secret-token"
    )

    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        token_mock,
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "local-secret-token",
            "hub.challenge": "123456789",
        },
    )

    assert response.status_code == 200
    assert response.text == "123456789"
    assert response.headers["content-type"].startswith(
        "text/plain"
    )

    token_mock.assert_called_once_with()


def test_invalid_token_returns_403(
    monkeypatch,
) -> None:
    """An incorrect verification token should be forbidden."""
    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        Mock(return_value="correct-token"),
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "123456789",
        },
        headers={
            "X-Request-ID": "wrong-whatsapp-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": "Invalid verification token.",
        "status_code": 403,
        "request_id": "wrong-whatsapp-token",
    }


def test_wrong_mode_returns_403(
    monkeypatch,
) -> None:
    """An unsupported verification mode should be forbidden."""
    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        Mock(return_value="local-secret-token"),
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": "local-secret-token",
            "hub.challenge": "123456789",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Unsupported verification mode."
    )


def test_missing_mode_returns_403(
    monkeypatch,
) -> None:
    """A missing mode should be rejected by verification logic."""
    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        Mock(return_value="local-secret-token"),
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.verify_token": "local-secret-token",
            "hub.challenge": "123456789",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Verification mode is required."
    )


def test_missing_incoming_token_returns_403(
    monkeypatch,
) -> None:
    """A missing incoming token should be rejected."""
    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        Mock(return_value="local-secret-token"),
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "123456789",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Verification token is required."
    )


def test_missing_challenge_returns_403(
    monkeypatch,
) -> None:
    """A missing challenge should be rejected."""
    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        Mock(return_value="local-secret-token"),
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "local-secret-token",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"] == (
        "Verification challenge is required."
    )


def test_missing_application_configuration_returns_500(
    monkeypatch,
) -> None:
    """Missing private application configuration is a server error."""
    monkeypatch.setattr(
        api_module,
        "get_configured_whatsapp_verify_token",
        Mock(
            side_effect=WhatsAppVerificationConfigurationError(
                "WHATSAPP_VERIFY_TOKEN is not configured."
            )
        ),
    )

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "some-token",
            "hub.challenge": "123456789",
        },
        headers={
            "X-Request-ID": "missing-whatsapp-config",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "WHATSAPP_VERIFY_TOKEN is not configured.",
        "status_code": 500,
        "request_id": "missing-whatsapp-config",
    }