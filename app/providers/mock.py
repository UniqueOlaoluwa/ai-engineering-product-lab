"""Mock language-model provider used during local development."""

from app.exceptions import ProviderRequestError, ProviderTimeoutError
from app.providers.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Return predictable responses without calling a paid AI API."""

    def __init__(self, failure_mode: str | None = None) -> None:
        """Create a mock provider with an optional simulated failure mode."""
        self.failure_mode = failure_mode

    def generate(self, prompt: str) -> str:
        """Return a mock response or raise a simulated provider error."""
        cleaned_prompt = prompt.strip()

        if not cleaned_prompt:
            raise ProviderRequestError(
                "The model provider received an empty prompt."
            )

        if self.failure_mode == "timeout":
            raise ProviderTimeoutError(
                "The mock model provider timed out."
            )

        if self.failure_mode == "request_error":
            raise ProviderRequestError(
                "The mock model provider could not complete the request."
            )

        return (
            "[Mock provider response]\n"
            "The provider successfully received the generated prompt.\n\n"
            f"{cleaned_prompt}"
        )