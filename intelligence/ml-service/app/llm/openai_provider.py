import os
import base64
from pathlib import Path
from typing import Any

from openai import OpenAI

from .provider import LLMProvider, UnsupportedProviderError


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4o provider."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        if image is not None:
            raise UnsupportedProviderError(
                "Image input is not configured for OpenAI; use the local character verifier"
            )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # openai's SDK types `messages` as a closed union of typed message
        # params rather than a plain `list[dict[str, str]]`; the dicts built
        # above are structurally identical to what the SDK expects at
        # runtime. type: ignore[arg-type] pins this to the upstream
        # openai-python stub strictness, not a first-party typing gap.
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
        )

        # ``message.content`` is ``str | None`` upstream (e.g. a tool-call-only
        # response has no text content). The ``LLMProvider`` interface promises
        # a ``str``, so a missing content is coerced to an empty string rather
        # than leaking ``None`` to callers.
        content = response.choices[0].message.content
        return content if content is not None else ""

    def complete_images(
        self, prompt: str, image_paths: list[str], system: str = "", temperature: float = 0.0
    ) -> tuple[str, dict[str, object]]:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for image_path in image_paths:
            encoded = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}})
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        return result, {
            "inputTokens": getattr(usage, "prompt_tokens", None),
            "outputTokens": getattr(usage, "completion_tokens", None),
            "requestId": getattr(response, "id", None),
        }
