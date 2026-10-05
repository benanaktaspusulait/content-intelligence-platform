"""Provider-neutral semantic video transport models.

The application layer exchanges these models with a vision provider. Provider SDK
request/response objects must stay inside the adapter implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class SemanticFrame:
    timestamp_seconds: float
    selection_reason: str
    image_path: str
    image_hash: str | None = None
    related_event_id: str | None = None
    related_beat_id: str | None = None


@dataclass(frozen=True)
class SemanticAnalysisRequest:
    asset_hash: str
    duration_seconds: float
    frames: tuple[SemanticFrame, ...]
    known_characters: tuple[str, ...] = ()
    transcript_context: tuple[dict[str, Any], ...] = ()
    planned_creative_context: dict[str, Any] = field(default_factory=dict)
    temporal_events: tuple[dict[str, Any], ...] = ()
    analysis_requirements: str = ""
    request_version: str = "semantic-analysis-request-v1"
    input_strategy: str = "SELECTED_FRAMES"


@dataclass(frozen=True)
class SemanticAnalysisResult:
    payload: dict[str, Any]
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class VisionLanguageModelProvider(Protocol):
    """Small provider boundary used by the semantic application service."""

    def analyze(self, request: SemanticAnalysisRequest) -> SemanticAnalysisResult:
        ...
