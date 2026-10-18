import os
import base64
import json
import uuid
import time
import re

import httpx
from openai import APITimeoutError, APIConnectionError, APIStatusError
from pathlib import Path
from typing import Any

from openai import OpenAI, Timeout

from .provider import LLMProvider, UnsupportedProviderError
from ..semantic_provider import SemanticAnalysisRequest, SemanticAnalysisResult


def safe_provider_error(error: Exception, elapsed_seconds: float) -> dict:
    """Allowlisted diagnostics only: never retain request bodies/headers or credentials."""
    if isinstance(error, (APITimeoutError, httpx.TimeoutException, TimeoutError)):
        failure = "SDK_TIMEOUT"
    elif isinstance(error, (APIConnectionError, httpx.NetworkError, ConnectionError)):
        failure = "NETWORK_CONNECTION_FAILURE"
    elif isinstance(error, APIStatusError):
        failure = "HTTP_STATUS_ERROR"
    else:
        failure = "UNKNOWN_TRANSPORT_FAILURE"
    # HTTP error strings may contain arbitrary response bodies and private input.
    # Preserve SDK-standard safe text; unknown messages are deliberately withheld.
    message = str(error)
    safe_messages = {"Request timed out.", "Connection error."}
    detail = message if message in safe_messages else type(error).__name__ + ": message withheld (may contain private request data)"
    status = getattr(error, "status_code", None)
    request_id = getattr(error, "request_id", None)
    response = getattr(error, "response", None)
    if response is not None:
        request_id = request_id or response.headers.get("x-request-id")
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,512}", request_id):
        request_id = None
    causes = []
    cause = error.__cause__
    while cause is not None and len(causes) < 4:
        causes.append(type(cause).__name__)
        cause = cause.__cause__
    return {"category": type(error).__name__, "detail": detail, "failureClass": failure,
            "causeType": causes[0] if causes else None, "causeChainTypes": causes,
            "httpStatus": status if isinstance(status, int) else None,
            "providerHttpRequestId": request_id, "elapsedSeconds": round(elapsed_seconds, 6)}


def _resolve_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """Resolve aspect ratio string to (width, height) for GPT Image 2.
    
    GPT Image 2 supports various aspect ratios via the 'prompt' parameter.
    Returns dimensions suitable for the target model.
    """
    ratio_map = {
        "9:16": (1024, 1792),
        "16:9": (1792, 1024),
        "1:1": (1024, 1024),
        "4:3": (1536, 1024),
        "3:4": (1024, 1536),
    }
    return ratio_map.get(aspect_ratio, (1024, 1024))


