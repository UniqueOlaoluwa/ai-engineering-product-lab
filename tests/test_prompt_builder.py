"""Tests for role normalization and prompt generation."""

import pytest

from app.prompt_builder import (
    build_prompt,
    get_default_role,
    get_role_name,
    normalize_role,
)


def test_default_role_is_support() -> None:
    """The configured fallback role should be support."""
    assert get_default_role() == "support"


def test_normalize_role_accepts_valid_role() -> None:
    """Valid roles should be cleaned and returned."""
    assert normalize_role("  BUSINESS  ") == "business"


def test_normalize_role_uses_default_for_unknown_role() -> None:
    """Unknown roles should fall back to the configured default."""
    assert normalize_role("doctor") == "support"


def test_get_role_name_returns_display_name() -> None:
    """Internal role keys should map to friendly display names."""
    assert get_role_name("clinic_admin") == "Clinic Administrative Assistant"


def test_build_prompt_contains_cleaned_message() -> None:
    """The generated prompt should contain the cleaned user message."""
    prompt = build_prompt(
        "  Help me automate customer support.  ",
        "business",
    )

    assert "User message: Help me automate customer support." in prompt


def test_build_prompt_contains_role_instruction() -> None:
    """The prompt should include the selected role instruction."""
    prompt = build_prompt(
        "Book an appointment.",
        "clinic_admin",
    )

    assert "Do not diagnose" in prompt
    assert "make clinical decisions" in prompt


def test_build_prompt_rejects_empty_message() -> None:
    """An empty message should produce a validation error."""
    with pytest.raises(
        ValueError,
        match="User message cannot be empty",
    ):
        build_prompt("   ", "support")