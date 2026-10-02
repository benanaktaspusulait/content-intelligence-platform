import os
from typing import Any

import requests

from .provider import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""

    def __init__(self, base_url: str | None = None, model: str = "llama3.2:latest"):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model

    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        # TODO: forward `image` once this provider targets a vision-capable local model;
        # accepted-but-ignored for now so callers can pass it uniformly across providers.
        del image
        url = f"{self.base_url}/api/generate"
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        result: dict[str, Any] = response.json()
        return str(result["response"])
