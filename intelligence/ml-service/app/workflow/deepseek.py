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
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""
