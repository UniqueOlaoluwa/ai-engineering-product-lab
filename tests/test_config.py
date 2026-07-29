"""Tests for application environment configuration."""

from app.config import Settings, get_optional_environment_value, load_settings


def test_load_settings_uses_mock_provider() -> None:
    """The local environment should currently select the mock provider."""
    settings = load_settings()

    assert settings.llm_provider == "mock"


def test_settings_stores_expected_values() -> None:
    """Settings should preserve structured configuration values."""
    settings = Settings(
        app_env="testing",
        llm_provider="mock",
        openai_api_key=None,
        openai_model=None,
    )

    assert settings.app_env == "testing"
    assert settings.llm_provider == "mock"
    assert settings.openai_api_key is None
    assert settings.openai_model is None


def test_optional_environment_value_returns_none_for_missing_value(
    monkeypatch,
) -> None:
    """A missing environment variable should become None."""
    monkeypatch.delenv("TEST_OPTIONAL_VALUE", raising=False)

    assert get_optional_environment_value("TEST_OPTIONAL_VALUE") is None


def test_optional_environment_value_cleans_text(
    monkeypatch,
) -> None:
    """Environment values should have surrounding spaces removed."""
    monkeypatch.setenv("TEST_OPTIONAL_VALUE", "  example-value  ")

    assert (
        get_optional_environment_value("TEST_OPTIONAL_VALUE")
        == "example-value"
    )


def test_optional_environment_value_returns_none_for_blank_text(
    monkeypatch,
) -> None:
    """Whitespace-only environment values should become None."""
    monkeypatch.setenv("TEST_OPTIONAL_VALUE", "   ")

    assert get_optional_environment_value("TEST_OPTIONAL_VALUE") is None