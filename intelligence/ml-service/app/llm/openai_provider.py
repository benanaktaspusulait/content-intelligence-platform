import os
import base64
import json
from pathlib import Path
from typing import Any

from openai import OpenAI

from .provider import LLMProvider, UnsupportedProviderError
from ..semantic_provider import SemanticAnalysisRequest, SemanticAnalysisResult


class OpenAIProvider(LLMProvider):
    """OpenAI adapter; provider-neutral semantic code never sees these SDK types."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = model
        timeout_seconds = float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "20"))
        self.client = OpenAI(api_key=self.api_key, timeout=timeout_seconds, max_retries=0)

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
            **({"max_tokens": self.max_output_tokens} if hasattr(self, "max_output_tokens") else {}),
        )

        # ``message.content`` is ``str | None`` upstream (e.g. a tool-call-only
        # response has no text content). The ``LLMProvider`` interface promises
        # a ``str``, so a missing content is coerced to an empty string rather
        # than leaking ``None`` to callers.
        usage = getattr(response, "usage", None)
        self.last_usage = usage.model_dump() if usage is not None and hasattr(usage, "model_dump") else None
        content = response.choices[0].message.content
        return content if content is not None else ""

    def complete_images(
        self, prompt: str, image_paths: list[str], system: str = "", temperature: float = 0.0
    ) -> tuple[str, dict[str, object]]:
        # Compatibility entry point for existing generic callers. The semantic
        # application uses analyze() below, which carries timestamps/context.
        result = self._responses_json(prompt, image_paths, system)
        return result[0], result[1]

    def analyze(self, request: SemanticAnalysisRequest) -> SemanticAnalysisResult:
        context = {
            "requestVersion": request.request_version,
            "inputStrategy": request.input_strategy,
            "assetHash": request.asset_hash,
            "durationSeconds": request.duration_seconds,
            "knownCharacters": list(request.known_characters),
            "transcriptContext": list(request.transcript_context),
            "plannedCreativeContext": request.planned_creative_context,
            "temporalEvents": list(request.temporal_events),
            "frames": [
                {"timestampSeconds": frame.timestamp_seconds, "selectionReason": frame.selection_reason,
                 "relatedEventId": frame.related_event_id, "relatedBeatId": frame.related_beat_id}
                for frame in request.frames
            ],
        }
        prompt = "Analyze only the supplied selected frames and structured context. Return the requested semantic evidence JSON.\n" + json.dumps(context, separators=(",", ":"))
        if request.analysis_requirements:
            prompt += "\nSchema requirements:\n" + request.analysis_requirements
        result, usage = self._responses_json(
            prompt,
            [frame.image_path for frame in request.frames],
            "Return only provider-neutral JSON evidence. Do not judge quality or predict performance. Use UNKNOWN when evidence is insufficient.",
        )
        try:
            payload = json.loads(result)
        except json.JSONDecodeError as error:
            raise ValueError("OpenAI semantic response was not valid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("OpenAI semantic response must be an object")
        return SemanticAnalysisResult(payload=payload, provider="openai", model=self.model, usage=usage)

    def _responses_json(self, prompt: str, image_paths: list[str], system: str) -> tuple[str, dict[str, object]]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        for image_path in image_paths:
            encoded = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
            content.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{encoded}"})
        inputs: list[dict[str, Any]] = []
        if system:
            inputs.append({"role": "system", "content": [{"type": "input_text", "text": system}]})
        inputs.append({"role": "user", "content": content})
        response = self.client.responses.create(
            model=self.model,
            input=inputs,
            text={"format": {"type": "json_object"}},
        )
        result = getattr(response, "output_text", None) or ""
        usage = getattr(response, "usage", None)
        return result, {
            "inputTokens": getattr(usage, "input_tokens", None) or getattr(usage, "prompt_tokens", None),
            "outputTokens": getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None),
            "requestId": getattr(response, "id", None),
        }
