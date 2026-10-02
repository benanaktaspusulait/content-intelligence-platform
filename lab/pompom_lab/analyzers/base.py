from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..frame_analysis import VisualMetrics
from ..models import VideoMetadata


class VisionAnalyzer(ABC):
    @abstractmethod
    def analyse(self, video: Path, metadata: VideoMetadata, metrics: VisualMetrics, frame_paths: list[Path]) -> dict[str, Any]:
        """Return structured semantic observations with confidence and evidence."""

