"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Store application configuration values."""

    app_env: str
    llm_provider: str
    openai_api_key: str | None
    openai_model: str | None


def get_optional_environment_value(name: str) -> str | None:
    """Return a cleaned environment value or None when it is empty."""
    value = os.getenv(name)

    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    return cleaned_value


def load_settings() -> Settings:
    """Load and normalize application settings."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    llm_provider = os.getenv("LLM_PROVIDER", "mock").strip().lower()

    return Settings(
        app_env=app_env,
        llm_provider=llm_provider,
        openai_api_key=get_optional_environment_value("OPENAI_API_KEY"),
        openai_model=get_optional_environment_value("OPENAI_MODEL"),
    )