"""No-credit local endpoints for the explicitly selected operational profile."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
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
    canonicalRulesetVersion: Literal["1.7", "1.8", "1.9", "1.10", "1.11"] | None = None
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
    canonicalRulesetVersion: Literal["1.7", "1.8", "1.9", "1.10", "1.11"] = "1.11"


@router.post("/source-plan")
def source_plan(request: SourcePlanRequest) -> dict[str, Any]:
    from app.parser.prompt_parser import source_plan_evidence
    return source_plan_evidence(request.prompt, request.sourceId, request.sourceVersion, request.canonicalRulesetVersion)


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


class OptimizationRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=16000)
    context: dict[str, Any]
    providerResult: dict[str, Any]
    diagnostics: dict[str, Any]


class OptimizationAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=16000)
    context: dict[str, Any]
    candidates: list[dict[str, Any]]
    baselineScore: float | None = None


class CreativePromptQualityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    originalPrompt: str = Field(min_length=1, max_length=50000)
    candidatePrompt: str = Field(min_length=1, max_length=50000)
    contentProfile: str = Field(default="UNKNOWN", max_length=80)
    generator: str = Field(default="UNKNOWN", max_length=80)
    durationSeconds: float | None = Field(default=None, gt=0, le=600)
    diagnosis: dict[str, Any] = Field(default_factory=dict)
    canonicalFindings: dict[str, Any] = Field(default_factory=dict)
    executionCritic: dict[str, Any] = Field(default_factory=dict)


@router.post('/optimization-assessment')
def optimization_assessment(request: OptimizationAssessmentRequest) -> dict[str, Any]:
    from .optimization_comparison import assess_comparison
    return assess_comparison(request.text, request.candidates, request.context, request.baselineScore)


@router.post("/creative-prompt-quality/assess")
def creative_prompt_quality_assess(request: CreativePromptQualityRequest) -> dict[str, Any]:
    from .creative_prompt_quality import assess
    try:
        return assess(request.model_dump())
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post("/creative-prompt-quality/calibration-readiness")
def creative_prompt_quality_calibration_readiness(request: dict[str, Any]) -> dict[str, Any]:
    from .creative_prompt_quality import validate_calibration
    records = request.get("records", [])
    if not isinstance(records, list) or len(records) > 5000:
        raise HTTPException(422, "records must be a list with at most 5000 examples")
    return validate_calibration(records)


@router.post("/creative-prompt-quality/calibration-preview")
def creative_prompt_quality_calibration_preview(request: dict[str, Any]) -> dict[str, Any]:
    from .creative_prompt_quality import calibration_preview
    records = request.get("records", [])
    if not isinstance(records, list) or len(records) > 5000:
        raise HTTPException(422, "records must be a list with at most 5000 examples")
    return calibration_preview(records)


@router.post('/optimization-recovery')
def optimization_recovery(request: OptimizationRecoveryRequest) -> dict[str, Any]:
    from .creative_roles import perform_role, _optimization_validation_category
    from copy import deepcopy
    # No SDK, provider factory, paid configuration or network path is reachable.
    class SavedResponse:
        saved_result_recovery = True
        def complete(self, *args, **kwargs):
            return json.dumps(request.providerResult, ensure_ascii=False)
    provider = SavedResponse()
    try:
        context = dict(request.context)
        # Historical candidate responses retain their legacy source contract.
        if 'proposals' in request.providerResult:
            context['optimizationGenerationContractVersion']='creative-reconstruction-v2'
        elif any(k in request.providerResult for k in ('plans','openingPlan','escalationPlan')):
            context['optimizationGenerationContractVersion']='plan-first-v1'
        else:
            context['optimizationGenerationContractVersion']='profile-ownership-v1'
        result = perform_role('PROMPT_OPTIMIZATION', request.text, context,
                              provider, str(request.diagnostics.get('model', 'saved-response')))
    except ValueError as error:
        raise HTTPException(409, {'category': _optimization_validation_category(error),
                                 'detail': str(error), 'providerDispatched': False,
                                 'providerCallsThisOperation': 0,
                                 'profileValidations': [c.get('profileValidation') for c in (getattr(provider, 'last_normalized_role_result', {}) or {}).get('candidates', [])],
                                 'profileValidation': getattr(error, 'profile_validation', None)}) from error
    if result.get('result',{}).get('creativeContractVersion') == 'creative-reconstruction-v2':
        result['result']['improvementMetrics'].update(providerCalls=0, callsWithoutAcceptableCandidate=0, providerCostUsd=None, reusedProviderResult=True)
    result.update(calls=0, provider='saved-response',
                  rawProviderResult=deepcopy(request.providerResult),
                  providerResponseMetadata=deepcopy(request.diagnostics))
    return result


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
async def creative_role(request: CreativeRoleRequest, http_request: Request) -> dict[str, Any]:
    from .creative_roles import CreativeRoleFailure, run_paid_role
    if request.role == 'PROMPT_OPTIMIZATION' or request.context.get('storyExperiment') or request.context.get('assessmentOnlyPolicy'):
        import hashlib, hmac, os
        token=os.getenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN','')
        expected=hmac.new(token.encode(),await http_request.body(),hashlib.sha256).hexdigest()
        if len(token)<32 or not hmac.compare_digest(expected,http_request.headers.get('X-Adaptive-Dispatch','')):
            raise HTTPException(403,'Adaptive dispatch requires the durable backend authorization boundary')
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
        if request.context.get('storyExperiment') or request.context.get('assessmentOnlyPolicy'):
            # Pilot post-dispatch failures are returned by execute as complete
            # receipts. An exception here therefore precedes provider creation.
            return {'requestId': request.context.get('storyRequestId'), 'role': request.role,
                    'processingStatus': 'NOT_DISPATCHED', 'billingStatus': 'NOT_DISPATCHED',
                    'providerDispatched': False, 'actualCostUsd': 0, 'usage': None,
                    'rawProviderResponse': None, 'retrySafe': False,
                    'error': {'category': type(error).__name__, 'detail': str(error)[:2000]}}
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
            'retrySafe': not bool(request.context.get('storyExperiment')),
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


@router.post('/story-experiment/preflight')
def story_experiment_preflight(request: CreativeRoleRequest) -> dict[str, Any]:
    from .story_experiment import preview
    return preview(request.role, request.text, request.context)


@router.post('/story-experiment/validate')
def story_experiment_validate(request: dict[str, Any]) -> dict[str, Any]:
    from .story_experiment import validate
    return validate(request['text'], request['context'], request['result'])


@router.post('/story-experiment/assessment-preflight')
def assessment_preflight(request: CreativeRoleRequest) -> dict[str, Any]:
    from .story_assessment import preview
    if request.role != 'STORY_REVIEW': raise HTTPException(400,'Assessment-only review role required')
    return preview(request.text, request.context)


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

class AdaptivePolicyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['PREFLIGHT','STAGE_DECISION','ESCALATION_BRIEF','METRICS','CREATIVE_VALIDITY']
    canonical: dict[str, Any]
    source: str = ''
    context: dict[str, Any] = Field(default_factory=dict)
    comparison: dict[str, Any] = Field(default_factory=dict)


@router.post('/adaptive-optimization-policy')
def adaptive_optimization_policy(request: AdaptivePolicyRequest) -> dict[str, Any]:
    from .adaptive_optimization import feasibility, stage_decision, escalation_brief, optimization_metrics
    from .creative_provider_profiles import readiness
    if request.action == 'PREFLIGHT':
        return {**feasibility(request.canonical, request.source, request.context), 'providerConfiguration': readiness()}
    if request.action == 'METRICS':
        return optimization_metrics(request.context.get('runs',[]))
    if request.action == 'CREATIVE_VALIDITY':
        from .creative_validity import assess
        return assess(request.source, request.canonical, request.context.get('provenance'), request.context.get('reviewer'))
    decision = stage_decision(request.comparison, request.canonical)
    if request.action == 'ESCALATION_BRIEF':
        return escalation_brief(request.source, request.context, request.comparison, decision)
    return decision


@router.post('/cpq-pilot/capabilities')
def cpq_pilot_capabilities(request: dict[str, Any]) -> dict[str, Any]:
    from .owner_machine_pilot import capabilities
    return capabilities()


@router.post('/cpq-pilot/execute')
async def cpq_pilot_execute(request: Request) -> dict[str, Any]:
    import os, hmac, hashlib
    from .owner_machine_pilot import execute
    raw = await request.body()
    token = os.getenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN', '')
    signature = request.headers.get('X-CPQ-Pilot-Dispatch', '')
    if os.getenv('CPQ_PILOT_REAL_ENABLED', 'false').lower() != 'true' or len(token)<32 or not hmac.compare_digest(signature, hmac.new(token.encode(), raw, hashlib.sha256).hexdigest()):
        raise HTTPException(403, 'Owner pilot real dispatch is disabled or unauthenticated')
    try:
        body=json.loads(raw)
        if body.get("input",{}).get("purpose")=="DRAFT_COMPARATIVE_REVIEW_V1":
            from .draft_comparative_review import execute as execute_draft
            return execute_draft(body)
        return execute(body)
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(422, 'Invalid bound pilot authorization/input; no retry') from error


@router.post('/cpq-pilot/revalidate-source')
async def cpq_pilot_revalidate_source(request: Request) -> dict[str, Any]:
    # Internal signed offline operation, deliberately independent of the paid-dispatch switch.
    import os, hmac, hashlib
    from .owner_machine_pilot import revalidate_saved_source
    from jsonschema.exceptions import ValidationError
    raw=await request.body();token=os.getenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN','')
    if len(token)<32 or not hmac.compare_digest(request.headers.get('X-CPQ-Pilot-Dispatch',''),hmac.new(token.encode(),raw,hashlib.sha256).hexdigest()):
        raise HTTPException(403,'Authenticated offline source revalidation required')
    try:return revalidate_saved_source(json.loads(raw))
    except (ValueError,KeyError,TypeError,ValidationError) as error:raise HTTPException(422,'Saved source evidence is not eligible for citation recovery') from error


@router.post('/cpq-pilot/draft-preflight')
def cpq_draft_preflight(request: dict[str, Any]) -> dict[str, Any]:
    from .draft_comparative_review import preflight
    try:return preflight(request)
    except (ValueError, KeyError, TypeError) as error:raise HTTPException(422,'Invalid diagnostic pair preflight') from error


@router.post('/optimization-loop/local')
def optimization_loop_local(body: dict[str, Any]) -> dict[str, Any]:
    from .optimization_loop import capabilities, evaluate, compare, preflight, preview
    try:
        action=body.get('action')
        if action=='CAPABILITIES': return capabilities()
        if action=='EVALUATE': return evaluate(body)
        if action=='COMPARE': return compare(body)
        if action=='PREFLIGHT_REQUEST': return preflight(body)
        if action=='PREVIEW_REQUEST': return preview(body)
        raise ValueError('Unsupported loop operation')
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(422, 'Invalid loop scope or local contract') from error


@router.post('/cpq-pilot/optimization-loop-execute')
async def optimization_loop_execute(request: Request) -> dict[str, Any]:
    import os, hmac, hashlib
    from .optimization_loop import execute_request
    raw=await request.body();token=os.getenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN','')
    signature=request.headers.get('X-CPQ-Pilot-Dispatch','')
    if os.getenv('CPQ_PILOT_REAL_ENABLED','false').lower()!='true' or len(token)<32 or not hmac.compare_digest(signature,hmac.new(token.encode(),raw,hashlib.sha256).hexdigest()):
        raise HTTPException(403,'Optimization real dispatch disabled or unsigned')
    try: return execute_request(json.loads(raw))
    except (ValueError,KeyError,TypeError):
        raise HTTPException(422,'Invalid bounded request before dispatch; no retry')
