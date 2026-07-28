"""Create language-model providers from application configuration."""

from app.config import Settings
from app.exceptions import ProviderRequestError
from app.providers.base import BaseLLMProvider
from app.providers.mock import MockLLMProvider


def create_provider(settings: Settings) -> BaseLLMProvider:
    """Create the configured language-model provider."""
    if settings.llm_provider == "mock":
        return MockLLMProvider()

    raise ProviderRequestError(
        f"Unsupported LLM provider: '{settings.llm_provider}'."
    )