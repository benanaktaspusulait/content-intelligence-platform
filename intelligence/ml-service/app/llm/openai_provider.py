import os

from openai import OpenAI

from .provider import LLMProvider


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
        # TODO: forward `image` as an OpenAI vision content part once a vision-capable
        # model is configured for this provider; accepted-but-ignored for now so callers
        # like CharacterVerifier can pass it uniformly across providers.
        del image
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
