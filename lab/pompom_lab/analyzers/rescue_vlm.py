from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class RescueVLMAnalyzer:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def analyse(self, frame_paths: list[Path]) -> dict[str, Any]:
        if not self.model:
            raise RuntimeError("VISION_MODEL is required for local_vlm rescue analysis")
        if len(frame_paths) <= 16:
            selected = frame_paths
        else:
            selected = [frame_paths[round(index * (len(frame_paths) - 1) / 15)] for index in range(16)]
        content: list[dict[str, Any]] = [{"type": "text", "text": _PROMPT}]
        for path in selected:
            timestamp = path.stem.rsplit("_", 1)[-1]
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            content.append({"type": "text", "text": f"Evidence frame at {timestamp}s"})
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}})
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps({"model": self.model, "temperature": 0.1, "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": content}]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read())
            result = json.loads(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Local rescue VLM unavailable or invalid: {exc}") from exc
        result.update({"provider": "local_vlm", "model": self.model})
        return result


_PROMPT = """Review the ENTIRE ordered storyboard of an existing Pompom Hills short. Do not force it into the
physical-anomaly format. Identify its own creative engine from: physical problem, visual anomaly, mystery,
surprise/reveal, character comedy, chase/movement, transformation, impossible scale, emotional/cute moment,
visual search/puzzle, repetition+escalation, narrative continuation, educational discovery, spectacle, or other.
Return JSON only with: confidence (0-1), creative_engines (list), viewer_keeps_watching_because, strongest_visual,
biggest_surprise, funniest_reaction, clearest_anomaly, emotional_frame, strongest_final (each with timestamp and
description), opening_assessment, final_three_seconds, cta_assessment, beats (list of start, end, what_changes,
retention_reason, risk), main_problem, do_not_change (list), alternative_pattern,
reveal_spoiled_by_cold_open (boolean), new_footage_needed (boolean), new_footage_prompt (string or null). Be honest
when an item is not visible. Evaluate CTA contextually rather than assuming it is good or bad. Do not
predict views. Preserve a promising mechanism different from current winners."""
