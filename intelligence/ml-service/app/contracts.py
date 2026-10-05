from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class VideoAnalysisRequest(BaseModel):
    contract_version: Literal["v1"] = Field(alias="contractVersion")
    relative_path: str = Field(alias="relativePath")
    analysis_version: str = Field("sampled-visual-motion-v5", alias="analysisVersion")
    cached_semantic_video_evidence: dict[str, Any] = Field(default_factory=dict, alias="cachedSemanticVideoEvidence")
    semantic_requested: bool = Field(False, alias="semanticRequested")


class VideoMetadata(BaseModel):
    duration_ms: int = Field(alias="durationMs")
    width: int
    height: int
    fps: float
    aspect_ratio: float = Field(alias="aspectRatio")
    codec: str
    audio_present: bool = Field(alias="audioPresent")
    sha256: str


class VideoAnalysisResponse(BaseModel):
    contract_version: Literal["v1"] = Field("v1", alias="contractVersion")
    metadata: VideoMetadata
    analysis_version: str = Field(alias="analysisVersion")
    analysis_type: str = Field(alias="analysisType")
    primary_engine: str = Field(alias="primaryEngine")
    secondary_engines: list[str] = Field(alias="secondaryEngines")
    classification: str
    motion_heuristic_score: float = Field(alias="motionHeuristicScore")
    measurement_confidence: float | None = Field(None, alias="measurementConfidence")
    measurement_quality: dict[str, Any] = Field(default_factory=dict, alias="measurementQuality")
    reason: str
    storyboard_path: str | None = Field(None, alias="storyboardPath")
    timeline: list[dict[str, Any]]
    features: dict[str, Any]
    evidence: dict[str, Any]
    sampling: dict[str, Any] = Field(default_factory=dict)
    motion: dict[str, Any] = Field(default_factory=dict)
    visual_similarity: dict[str, Any] = Field(default_factory=dict, alias="visualSimilarity")
    dark_frame_candidates: list[dict[str, Any]] = Field(default_factory=list, alias="darkFrameCandidates")
    semantic_video_evidence: dict[str, Any] = Field(default_factory=dict, alias="semanticVideoEvidence")


class PredictionRequest(BaseModel):
    contract_version: Literal["v1"] = Field(alias="contractVersion")
    platform: Literal["instagram", "facebook", "tiktok", "youtube"]
    fingerprint: dict[str, Any]
    knowledge_cutoff: datetime = Field(alias="knowledgeCutoff")


class LivePredictionRequest(PredictionRequest):
    live_features: dict[str, Any] = Field(alias="liveFeatures")


class ReachFurtherEvaluationRequest(BaseModel):
    contract_version: Literal["v1"] = Field(alias="contractVersion")
    platform: Literal["instagram", "facebook", "tiktok"]
    rows: list[dict[str, Any]]


class PredictionResponse(BaseModel):
    contract_version: Literal["v1"] = Field("v1", alias="contractVersion")
    model_version: str = Field(alias="modelVersion")
    dataset_version: str = Field(alias="datasetVersion")
    feature_version: str = Field(alias="featureVersion")
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    comparable_sample_size: int = Field(alias="comparableSampleSize")
    payload: dict[str, Any]


class TrainingRequest(BaseModel):
    contract_version: Literal["v1"] = Field(alias="contractVersion")
    platform: Literal["instagram", "facebook", "tiktok"]
    dataset_version: str = Field(alias="datasetVersion")
    rows: list[dict[str, Any]]
