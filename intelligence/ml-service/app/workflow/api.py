"""No-credit local endpoints for the explicitly selected operational profile."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings

from .feedback import compare_cohort, match_publication, measure_observation, review_render
from .repair import repair_prompt
from .review import review_prompt
from .start_frame_generation import generate_start_frame

router = APIRouter(prefix="/api/v1/workflow", tags=["post-family-workflow"])
logger = logging.getLogger(__name__)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=50000)
    sourceId: str
    sourceVersion: str
    profile: Literal["post-family-v1"]
    contentProfile: Literal[
        "AUTO", "ABSURD_PHYSICS", "CURIOSITY_ADVENTURE", "EDUCATIONAL", "MIXED", "UNKNOWN"
    ] = "AUTO"
    openingStrategy: Literal["AUTO", "INSTANT_IMPOSSIBLE", "IMMEDIATE_PROBLEM", "CURIOSITY_DISCOVERY"] = (
        "AUTO"
    )
    desiredDuration: float | None = Field(None, gt=0, le=600)
    plannedEditedDuration: float | None = Field(None, gt=0, le=600)
    generator: Literal["AUTO", "SEEDANCE_2_0_MINI", "SEEDANCE_2_0", "SEEDANCE_2_5"] = "AUTO"
    qualityJustification: str = ""
    viewerQuestion: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)
    references: list[dict[str, Any]] = Field(default_factory=list)
    segments: list[dict[str, Any]] = Field(default_factory=list)
    protectedIntent: list[str] = Field(default_factory=list)
    intentRequirements: list[dict[str, Any]] = Field(default_factory=list)
    creativeEvidence: list[dict[str, Any]] = Field(default_factory=list)
    intentChangeReason: str = ""
    lessonModelVersion: str = ""
    retrievedLessons: list[dict[str, Any]] = Field(default_factory=list)
    structuredPlan: dict[str, Any] | None = None
    canonicalValidationId: int | None = None
    authorizationEvidence: dict[str, Any] = Field(default_factory=dict)
    acceptedStartFrame: bool = False


def capabilities() -> dict[str, Any]:
    path = settings.data_root / "workflow/provider-capabilities.json"
    return dict(json.loads(path.read_text())["models"]) if path.is_file() else {}


@router.post("/review")
def review(request: ReviewRequest) -> dict[str, Any]:
    return review_prompt(request.model_dump(), capabilities())


class SourcePlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=50000)
    sourceId: str
    sourceVersion: str


@router.post("/source-plan")
def source_plan(request: SourcePlanRequest) -> dict[str, Any]:
    from app.parser.prompt_parser import source_plan_evidence
    return source_plan_evidence(request.prompt, request.sourceId, request.sourceVersion)


class RepairRequest(BaseModel):
    request: ReviewRequest
    patches: list[dict[str, Any]]
    repairPasses: int = Field(0, ge=0, le=1)


@router.post("/repair")
def repair(request: RepairRequest) -> dict[str, Any]:
    try:
        if any("sourceQuote" not in patch for patch in request.patches):
            raise ValueError("Every API patch requires its exact source quote")
        return repair_prompt(
            {**request.request.model_dump(), "repairPasses": request.repairPasses},
            request.patches,
            capabilities(),
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error


class FeedbackRequest(BaseModel):
    kind: Literal["ACTUAL_RENDER_QA", "MEASUREMENT", "ASSOCIATION", "COHORT"]
    payload: dict[str, Any]


@router.post("/feedback")
def feedback(request: FeedbackRequest) -> dict[str, Any]:
    value = request.payload
    try:
        if request.kind == "ACTUAL_RENDER_QA":
            return review_render(value["plan"], value["observation"])
        if request.kind == "MEASUREMENT":
            return measure_observation(value["observation"], value.get("nearOrganicThreshold", 0.05))
        if request.kind == "COHORT":
            return compare_cohort(value["records"], value["horizon"], value.get("nearOrganicThreshold", 0.05))
        return match_publication(value["platform"], value["platformContentId"], value["associations"])
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(400, str(error)) from error


class CriticRequest(BaseModel):
    request: ReviewRequest
    provider: str
    model: str


@router.post("/critic")
def critic(request: CriticRequest) -> dict[str, Any]:
    import os

    if os.getenv("WORKFLOW_PAID_CRITIC_ENABLED", "false").lower() != "true":
        raise HTTPException(403, "Paid critic execution is disabled; explicit approved scope/budget required")
    from app.llm.provider import get_provider

    from .critic import ProviderExecutionCritic
    from .deepseek import DeepSeekTextProvider

    value = request.request.model_dump()
    reviewed = review_prompt(value, capabilities())
    try:
        if request.provider not in {"deepseek", "openai"}:
            raise ValueError("A bounded timeout/no-retry runtime adapter is not configured for this provider")
        provider = (
            DeepSeekTextProvider(request.model)
            if request.provider == "deepseek"
            else get_provider(request.provider, request.model)
        )
        if request.provider == "openai":
            provider.client = provider.client.with_options(timeout=20, max_retries=0)  # type: ignore[attr-defined]
        opinion = ProviderExecutionCritic(provider, request.provider, request.model).review(
            value, reviewed["productionEvidence"], reviewed["generation"]
        )
    except Exception:
        opinion = {
            "status": "UNKNOWN",
            "technicalStatus": "CRITIC_CONFIGURATION_UNAVAILABLE",
            "visualInspected": False,
            "calls": 0,
        }
    return {"bindingHash": reviewed["bindingHash"], "secondOpinion": opinion, "canonicalReview": reviewed}


class CreativeRoleRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['STORY', 'STORY_REVIEW', 'BUILD_PROMPT', 'MINIMAL_REPAIR', 'PROMPT_OPTIMIZATION']
    text: str = Field(min_length=1, max_length=16000)
    context: dict[str, Any] = Field(default_factory=dict)
    maxCostUsd: float = Field(gt=0, le=20)


class LegacyProductionSpecMigrationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    prompt: str = Field(min_length=1, max_length=50000)
    approvedStory: str = Field(default='', max_length=16000)
    context: dict[str, Any] = Field(default_factory=dict)


@router.get('/creative-role/readiness')
@router.post('/creative-role/readiness')
def creative_role_readiness() -> dict[str, Any]:
    from .creative_roles import role_readiness
    return role_readiness()


@router.post('/creative-role')
def creative_role(request: CreativeRoleRequest) -> dict[str, Any]:
    from .creative_roles import CreativeRoleFailure, run_paid_role
    attempt_id = str(request.context.get('attemptId') or 'unassigned')
    try:
        result = run_paid_role(request.role, request.text, request.context, request.maxCostUsd)
        logger.info(
            "Creative role completed role=%s attempt_id=%s provider=%s model=%s provider_request_id=%s",
            request.role, attempt_id, result.get('provider'), result.get('model'),
            (result.get('providerResponseMetadata') or {}).get('requestId', 'unavailable'),
        )
        return result
    except CreativeRoleFailure as error:
        detail = {'detail': str(error), **error.diagnostics, 'attemptId': attempt_id}
        status_code = 502 if error.diagnostics.get('category') in {
            'PROVIDER_CONNECTION_ERROR', 'PROVIDER_TIMEOUT', 'PROVIDER_OUTCOME_UNKNOWN'
        } else 409
        raise HTTPException(status_code, detail) from error
    except (ValueError, json.JSONDecodeError) as error:
        message = str(error)
        category = (
            'CONFIGURATION_ERROR' if 'configuration' in message.lower() or 'api key' in message.lower()
            else 'SOURCE_PLAN_VALIDATION_FAILED' if 'source-plan' in message.lower()
            else 'COST_CEILING_EXCEEDED' if 'budget' in message.lower() or 'cost ceiling' in message.lower()
            else 'CANDIDATE_STRUCTURE_INVALID' if request.role == 'PROMPT_OPTIMIZATION'
            else 'REQUEST_VALIDATION_ERROR'
        )
        detail = {
            'detail': message,
            'category': category,
            'attemptId': attempt_id,
            'providerDispatched': False,
            'providerResponseReturned': False,
            'candidatesSaved': False,
            'retrySafe': True,
            'retryRequiresOperatorAuthorization': True,
        }
        logger.warning("Creative role pre-dispatch rejection role=%s attempt_id=%s category=%s", request.role, attempt_id, category)
        raise HTTPException(409, detail) from error
    except Exception as error:
        logger.error("Creative role outcome unknown role=%s attempt_id=%s exception_type=%s", request.role, attempt_id, type(error).__name__)
        raise HTTPException(502, {
            'detail': 'The provider request outcome is unknown; do not retry automatically.',
            'category': 'PROVIDER_OUTCOME_UNKNOWN',
            'attemptId': attempt_id,
            'providerDispatched': True,
            'providerResponseReturned': False,
            'candidatesSaved': False,
            'retrySafe': False,
            'retryRequiresOperatorAuthorization': True,
        }) from error


@router.post('/creative-role/revalidate-production-spec')
def revalidate_production_spec(request: LegacyProductionSpecMigrationRequest) -> dict[str, Any]:
    """Local deterministic migration. This route never obtains a provider adapter."""
    from .creative_roles import migrate_legacy_production_spec
    context = dict(request.context)
    context['generatorCapabilities'] = capabilities().get(
        str((context.get('targetConfiguration') or {}).get('selectedGenerator') or ''),
        {'status': 'UNKNOWN', 'source': 'provider-capabilities.json has no selected generator'},
    )
    try:
        return migrate_legacy_production_spec(request.prompt, request.approvedStory, context)
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(409, str(error)) from error


class StartFrameRequest(BaseModel):
    """Request to generate a start-frame candidate image."""
    model_config = ConfigDict(extra='forbid')
    prompt: str = Field(min_length=1, max_length=50000)
    contentId: int = Field(gt=0)
    promptVersionId: int = Field(gt=0)
    characterName: str = ""
    characterDescription: str = ""
    characterId: str = ""
    referenceImagePath: str | None = None
    referenceId: str = ""
    referenceSha256: str = ""
    aspectRatio: str = "9:16"
    contentProfile: str = "AUTO"
    generator: str = "SEEDANCE_2_0_MINI"
    maxCostUsd: float = Field(gt=0, le=5.0)
    promptFingerprint: str = ""
    sourceRevisionId: str = ""


@router.post('/start-frame/generate')
def generate_start_frame_endpoint(request: StartFrameRequest) -> dict[str, Any]:
    """Generate a start-frame candidate image from the saved production prompt.
    
    Requires explicit cost authorization (maxCostUsd > 0).
    Requires a verified character reference image path.
    The generated image is a CANDIDATE that must be explicitly accepted by the user
    before satisfying F8 EXECUTION_INPUTS.
    """
    return generate_start_frame(
        prompt_text=request.prompt,
        content_id=request.contentId,
        prompt_version_id=request.promptVersionId,
        character_name=request.characterName,
        character_description=request.characterDescription,
        character_id=request.characterId,
        reference_image_path=request.referenceImagePath,
        reference_id=request.referenceId,
        reference_sha256=request.referenceSha256,
        aspect_ratio=request.aspectRatio,
        content_profile=request.contentProfile,
        generator=request.generator,
        max_cost_usd=request.maxCostUsd,
        prompt_fingerprint=request.promptFingerprint,
        source_revision_id=request.sourceRevisionId,
    )
