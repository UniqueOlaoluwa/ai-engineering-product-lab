"""Tests for WhatsApp-specific utility functions."""

import pytest

from app.whatsapp import (
    build_whatsapp_session_id,
    normalize_phone_number,
)


def test_normalize_phone_number_removes_plus_sign() -> None:
    """A valid international number should become digits only."""
    result = normalize_phone_number("+2348012345678")

    assert result == "2348012345678"


def test_normalize_phone_number_keeps_digits() -> None:
    """A digits-only phone number should remain unchanged."""
    result = normalize_phone_number("2348012345678")

    assert result == "2348012345678"


def test_normalize_phone_number_trims_spaces() -> None:
    """Surrounding whitespace should be removed."""
    result = normalize_phone_number("  +2348012345678  ")

    assert result == "2348012345678"


def test_build_whatsapp_session_id_is_stable() -> None:
    """The same phone number should always produce the same session."""
    first = build_whatsapp_session_id("+2348012345678")
    second = build_whatsapp_session_id("2348012345678")

    assert first == "whatsapp-2348012345678"
    assert second == first


def test_normalize_phone_number_rejects_letters() -> None:
    """Phone numbers containing letters should be rejected."""
    with pytest.raises(
        ValueError,
        match="must contain only digits",
    ):
        normalize_phone_number("+23480ABC45678")


def test_normalize_phone_number_rejects_symbols() -> None:
    """Spaces or formatting symbols inside a number are rejected."""
    with pytest.raises(
        ValueError,
        match="must contain only digits",
    ):
        normalize_phone_number("+234-801-234-5678")


def test_normalize_phone_number_rejects_short_number() -> None:
    """Numbers shorter than seven digits should be rejected."""
    with pytest.raises(
        ValueError,
        match="at least 7 digits",
    ):
        normalize_phone_number("12345")


def test_normalize_phone_number_rejects_long_number() -> None:
    """Numbers longer than fifteen digits should be rejected."""
    with pytest.raises(
        ValueError,
        match="cannot exceed 15 digits",
    ):
        normalize_phone_number("1" * 16)


def test_normalize_phone_number_rejects_blank_value() -> None:
    """Blank phone numbers should be rejected."""
    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        normalize_phone_number("   ")