from pathlib import Path
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .api.quality import router as quality_router
from .workflow.api import router as workflow_router
from .config import settings
from .contracts import (
    LivePredictionRequest,
    PredictionRequest,
    PredictionResponse,
    ReachFurtherEvaluationRequest,
    TrainingRequest,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
)
from .prediction import live, prepublish
from .retention_assessment import RetentionAssessmentRequest, assess
from .qa.character_verifier import CharacterVerifier
from .qa.dead_air_analyzer import DeadAirAnalyzer
from .rules.rule_versioning import RulesetConfigurationError, RuleVersionManager
from .video import analyse
from .semantic_fusion import fuse_canonical_assessments
from .semantic_evidence import analyse_semantic_video

app = FastAPI(title="Pompom Creative Intelligence ML", version="0.1.0")

# Quality engine endpoints are mounted once under a single prefix.
app.include_router(quality_router, prefix="/api/v1/quality")
app.include_router(workflow_router)

# Initialize only analyzers that do not require optional external services.
dead_air_analyzer = DeadAirAnalyzer()
_character_verifier: CharacterVerifier | None = None


def get_character_verifier() -> CharacterVerifier:
    global _character_verifier
    if _character_verifier is None:
        try:
            _character_verifier = CharacterVerifier()
        except ValueError as error:
            raise HTTPException(
                status_code=503,
                detail="Character identity verification is not configured",
            ) from error
    return _character_verifier


# QA Request/Response models
class DeadAirRequest(BaseModel):
    video_path: str


class DeadAirSegment(BaseModel):
    start_ms: int
    end_ms: int
    duration: float


class DeadAirResponse(BaseModel):
    has_dead_air: bool
    dead_air_segments: list[DeadAirSegment]
    total_dead_air_duration_ms: int
    segment_count: int


class CharacterIdentityRequest(BaseModel):
    video_path: str
    expected_character: str
    reference_image_path: str | None = None


class CharacterIdentityResponse(BaseModel):
    character_identity_verified: bool
    confidence: float
    character_identity_issues: str | None
    reasoning: str


class SemanticFusionRequest(BaseModel):
    temporal_profile: dict[str, object]
    semantic_video_evidence: dict[str, object]


class SemanticReplayRequest(BaseModel):
    """Exact-frame semantic replay input; available only in an explicitly enabled test runtime."""

    asset_hash: str
    frame_selection: dict[str, object]
    canonical_characters: list[str] = []
    replay_index: int


SEMANTIC_REPLAY_ASSET_HASH = "fcba5934179363b02b063083dd075a3b7c2d66db69e9167773fbf704cd5e9816"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP", "service": "pompom-ml"}


@app.get("/health/ready")
def readiness() -> JSONResponse:
    """Readiness probe.

    Reports ``503`` when the active ruleset cannot be loaded from the
    configured data root (e.g. the rules directory or ``versions.yaml`` is
    absent). This is a read-only check and never provisions files on disk.
    """
    try:
        manager = RuleVersionManager(settings.rules_dir)
        latest = manager.get_latest_version()
    except (RulesetConfigurationError, ValueError, OSError) as error:
        return JSONResponse(
            status_code=503,
            content={"status": "DOWN", "detail": str(error)},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "UP", "ruleset_version": latest},
    )


@app.post("/v1/analysis/video", response_model=VideoAnalysisResponse, response_model_by_alias=True)
def analyse_video(request: VideoAnalysisRequest) -> VideoAnalysisResponse:
    try:
        return analyse(request.relative_path, request.analysis_version, request.cached_semantic_video_evidence, request.semantic_requested)
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/v1/analysis/semantic-fusion")
def fuse_semantic_evidence(request: SemanticFusionRequest) -> dict[str, object]:
    """Recompute canonical assessments from persisted evidence only.

    This endpoint is intentionally local/deterministic and never invokes a VLM.
    It lets historical semantic rows receive the current fusion projection.
    """
    return fuse_canonical_assessments(request.temporal_profile, request.semantic_video_evidence)


@app.post("/v1/test/semantic-replay")
def semantic_replay(request: SemanticReplayRequest) -> dict[str, object]:
    """Run one exact-input semantic replay; never enabled in normal production mode."""
    if os.getenv("SEMANTIC_REPLAY_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Semantic replay is disabled")
    if request.asset_hash != SEMANTIC_REPLAY_ASSET_HASH:
        raise HTTPException(status_code=403, detail="Replay is restricted to the audited Hıçkıran Kutu asset")
    if request.replay_index not in {1, 2, 3}:
        raise HTTPException(status_code=400, detail="replay_index must be 1, 2, or 3")
    selection = dict(request.frame_selection)
    if str(selection.get("assetHash") or "") != request.asset_hash:
        raise HTTPException(status_code=400, detail="Frame manifest asset hash does not match replay asset")
    result = analyse_semantic_video(
        selection,
        canonical_characters=request.canonical_characters,
        cached_evidence={},
        semantic_requested=True,
        bypass_cache=True,
        allow_fallback=False,
    )
    result.setdefault("provenance", {})["replayIndex"] = request.replay_index
    result["provenance"]["replayMode"] = "EXACT_PERSISTED_FRAME_MANIFEST"
    return result