class OpenAIProvider(LLMProvider):
    """OpenAI adapter; provider-neutral semantic code never sees these SDK types."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o", request_timeout: Timeout | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.model = model
        timeout_seconds = float(os.getenv("OPENAI_REQUEST_TIMEOUT_SECONDS", "20"))
        self.client = OpenAI(api_key=self.api_key, timeout=request_timeout if request_timeout is not None else timeout_seconds, max_retries=0)

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
        client_id = getattr(self, "client_request_id", None)
        if client_id is not None and (not isinstance(client_id, str) or not re.fullmatch(r"[\x21-\x7e]{1,512}", client_id)):
            raise ValueError("Client request ID must be 1-512 printable ASCII characters")
        self.last_request_started = True
        started = time.monotonic()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                **({"extra_headers": {"X-Client-Request-Id": client_id}} if client_id else {}),
                **({"max_tokens": self.max_output_tokens} if hasattr(self, "max_output_tokens") else {}),
                **({"response_format": self.response_format} if hasattr(self, "response_format") else
                   {"response_format": {"type": "json_object"}} if getattr(self, "json_output", False) else {}),
            )
        except Exception as error:
            self.last_error = safe_provider_error(error, time.monotonic() - started)
            raise

        # ``message.content`` is ``str | None`` upstream (e.g. a tool-call-only
        # response has no text content). The ``LLMProvider`` interface promises
        # a ``str``, so a missing content is coerced to an empty string rather
        # than leaking ``None`` to callers.
        self.last_provider_response = response.model_dump() if hasattr(response, "model_dump") else None
        usage = getattr(response, "usage", None)
        self.last_usage = usage.model_dump() if usage is not None and hasattr(usage, "model_dump") else None
        choices = getattr(response, "choices", None)
        choice = choices[0] if choices else None
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        self.last_response_metadata = {
            "httpRequestId": getattr(response, "_request_id", None),
            "clientRequestId": client_id,
            "elapsedSeconds": round(time.monotonic() - started, 6),
            "model": getattr(response, "model", None),
            "requestId": getattr(response, "id", None),
            "finishReason": getattr(choice, "finish_reason", None),
            "refusal": getattr(message, "refusal", None),
            "promptPresent": bool(content and content.strip()),
            "promptLength": len(content or ""),
            "apiStatus": "COMPLETED",
        }
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

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        model: str | None = None,
        quality: str = "medium",
        reference_image_paths: list[str] | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        """Generate an image using GPT Image 2 with optional character reference images.

        Uses client.images.edit() when reference images are provided (image-to-image),
        or client.images.generate() for text-only generation.

        Args:
            prompt: Text description of the desired image
            aspect_ratio: Target aspect ratio (e.g., "9:16")
            model: Model name (defaults to GPT_IMAGE_MODEL env var or "gpt-image-2")
            quality: Quality level - "low", "medium", or "high"
            reference_image_paths: Paths to reference images for character consistency
            output_dir: Directory to save the generated image

        Returns a dict with:
        - image_path: path to the saved image file
        - image_url: URL of the generated image (from OpenAI)
        - sha256: SHA-256 hash of the saved image bytes
        - width, height: actual image dimensions
        - requestId: OpenAI request ID
        - model: model used
        - prompt: the prompt sent to the provider
        - referenceImages: count of reference images used
        """
        import hashlib
        import urllib.request

        model = model or os.getenv("GPT_IMAGE_MODEL", "gpt-image-2")
        dimensions = _resolve_dimensions(aspect_ratio)
        size = f"{dimensions[0]}x{dimensions[1]}"

        # Open the reference image file handles for images.edit()
        image_files = None
        if reference_image_paths:
            image_files = [open(p, "rb") for p in reference_image_paths]

        try:
            if image_files:
                # Image-to-image: use images.edit with reference image(s)
                response = self.client.images.edit(
                    model=model,
                    image=image_files,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=1,
                    response_format="url",
                )
            else:
                # Text-only: use images.generate
                response = self.client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    n=1,
                    response_format="url",
                )

            image_url = response.data[0].url
            request_id = getattr(response, "id", None)

        finally:
            if image_files:
                for fh in image_files:
                    fh.close()

        # Download and save the image
        if output_dir is None:
            output_dir = os.getenv("IMAGE_OUTPUT_DIR", "/tmp/pompom-images")

        os.makedirs(output_dir, exist_ok=True)
        filename = f"start-frame-{uuid.uuid4().hex}.png"
        image_path = os.path.join(output_dir, filename)

        # Download image
        urllib.request.urlretrieve(image_url, image_path)

        # Calculate SHA-256 and get actual dimensions
        image_bytes = Path(image_path).read_bytes()
        sha256 = hashlib.sha256(image_bytes).hexdigest()

        # Try to get actual dimensions from the image file
        actual_width, actual_height = dimensions  # fallback to requested
        try:
            import struct
            if image_bytes[:4] == b'\x89PNG':
                # PNG: width/height at offset 16-23
                actual_width = struct.unpack('>I', image_bytes[16:20])[0]
                actual_height = struct.unpack('>I', image_bytes[20:24])[0]
            elif image_bytes[:2] == b'\xff\xd8':
                # JPEG: parse SOF marker
                i = 2
                while i < len(image_bytes) - 1:
                    if image_bytes[i] == 0xFF:
                        marker = image_bytes[i + 1]
                        if marker in (0xC0, 0xC1, 0xC2):
                            actual_height = struct.unpack('>H', image_bytes[i+5:i+7])[0]
                            actual_width = struct.unpack('>H', image_bytes[i+7:i+9])[0]
                            break
                        length = struct.unpack('>H', image_bytes[i+2:i+4])[0]
                        i += 2 + length
                    else:
                        i += 1
        except Exception:
            pass  # keep fallback dimensions

        return {
            "image_path": image_path,
            "image_url": image_url,
            "sha256": sha256,
            "width": actual_width,
            "height": actual_height,
            "requestId": request_id,
            "model": model,
            "prompt": prompt,
            "referenceImages": len(reference_image_paths) if reference_image_paths else 0,
        }
