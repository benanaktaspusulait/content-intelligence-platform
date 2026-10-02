from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import VisionAnalyzer
from ..frame_analysis import VisualMetrics
from ..models import VideoMetadata


class LocalVLMAnalyzer(VisionAnalyzer):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def analyse(self, video: Path, metadata: VideoMetadata, metrics: VisualMetrics, frame_paths: list[Path]) -> dict[str, Any]:
        if not self.model:
            raise RuntimeError("VISION_MODEL is required for local_vlm")
        if len(frame_paths) <= 12:
            selected = frame_paths
        else:
            selected = [frame_paths[round(index * (len(frame_paths) - 1) / 11)] for index in range(12)]
        images = []
        for path in selected:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            timestamp = path.stem.rsplit("_", 1)[-1]
            images.append({"type": "text", "text": f"Evidence frame at {timestamp}s"})
            images.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}})
        prompt = (
            "Analyse this ordered storyboard for Pompom Hills creative structure. Return JSON only with keys "
            "confidence, goal, physical_rule, physical_actions (list with timestamp/evidence), resistance, escalation, "
            "fake_resolution, final_twist, continuity_issues, text_findings. Do not predict views. If uncertain say so. "
            "Each image is preceded by its timestamp."
        )
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}, *images]
        body = json.dumps({"model": self.model, "temperature": 0.1, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": content}]}).encode()
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read())
            result = json.loads(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Local VLM unavailable or returned invalid data: {exc}") from exc
        result.update({"provider": "local_vlm", "model": self.model, "raw": result.copy()})
        return result
