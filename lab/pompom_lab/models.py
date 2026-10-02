from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

Classification = Literal["BAD", "AVERAGE/FIXABLE", "GOOD", "WINNER CANDIDATE"]
RescueClassification = Literal["A", "B", "C", "D", "E"]


@dataclass(slots=True)
class VideoMetadata:
    path: str
    filename: str
    series: str
    duration: float
    fps: float
    width: int
    height: int
    aspect_ratio: float
    codec: str
    has_audio: bool
    audio_codec: str | None
    size_bytes: int
    content_hash: str


@dataclass(slots=True)
class Evidence:
    start: float
    end: float
    kind: str
    detail: str
    value: float | None = None
    confidence: float = 1.0


@dataclass(slots=True)
class Issue:
    code: str
    severity: Literal["info", "warning", "fatal"]
    start: float
    end: float
    evidence: str
    consequence: str
    proposed_change: str
    auto_fixable: bool = False


@dataclass(slots=True)
class FixOperation:
    operation: str
    start: float | None = None
    end: float | None = None
    source_time: float | None = None
    duration: float | None = None
    reason: str = ""


@dataclass(slots=True)
class AnalysisResult:
    video_id: str
    metadata: VideoMetadata
    classification: Classification
    classification_reason: str
    diagnosis: str
    creative_structure_match: float
    confidence: float
    scores: dict[str, float]
    timeline: list[Evidence] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    physical_actions: list[Evidence] = field(default_factory=list)
    dead_time: list[Evidence] = field(default_factory=list)
    continuity_findings: list[Issue] = field(default_factory=list)
    text_findings: list[Issue] = field(default_factory=list)
    audio_findings: list[Evidence] = field(default_factory=list)
    fix_plan: list[FixOperation] = field(default_factory=list)
    semantic_notes: dict[str, Any] = field(default_factory=dict)
    provider: str = "local_heuristic"
    model: str = "opencv+ffmpeg"
    prompt_version: str = "heuristic-v1"
    rubric_version: str = "pompom-action-dna-v1"
    software_version: str = "0.1.0"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisArtifacts:
    root: Path
    frames_dir: Path
    storyboard: Path
    analysis_json: Path
    report_md: Path
    timeline_json: Path
    fix_json: Path
    fix_md: Path


@dataclass(slots=True)
class RescueBeat:
    start: float
    end: float
    what_changes: str
    retention_reason: str
    risk: bool = False


@dataclass(slots=True)
class RescueMoment:
    kind: str
    timestamp: float | None
    description: str
    confidence: float


@dataclass(slots=True)
class RescueEdit:
    variant: Literal["minimal", "cold_open"]
    operation: str
    start: float | None = None
    end: float | None = None
    source_start: float | None = None
    source_end: float | None = None
    reason: str = ""
    semantic_risk: bool = False


@dataclass(slots=True)
class RescueResult:
    video_id: str
    filename: str
    classification: RescueClassification
    classification_label: str
    classification_reason: str
    creative_engine: list[str]
    core_viewer_question: str
    hook_score: float
    ending_score: float
    best_moments: list[RescueMoment]
    main_problem: str
    do_not_change: list[str]
    fix_first: list[RescueEdit]
    optional_experiment: str
    alternative_pattern: str
    opening_comparison: str
    final_three_seconds: str
    cta_assessment: str
    new_footage_needed: bool
    new_footage_prompt: str | None
    publishing_use: str
    confidence: float
    beats: list[RescueBeat]
    provider: str
    model: str
    prompt_version: str = "stock-creative-rescue-v1"
    software_version: str = "0.2.0"
    performance_override: bool = False
    observed_performance_note: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
