"""Explicitly configured text-only second opinion; no implicit modality upgrade."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from app.llm.provider import LLMProvider, UnsupportedProviderError


class DeepSeekTextProvider(LLMProvider):
    def __init__(self, model: str):
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key or not model:
            raise ValueError("DeepSeek server credentials and explicit critic model are required")
        self.model = model
        # DeepSeek reasoning models spend part of the completion budget on
        # hidden reasoning. A 2k cap can therefore finish with no visible JSON
        # even when the request itself is valid.
        self.max_output_tokens = 4000
        self.client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=20, max_retries=0)

    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        if image is not None:
            raise UnsupportedProviderError(
                "This critic adapter is text-only; no visual evidence was inspected"
            )
        messages: Any = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
            max_tokens=self.max_output_tokens,
        )
        usage = getattr(response, "usage", None)
        self.last_usage = usage.model_dump() if usage is not None and hasattr(usage, "model_dump") else None
        return response.choices[0].message.content or ""
