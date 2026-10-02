import os

import google.generativeai as genai

from .provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.0-flash-exp"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        self.model = model
        self._configured = False

    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        # TODO: forward `image` as a Gemini inline image part once wired for vision use;
        # accepted-but-ignored for now so callers can pass it uniformly across providers.
        del image
        if not self._configured:
            # google-generativeai's package __init__ does not declare
            # `configure`/`GenerativeModel` in its public type stubs even
            # though both are documented, supported public API. The ignore
            # below pins this to that upstream deprecated-generative-ai-python
            # stub gap, not a first-party bug.
            genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
            self._configured = True

        client = genai.GenerativeModel(self.model)  # type: ignore[attr-defined]
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = client.generate_content(
            full_prompt, generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
        return str(response.text)
