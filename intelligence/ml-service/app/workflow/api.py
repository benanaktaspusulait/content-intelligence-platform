"""No-credit local endpoints for the explicitly selected operational profile."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings

from .feedback import compare_cohort, match_publication, measure_observation, review_render
from .repair import repair_prompt
from .review import review_prompt

router = APIRouter(prefix="/api/v1/workflow", tags=["post-family-workflow"])


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


def capabilities() -> dict[str, Any]:
    path = settings.data_root / "workflow/provider-capabilities.json"
    return dict(json.loads(path.read_text())["models"]) if path.is_file() else {}


@router.post("/review")
def review(request: ReviewRequest) -> dict[str, Any]:
    return review_prompt(request.model_dump(), capabilities())


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
    role: Literal['STORY', 'BUILD_PROMPT', 'MINIMAL_REPAIR']
    text: str = Field(min_length=1, max_length=16000)
    context: dict[str, Any] = Field(default_factory=dict)
    maxCostUsd: float = Field(gt=0, le=20)


@router.get('/creative-role/readiness')
@router.post('/creative-role/readiness')
def creative_role_readiness() -> dict[str, Any]:
    from .creative_roles import role_readiness
    return role_readiness()


@router.post('/creative-role')
def creative_role(request: CreativeRoleRequest) -> dict[str, Any]:
    from .creative_roles import run_paid_role
    try:
        return run_paid_role(request.role, request.text, request.context, request.maxCostUsd)
    except (ValueError, json.JSONDecodeError) as error:
        raise HTTPException(409, str(error)) from error
    except Exception as error:
        raise HTTPException(502, {'status': 'PROVIDER_OUTCOME_UNKNOWN', 'retryAutomatically': False}) from error
