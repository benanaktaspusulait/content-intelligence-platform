import os
from unittest.mock import MagicMock, patch

import pytest

from app.llm.provider import LLMProvider, UnsupportedProviderError, get_provider


def test_abstract_provider_cannot_instantiate() -> None:
    """Abstract LLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_get_provider_unsupported_raises() -> None:
    """get_provider raises UnsupportedProviderError for unknown provider."""
    with pytest.raises(UnsupportedProviderError):
        get_provider("nonexistent")


def test_openai_provider_complete() -> None:
    """OpenAI provider calls OpenAI API and returns completion."""
    with patch("app.llm.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="test response"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        from app.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        result = provider.complete("test prompt", system="test system")

        assert result == "test response"
        mock_client.chat.completions.create.assert_called_once()


def test_openai_provider_complete_accepts_optional_image_without_sending_it() -> None:
    """``complete`` accepts the ``image`` keyword used by vision callers (e.g. CharacterVerifier),
    but OpenAIProvider does not yet forward it to the chat-completions call -- this pins that
    exact current behavior so widening the interface for mypy does not silently change it."""
    with patch("app.llm.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="described"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        from app.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        result = provider.complete("describe this", image="base64-image-data")

        assert result == "described"
        _, kwargs = mock_client.chat.completions.create.call_args
        assert "image" not in kwargs


def test_openai_provider_complete_handles_none_content() -> None:
    """OpenAI provider returns an empty string instead of None.

    The OpenAI SDK types ``message.content`` as ``str | None`` (e.g. a
    tool-call-only response has no text content). The ``LLMProvider``
    interface promises a ``str`` return, so this pins the coercion to an
    empty string rather than leaking ``None`` to callers.
    """
    with patch("app.llm.openai_provider.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        from app.llm.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="test-key")
        result = provider.complete("test prompt")

        assert result == ""


def test_get_provider_openai() -> None:
    """get_provider('openai') returns OpenAIProvider."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = get_provider("openai")
        from app.llm.openai_provider import OpenAIProvider

        assert isinstance(provider, OpenAIProvider)


def test_get_provider_claude() -> None:
    """get_provider('claude') returns ClaudeProvider."""
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        provider = get_provider("claude")
        from app.llm.claude_provider import ClaudeProvider

        assert isinstance(provider, ClaudeProvider)


def test_get_provider_gemini() -> None:
    """get_provider('gemini') returns GeminiProvider."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        provider = get_provider("gemini")
        from app.llm.gemini_provider import GeminiProvider

        assert isinstance(provider, GeminiProvider)


def test_get_provider_ollama() -> None:
    """get_provider('ollama') returns OllamaProvider."""
    provider = get_provider("ollama")
    from app.llm.ollama_provider import OllamaProvider

    assert isinstance(provider, OllamaProvider)


def test_get_provider_default_uses_env() -> None:
    """get_provider() with no args uses DEFAULT_LLM_PROVIDER env var."""
    with patch.dict(os.environ, {"DEFAULT_LLM_PROVIDER": "claude", "ANTHROPIC_API_KEY": "test-key"}):
        provider = get_provider()
        from app.llm.claude_provider import ClaudeProvider

        assert isinstance(provider, ClaudeProvider)
