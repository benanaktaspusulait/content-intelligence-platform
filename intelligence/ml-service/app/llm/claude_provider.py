import os

from anthropic import Anthropic

from .provider import LLMProvider


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.model = model
        self.client = Anthropic(api_key=self.api_key)

    def complete(
        self, prompt: str, system: str = "", temperature: float = 0.7, image: str | None = None
    ) -> str:
        # TODO: forward `image` as a Claude vision content block once a vision-capable
        # model is configured for this provider; accepted-but-ignored for now.
        del image
        # anthropic's SDK types `model` as a closed `Literal[...]` of known
        # model names, but this provider accepts an arbitrary configured
        # model string, and `system=""` (not `None`) is the SDK's own
        # documented "no system prompt" sentinel. type: ignore[call-overload]
        # pins this to the upstream anthropic-sdk-python stub strictness,
        # not a first-party typing gap.
        response = self.client.messages.create(  # type: ignore[call-overload]
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        content_block = response.content[0]
        return content_block.text if hasattr(content_block, "text") else str(content_block)
