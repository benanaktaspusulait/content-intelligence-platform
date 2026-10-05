import os
from abc import ABC, abstractmethod


class UnsupportedProviderError(Exception):
    """Raised when requesting an unsupported LLM provider."""

    pass


_DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "claude": "claude-3-5-sonnet-20241022",
    "gemini": "gemini-2.0-flash-exp",
    "ollama": "llama3.2-vision:latest",
}


def get_provider_identity(name: str | None = None) -> tuple[str, str]:
    """Return the provider/model pair used by :func:`get_provider`."""
    resolved_name: str = name if name is not None else os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    provider_name = resolved_name.lower()
    if provider_name not in _DEFAULT_MODELS:
        raise UnsupportedProviderError(f"Unsupported provider: {provider_name}")
    model_env = "OPENAI_VLM_MODEL" if provider_name == "openai" else f"{provider_name.upper()}_MODEL"
    return provider_name, os.getenv(model_env, os.getenv(f"{provider_name.upper()}_MODEL", _DEFAULT_MODELS[provider_name]))


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
            image: Optional base64-encoded image. A provider must either forward
                it to a configured vision model or reject it explicitly; silently
                ignoring image evidence is forbidden.

        Returns:
            Generated completion text

        Raises:
            Exception: If API call fails
        """
        pass

    def complete_images(
        self, prompt: str, image_paths: list[str], system: str = "", temperature: float = 0.0
    ) -> tuple[str, dict[str, object]]:
        """Run one structured vision request when the provider supports it."""
        raise UnsupportedProviderError(f"Vision input is not configured for {type(self).__name__}")


def get_provider(name: str | None = None, model: str | None = None) -> LLMProvider:
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
    name, configured_model = get_provider_identity(name)
    model = model or configured_model

    if name == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model=model)
    elif name == "claude":
        from .claude_provider import ClaudeProvider

        return ClaudeProvider(model=model)
    elif name == "gemini":
        from .gemini_provider import GeminiProvider

        return GeminiProvider(model=model)
    elif name == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(model=model)
    else:
        raise UnsupportedProviderError(f"Unsupported provider: {name}")
