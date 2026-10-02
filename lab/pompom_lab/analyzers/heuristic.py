from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import VisionAnalyzer
from ..frame_analysis import VisualMetrics
from ..models import VideoMetadata


class LocalHeuristicAnalyzer(VisionAnalyzer):
    def analyse(self, video: Path, metadata: VideoMetadata, metrics: VisualMetrics, frame_paths: list[Path]) -> dict[str, Any]:
        return {
            "provider": "local_heuristic",
            "model": "opencv+ffmpeg",
            "confidence": 0.42,
            "goal": "Not semantically verified; enable a local VLM or add human review.",
            "physical_rule": "Not semantically verified; motion metrics cannot identify causal rules.",
            "continuity": "Only abrupt frame-level discontinuities are measured; anatomy/identity require semantic review.",
            "text": "Embedded text meaning is not inferred by the heuristic provider.",
            "raw": {
                "strongest_motion_time": metrics.strongest_motion_time,
                "first_meaningful_change": metrics.first_meaningful_change,
                "action_density": metrics.action_density,
            },
        }

