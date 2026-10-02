import os
from abc import ABC, abstractmethod


class UnsupportedProviderError(Exception):
    """Raised when requesting an unsupported LLM provider."""

    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        """
        Generate completion from LLM.

        Args:
            prompt: User prompt text
            system: System prompt text
            temperature: Sampling temperature (0.0-1.0)
            image: Optional base64-encoded image for vision-capable callers (e.g.
                CharacterVerifier). Providers that do not support vision input may
                accept and ignore this parameter rather than rejecting the call.

        Returns:
            Generated completion text

        Raises:
            Exception: If API call fails
        """
        pass


def get_provider(name: str | None = None) -> LLMProvider:
    """
    Factory function to get LLM provider by name.

    Args:
        name: Provider name ('openai', 'claude', 'gemini', 'ollama')
              If None, uses DEFAULT_LLM_PROVIDER env var (default: 'openai')

    Returns:
        LLMProvider instance

    Raises:
        UnsupportedProviderError: If provider name not recognized
    """
    if name is None:
        name = os.getenv("DEFAULT_LLM_PROVIDER", "openai")

    name = name.lower()

    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    elif name == "claude":
        from .claude_provider import ClaudeProvider

        return ClaudeProvider()
    elif name == "gemini":
        from .gemini_provider import GeminiProvider

        return GeminiProvider()
    elif name == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider()
    else:
        raise UnsupportedProviderError(f"Unsupported provider: {name}")
