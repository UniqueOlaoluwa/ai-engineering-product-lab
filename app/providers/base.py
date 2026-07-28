"""Base interface for AI model providers."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Define the interface every language-model provider must implement."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate and return a response for the supplied prompt."""
        raise NotImplementedError