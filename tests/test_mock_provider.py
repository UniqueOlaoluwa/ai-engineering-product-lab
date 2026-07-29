"""Tests for the local mock model provider."""

import pytest

from app.exceptions import ProviderRequestError, ProviderTimeoutError
from app.providers.mock import MockLLMProvider


def test_mock_provider_returns_response() -> None:
    """A normal mock request should return predictable output."""
    provider = MockLLMProvider()

    response = provider.generate("Help a business improve support.")

    assert response.startswith("[Mock provider response]")
    assert "Help a business improve support." in response


def test_mock_provider_rejects_empty_prompt() -> None:
    """The provider should reject a prompt containing only spaces."""
    provider = MockLLMProvider()

    with pytest.raises(
        ProviderRequestError,
        match="received an empty prompt",
    ):
        provider.generate("   ")


def test_mock_provider_simulates_timeout() -> None:
    """The timeout failure mode should raise the correct exception."""
    provider = MockLLMProvider(failure_mode="timeout")

    with pytest.raises(
        ProviderTimeoutError,
        match="timed out",
    ):
        provider.generate("Test prompt")


def test_mock_provider_simulates_request_error() -> None:
    """The request-error mode should raise the correct exception."""
    provider = MockLLMProvider(failure_mode="request_error")

    with pytest.raises(
        ProviderRequestError,
        match="could not complete the request",
    ):
        provider.generate("Test prompt")