@app.post("/v1/analysis/retention")
def assess_retention(request: RetentionAssessmentRequest) -> dict[str, object]:
    """Return the strict short-form retention assessment from supplied evidence."""
    return assess(request)


@app.post("/v1/prediction/prepublish", response_model=PredictionResponse, response_model_by_alias=True)
def predict_prepublish(request: PredictionRequest) -> PredictionResponse:
    try:
        return prepublish(request)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


@app.post("/v1/prediction/live", response_model=PredictionResponse, response_model_by_alias=True)
def predict_live(request: LivePredictionRequest) -> PredictionResponse:
    return live(request)


@app.post("/v1/evaluation/reach-further-ablation")
def reach_further_ablation(request: ReachFurtherEvaluationRequest) -> dict[str, object]:
    eligible = len(request.rows) >= 30
    return {
        "method": "TEMPORAL_WALK_FORWARD",
        "platform": request.platform,
        "sampleSize": len(request.rows),
        "eligible": eligible,
        "modelA": {"features": "live-signals-without-reach-further", "metrics": None},
        "modelB": {"features": "live-signals-with-reach-further", "metrics": None},
        "decision": "RUN_BACKTEST" if eligible else "INSUFFICIENT_SAMPLE",
        "notice": "Keep Reach Further only if temporal validation improves forecast accuracy or calibration.",
    }


@app.post("/v1/training/train")
def train(request: TrainingRequest) -> dict[str, object]:
    if len(request.rows) < 30:
        raise HTTPException(
            status_code=409, detail="At least 30 completed historical videos are required for a challenger"
        )
    from .statistical_model import fit
    try:
        return fit(request)
    except ValueError as error:
        raise HTTPException(409, detail={"status":"TRAINING_DATA_INELIGIBLE","artifactCreated":False,"reason":str(error)}) from error


@app.post("/v1/training/verify-artifact")
def verify_artifact(request: dict[str, object]) -> dict[str, object]:
    from .statistical_model import load
    try:
        model=load(request, str(request.get("platform")))
        return {"verified":True, "artifactSha256":request["artifactSha256"], "featureVersion":model["featureVersion"], "promotionEligible":model["metrics"]["promotionEligible"], "pipelineVersion":model["pipelineVersion"], "knowledgeCutoff":model["knowledgeCutoff"]}
    except (ValueError,KeyError,TypeError) as error:
        raise HTTPException(409, str(error)) from error



@app.post("/v1/evaluation/backtest")
def backtest(request: TrainingRequest) -> dict[str, object]:
    from .statistical_model import fit
    try:
        return fit(request,persist=False)
    except ValueError as error:
        raise HTTPException(409,str(error)) from error



@app.post("/api/v1/qa/dead-air", response_model=DeadAirResponse)
def analyze_dead_air(request: DeadAirRequest) -> DeadAirResponse:
    """
    Analyze video for dead air (silence segments).

    Uses FFmpeg silencedetect filter to identify segments with >2s of silence.
    """
    video_path = Path(request.video_path)

    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {request.video_path}")

    try:
        result = dead_air_analyzer.analyze(video_path)

        # `analyze` returns dict[str, object] (the segment list elements are
        # themselves dicts, which object-typed values do not expose), so
        # narrow the two heterogeneous fields explicitly before use.
        raw_segments = result["dead_air_segments"]
        duration_ms = result["total_dead_air_duration_ms"]
        segment_count = result["segment_count"]
        assert isinstance(raw_segments, list)
        assert isinstance(duration_ms, int)
        assert isinstance(segment_count, int)
        segments = [DeadAirSegment(**seg) for seg in raw_segments]

        return DeadAirResponse(
            has_dead_air=bool(result["has_dead_air"]),
            dead_air_segments=segments,
            total_dead_air_duration_ms=duration_ms,
            segment_count=segment_count,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/v1/qa/character-identity", response_model=CharacterIdentityResponse)
def verify_character_identity(request: CharacterIdentityRequest) -> CharacterIdentityResponse:
    """
    Verify character identity in video using vision LLM.

    Extracts first frame and uses GPT-4V to verify the expected character is present
    and matches the design specifications.
    """
    video_path = Path(request.video_path)

    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found: {request.video_path}")

    reference_path = Path(request.reference_image_path) if request.reference_image_path else None

    try:
        result = get_character_verifier().verify(video_path, request.expected_character, reference_path)

        return CharacterIdentityResponse(**result)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"LLM response parsing failed: {e}") from e
