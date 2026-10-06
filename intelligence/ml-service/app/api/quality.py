"""
Pompom Creative Quality Engine - FastAPI Router
REST API endpoints for quality validation, scoring, and ruleset management.
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..autofix.iteration_loop import AutoFixIterationLoop
from ..assessment.pre_render_assessment import build_pre_render_assessment
from ..config import settings
from ..llm.provider import get_provider_identity
from ..parser.prompt_parser import parse_prompt
from ..quality.contracts import EnhancedQualityReport
from ..rules.rule_versioning import (
    RulesetConfigurationError,
    RulesetVersion,
    RuleVersionManager,
    VersionComparisonReport,
)
from ..scoring.quality_scorer import QualityScorer
from ..validation.regression_checker import RegressionChecker, RegressionReport

# The autofix package now shares the canonical quality contracts, so it imports
# cleanly at module load; no lazy-import workaround is required.


# Prefixless router; the ``/api/v1/quality`` prefix is applied once at mount
# time in ``app.main``.
router = APIRouter(tags=["quality"])


# === Request Models ===


class ValidateRequest(BaseModel):
    prompt: str = Field(..., min_length=100, max_length=10000, description="Video prompt text")
    ruleset_version: str = Field(
        default="1.0",
        description=(
            "Ruleset version, or 'latest' to explicitly opt into the newest version on disk. "
            "Defaults to the pinned stable version (1.0), not 'latest', so that publishing a "
            "new ruleset version never silently changes validation behavior for callers that "
            "omit this field."
        ),
    )
    evaluation_stage: Literal["PRE_RENDER", "POST_RENDER"] = "PRE_RENDER"
    visual_evidence: dict[str, Any] | None = None


class CompareVersionsRequest(BaseModel):
    prompt_before: str = Field(..., description="Original prompt")
    prompt_after: str = Field(..., description="Revised prompt")
    version_before: str = Field(default="before", description="Label for before version")
    version_after: str = Field(default="after", description="Label for after version")


class AutoFixRequest(BaseModel):
    prompt: str = Field(..., min_length=100, max_length=10000, description="Video prompt to auto-fix")
    ruleset_version: str = Field(
        default="1.0",
        description=(
            "Ruleset version, or 'latest' to explicitly opt into the newest version on disk. "
            "Defaults to the pinned stable version (1.0) for the same reason as "
            "ValidateRequest.ruleset_version — see that field's description."
        ),
    )
    max_iterations: int = Field(default=5, ge=1, le=10, description="Maximum fix iterations")
    min_improvement_threshold: float = Field(
        default=2.0, ge=0.0, description="Minimum score improvement per fix"
    )


# === Response Models ===


class RuleEvaluationResponse(BaseModel):
    rule_id: str
    rule_name: str
    family: str
    severity: str
    outcome: str
    message: str
    actual_value: float | None
    threshold_value: float | None
    details: dict[str, Any] = Field(default_factory=dict)


class PriorityFixResponse(BaseModel):
    rule_id: str
    rule_name: str
    family: str
    severity: str
    issue: str
    recommendation: str
    impact: str
    strategy: str


class ScoreCardResponse(BaseModel):
    score: float
    label: str
    color: str


class BeatResponse(BaseModel):
    start_time: float
    end_time: float
    action: str
    consequence: str
    intensity: int
    is_new_consequence: bool


class ConsequenceMarkerResponse(BaseModel):
    time: float
    consequence: str
    type: str


class StateSegmentResponse(BaseModel):
    state_id: str
    start_time: float
    end_time: float
    percentage: float


class TimelineDataResponse(BaseModel):
    beats: list[BeatResponse]
    consequence_markers: list[ConsequenceMarkerResponse]
    state_segments: list[StateSegmentResponse]


class PreRenderDimensionResponse(BaseModel):
    key: str
    title: str
    status: str
    summary: str
    observed: str
    recommendation: str
    evidence_status: str


class PreRenderAssessmentResponse(BaseModel):
    name: str
    story_structure: dict[str, Any] | None = None
    temporal_complexity: dict[str, Any] | None = None
    grade: str
    # Grade from creative judgments only; evidence gaps are reported separately below.
    creative_grade: str | None = None
    creative_score: float | None = None
    prompt_stage: str | None = None
    first_frame: dict[str, Any] | None = None
    render_authorization: dict[str, Any] | None = None
    readiness: str
    assessment_coverage_percent: int
    evidence_completeness: dict[str, Any] | None = None
    verdict: str
    strengths: list[str]
    concerns: list[str]
    recommended_changes: list[str]
    dimensions: list[PreRenderDimensionResponse]
    stable_intent: list[str]
    provenance: dict[str, Any]


class QualityProvenanceResponse(BaseModel):
    parser_version: str
    canonical_evidence_version: str = "canonical-attempt-evidence-v2"
    rule_engine_version: str
    scoring_version: str = "quality-scorer-v2"
    assessment_version: str = "pre-render-assessment-v2"
    semantic_provider: str
    semantic_model_version: str
    # Deliberately str | None, always None: no independent "producibility
    # validator" runtime exists to version. AI producibility validation is a
    # family of ordinary deterministic rules in the versioned ruleset,
    # already fully identified by ruleset_version elsewhere on this report.
    # Kept (not removed) so this response shape does not break existing
    # consumers; see PART_01_COMPLETION_ROADMAP.md's Plan C1.
    producibility_validator_version: str | None = None
    evaluation_stage: str


class ScoreBreakdownResponse(BaseModel):
    family: str
    score: float | None
    weight: float
    weighted_contribution: float | None
    rules_passed: int
    rules_failed: int
    rules_warning: int
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]


class QualityReportResponse(BaseModel):
    overall_score: float
    status: str
    ruleset_version: str
    blocker_count: int
    critical_count: int
    warning_count: int
    family_scores: dict[str, float | None]
    family_assessments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    failed_rules: list[RuleEvaluationResponse]
    unknown_rules: list[RuleEvaluationResponse]
    not_applicable_rules: list[RuleEvaluationResponse]
    service_errors: list[RuleEvaluationResponse]
    parser_confidence: float
    parser_warnings: list[str]
    parser_assumptions: list[str]
    evidence_missing: list[str]
    top_strengths: list[str]
    top_weaknesses: list[str]
    priority_fixes: list[PriorityFixResponse]
    score_card: ScoreCardResponse
    timeline_data: TimelineDataResponse
    score_breakdowns: list[ScoreBreakdownResponse]
    family_radar: dict[str, Any]
    provenance: QualityProvenanceResponse
    pre_render_assessment: PreRenderAssessmentResponse
    video_plan_ir: dict[str, Any]


class RegressionIssueResponse(BaseModel):
    rule_id: str
    rule_name: str
    family: str
    severity: str
    before_status: str
    after_status: str
    before_value: float | None
    after_value: float | None
    score_delta: float
    message: str
    recommendation: str


class RegressionReportResponse(BaseModel):
    version_before: str
    version_after: str
    has_regressions: bool
    score_before: float
    score_after: float
    score_delta: float
    status_before: str
    status_after: str
    status_improved: bool
    critical_regressions: list[RegressionIssueResponse]
    warning_regressions: list[RegressionIssueResponse]
    fixed_rules: list[str]
    improved_families: list[str]
    degraded_families: list[str]
    net_improvement: bool
    recommendation: str
    summary: str


class RuleChangeResponse(BaseModel):
    rule_id: str
    change_type: str
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    reason: str
    breaking_change: bool


class RulesetVersionResponse(BaseModel):
    version: str
    release_date: str
    description: str
    ruleset_path: str
    learned_from: list[str]
    deprecated_rules: list[str]
    is_breaking: bool
    changelog: str
    changes: list[RuleChangeResponse]


class RulesetComparisonResponse(BaseModel):
    version_from: str
    version_to: str
    is_backward_compatible: bool
    breaking_changes: list[RuleChangeResponse]
    new_rules: list[str]
    removed_rules: list[str]
    modified_rules: list[str]
    migration_notes: str


class HealthResponse(BaseModel):
    status: str
    message: str


class FixIterationResponse(BaseModel):
    iteration: int
    rule_id: str
    fix_description: str
    accepted: bool
    reason: str
    score_after: float


class AutoFixResultResponse(BaseModel):
    success: bool
    final_prompt: str
    initial_score: float
    final_score: float
    score_delta: float
    initial_status: str
    final_status: str
    iteration_count: int
    applied_fixes: list[FixIterationResponse]
    improvement_history: list[float]
    warnings: list[str]
    early_stop_reason: str | None
    final_report: QualityReportResponse


# === Endpoints ===


@router.post("/validate", response_model=QualityReportResponse, status_code=status.HTTP_200_OK)
async def validate_prompt(request: ValidateRequest) -> QualityReportResponse:
    """
    Validate a video prompt and return quality report.

    Returns score (0-100), status (RENDER_READY/NEEDS_REVISION/BLOCKED),
    failed rules, fix suggestions, and timeline visualization data.
    """
    # Parse prompt
    parse_result = parse_prompt(request.prompt)
    ir = parse_result.video_plan_ir
    if request.visual_evidence is not None:
        ir["visualEvidence"] = request.visual_evidence

    # Load ruleset. An unknown version or an absent/misconfigured ruleset
    # directory is a client/config error, not a server fault.
    version_manager = RuleVersionManager(settings.rules_dir)
    try:
        if request.ruleset_version == "latest":
            engine = version_manager.load_latest()
            ruleset_version = version_manager.get_latest_version()
        else:
            engine = version_manager.load_version(request.ruleset_version)
            ruleset_version = request.ruleset_version
    except (RulesetConfigurationError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ruleset not found: {request.ruleset_version}",
        ) from error

    # Evaluate
    report = engine.evaluate(ir, evaluation_stage=request.evaluation_stage)

    # Enhance with scoring
    scorer = QualityScorer()
    enhanced = scorer.create_enhanced_report(report, ir, parse_result.metadata)

    # Convert to response model
    return convert_quality_report(enhanced, ruleset_version, request.evaluation_stage, ir)


@router.post("/compare-versions", response_model=RegressionReportResponse)
async def compare_versions(request: CompareVersionsRequest) -> RegressionReportResponse:
    """
    Compare two prompt versions and detect regressions.

    Returns regression analysis with breaking changes, fixed rules,
    and recommendation (ACCEPT/REVISE/REJECT).
    """
    # Parse both prompts
    result_before = parse_prompt(request.prompt_before)
    result_after = parse_prompt(request.prompt_after)

    ir_before = result_before.video_plan_ir
    ir_after = result_after.video_plan_ir

    # Load the active ruleset; an absent/misconfigured ruleset is a config error.
    try:
        engine = RuleVersionManager(settings.rules_dir).load_latest()
    except (RulesetConfigurationError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Active ruleset is not available",
        ) from error

    report_before = engine.evaluate(ir_before)
    report_after = engine.evaluate(ir_after)

    # Check regression
    checker = RegressionChecker()
    regression = checker.check(report_before, report_after, request.version_before, request.version_after)

    return convert_regression_report(regression)


@router.post("/auto-fix", response_model=AutoFixResultResponse, status_code=status.HTTP_200_OK)
async def auto_fix_prompt(request: AutoFixRequest) -> AutoFixResultResponse:
    """
    Automatically fix quality issues in a video prompt through iterative improvement.

    Applies rule-specific fixes (add consequences, reduce static state, break repetitions)
    and validates each change using regression checking. Stops when RENDER_READY or
    max iterations reached.

    Returns final improved prompt with score trajectory and applied fixes.
    """
    # Load ruleset version label; an unknown/absent ruleset is a client/config
    # error, not a server fault.
    try:
        version_manager = RuleVersionManager(settings.rules_dir)
        if request.ruleset_version == "latest":
            ruleset_version = version_manager.get_latest_version()
        else:
            ruleset_version = request.ruleset_version
    except (RulesetConfigurationError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ruleset not found: {request.ruleset_version}",
        ) from error

    # Run auto-fix loop. A missing ruleset file is a config error (503); any
    # malformed ruleset content surfaces the same way rather than leaking a
    # raw stack string.
    try:
        loop = AutoFixIterationLoop(
            ruleset_version=ruleset_version,
            max_iterations=request.max_iterations,
            min_improvement_threshold=request.min_improvement_threshold,
        )
        result = loop.run(request.prompt)
    except (FileNotFoundError, RulesetConfigurationError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Active ruleset is not available",
        ) from error

    # The loop already produced the enhanced final report; reuse it.
    final_report_response = convert_quality_report(result.final_enhanced_report, ruleset_version)

    applied_fixes_response = [
        FixIterationResponse(
            iteration=fix.iteration,
            rule_id=fix.fix_applied.rule_id,
            fix_description=fix.fix_applied.fix_description,
            accepted=fix.accepted,
            reason=fix.reason,
            score_after=fix.report.overall_score,
        )
        for fix in result.applied_fixes
    ]

    return AutoFixResultResponse(
        success=result.success,
        final_prompt=result.final_prompt,
        initial_score=result.initial_score,
        final_score=result.final_score,
        score_delta=result.score_delta,
        initial_status=result.initial_status,
        final_status=result.final_status,
        iteration_count=result.iteration_count,
        applied_fixes=applied_fixes_response,
        improvement_history=result.improvement_history,
        warnings=result.warnings,
        early_stop_reason=result.early_stop_reason,
        final_report=final_report_response,
    )


@router.get("/rulesets", response_model=list[RulesetVersionResponse])
async def list_rulesets() -> list[RulesetVersionResponse]:
    """Get all available ruleset versions."""
    try:
        manager = RuleVersionManager(settings.rules_dir)
        versions = manager.list_versions()
        return [convert_ruleset_version(v) for v in versions]
    except (RulesetConfigurationError, ValueError) as error:
        # Absent/misconfigured ruleset directory or metadata.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ruleset catalog is not available",
        ) from error


@router.get("/rulesets/{version}", response_model=RulesetVersionResponse)
async def get_ruleset(version: str) -> RulesetVersionResponse:
    """Get detailed information about a specific ruleset version."""
    try:
        manager = RuleVersionManager(settings.rules_dir)
    except RulesetConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ruleset catalog is not available",
        ) from error
    try:
        ruleset = manager.get_version_info(version)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ruleset not found: {version}",
        ) from error
    return convert_ruleset_version(ruleset)


@router.get("/rulesets/compare/{from_version}/{to_version}", response_model=RulesetComparisonResponse)
async def compare_rulesets(from_version: str, to_version: str) -> RulesetComparisonResponse:
    """Compare two ruleset versions and get migration guide."""
    try:
        manager = RuleVersionManager(settings.rules_dir)
    except RulesetConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ruleset catalog is not available",
        ) from error
    try:
        comparison = manager.compare_versions(from_version, to_version)
    except ValueError as error:
        # Unknown from/to version.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (FileNotFoundError, OSError) as error:
        # Ruleset file referenced by metadata is missing/unreadable.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ruleset content is not available for comparison",
        ) from error
    return convert_ruleset_comparison(comparison)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    try:
        # Quick validation that core modules load
        manager = RuleVersionManager(settings.rules_dir)
        latest = manager.get_latest_version()
        return HealthResponse(status="UP", message=f"Quality Engine operational, ruleset v{latest}")
    except Exception as e:
        return HealthResponse(status="DOWN", message=f"Quality Engine error: {str(e)}")


# === Conversion Helpers ===


def _as_optional_float(value: Any) -> float | None:
    """Coerce a measurement to float for the DTO, or None if non-numeric.

    Some rules measure enums/strings (e.g. complexity ``very_high``); those are
    not expressible as a float threshold and are reported as ``None``.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def convert_quality_report(
    enhanced: EnhancedQualityReport, ruleset_version: str, evaluation_stage: str = "PRE_RENDER",
    video_plan_ir: dict[str, Any] | None = None,
) -> QualityReportResponse:
    """Convert an :class:`EnhancedQualityReport` to the API response model.

    Consumes the canonical ``base_report`` (explicit ``RuleOutcome`` /
    ``Severity``) and the typed ``priority_fixes``. The timeline keys produced
    by the scorer are already DTO-aligned, so this is a single mechanical map.
    """
    report = enhanced.base_report

    def _to_rule_evaluation_response(ev: Any) -> RuleEvaluationResponse:
        return RuleEvaluationResponse(
            rule_id=ev.rule_id,
            rule_name=ev.rule_name,
            family=ev.family,
            severity=ev.configured_severity.value,
            outcome=ev.outcome.value,
            message=ev.message,
            actual_value=_as_optional_float(ev.actual_value),
            threshold_value=_as_optional_float(ev.threshold_value),
            details=dict(ev.details),
        )

    failed_rules = [_to_rule_evaluation_response(ev) for ev in report.failed_rules]
    unknown_rules = [_to_rule_evaluation_response(ev) for ev in report.unknown_rules]
    not_applicable_rules = [_to_rule_evaluation_response(ev) for ev in report.not_applicable_rules]
    service_errors = [_to_rule_evaluation_response(ev) for ev in report.service_errors]

    priority_fixes = [
        PriorityFixResponse(
            rule_id=fix.rule_id,
            rule_name=fix.rule_name,
            family=fix.family,
            severity=fix.severity.value,
            issue=fix.issue,
            recommendation=fix.recommendation,
            impact=fix.impact,
            strategy=fix.strategy.value,
        )
        for fix in enhanced.priority_fixes
    ]

    timeline_data = TimelineDataResponse(
        beats=[
            BeatResponse(
                start_time=b["start_time"],
                end_time=b["end_time"],
                action=b["action"],
                consequence=b["consequence"],
                intensity=b["intensity"],
                is_new_consequence=b["is_new_consequence"],
            )
            for b in enhanced.timeline_data.get("beats", [])
        ],
        consequence_markers=[
            ConsequenceMarkerResponse(
                time=m["time"],
                consequence=m["consequence"],
                type=m["type"],
            )
            for m in enhanced.timeline_data.get("consequence_markers", [])
        ],
        state_segments=[
            StateSegmentResponse(
                state_id=s["state_id"],
                start_time=s["start_time"],
                end_time=s["end_time"],
                percentage=s["percentage"],
            )
            for s in enhanced.timeline_data.get("state_segments", [])
        ],
    )

    semantic_provider, semantic_model_version = get_provider_identity()
    plan_ir = video_plan_ir or {}
    assessment = build_pre_render_assessment(plan_ir, enhanced.parser_metadata, report, ruleset_version)

    return QualityReportResponse(
        overall_score=report.overall_score,
        status=report.status,
        ruleset_version=ruleset_version,
        blocker_count=report.blocker_count,
        critical_count=report.critical_count,
        warning_count=report.warning_count,
        family_scores=report.family_scores,
        family_assessments=report.family_assessments,
        failed_rules=failed_rules,
        unknown_rules=unknown_rules,
        not_applicable_rules=not_applicable_rules,
        service_errors=service_errors,
        parser_confidence=enhanced.parser_metadata.confidence,
        parser_warnings=list(enhanced.parser_metadata.warnings),
        parser_assumptions=list(enhanced.parser_metadata.assumptions),
        evidence_missing=list(enhanced.parser_metadata.evidence_missing),
        top_strengths=list(enhanced.top_3_strengths),
        top_weaknesses=list(enhanced.top_3_weaknesses),
        priority_fixes=priority_fixes,
        score_card=ScoreCardResponse(**enhanced.score_card),
        timeline_data=timeline_data,
        score_breakdowns=[
            ScoreBreakdownResponse(
                family=item.family,
                score=item.score,
                weight=item.weight,
                weighted_contribution=item.weighted_contribution,
                rules_passed=item.rules_passed,
                rules_failed=item.rules_failed,
                rules_warning=item.rules_warning,
                strengths=list(item.strengths),
                weaknesses=list(item.weaknesses),
                recommendations=list(item.recommendations),
            )
            for item in enhanced.score_breakdowns
        ],
        family_radar=enhanced.family_radar,
        provenance=QualityProvenanceResponse(
            parser_version=settings.parser_version,
            canonical_evidence_version="canonical-attempt-evidence-v2",
            rule_engine_version=settings.rule_engine_version,
            scoring_version="quality-scorer-v2",
            assessment_version="pre-render-assessment-v2",
            semantic_provider=semantic_provider,
            semantic_model_version=semantic_model_version,
            producibility_validator_version=None,
            evaluation_stage=evaluation_stage,
        ),
        pre_render_assessment=PreRenderAssessmentResponse(**assessment),
        video_plan_ir=plan_ir,
    )


def convert_regression_report(regression: RegressionReport) -> RegressionReportResponse:
    """Convert RegressionReport to API response model."""
    return RegressionReportResponse(
        version_before=regression.version_before,
        version_after=regression.version_after,
        has_regressions=regression.has_regressions,
        score_before=regression.score_before,
        score_after=regression.score_after,
        score_delta=regression.score_delta,
        status_before=regression.status_before,
        status_after=regression.status_after,
        status_improved=regression.status_improved,
        critical_regressions=[
            RegressionIssueResponse(
                rule_id=issue.rule_id,
                rule_name=issue.rule_name,
                family=issue.family,
                severity=issue.severity.value,
                before_status=issue.before_status,
                after_status=issue.after_status,
                before_value=issue.before_value,
                after_value=issue.after_value,
                score_delta=issue.score_delta,
                message=issue.message,
                recommendation=issue.recommendation,
            )
            for issue in regression.critical_regressions
        ],
        warning_regressions=[
            RegressionIssueResponse(
                rule_id=issue.rule_id,
                rule_name=issue.rule_name,
                family=issue.family,
                severity=issue.severity.value,
                before_status=issue.before_status,
                after_status=issue.after_status,
                before_value=issue.before_value,
                after_value=issue.after_value,
                score_delta=issue.score_delta,
                message=issue.message,
                recommendation=issue.recommendation,
            )
            for issue in regression.warning_regressions
        ],
        fixed_rules=regression.fixed_rules,
        improved_families=regression.improved_families,
        degraded_families=regression.degraded_families,
        net_improvement=regression.net_improvement,
        recommendation=regression.recommendation,
        summary=regression.summary,
    )


def convert_ruleset_version(version: RulesetVersion) -> RulesetVersionResponse:
    """Convert RulesetVersion to API response model."""
    return RulesetVersionResponse(
        version=version.version,
        release_date=version.release_date,
        description=version.description,
        ruleset_path=version.ruleset_path,
        learned_from=version.learned_from,
        deprecated_rules=list(version.deprecated_rules),
        is_breaking=version.is_breaking,
        changelog=version.changelog,
        changes=[
            RuleChangeResponse(
                rule_id=change.rule_id,
                change_type=change.change_type,
                old_value=change.old_value,
                new_value=change.new_value,
                reason=change.reason,
                breaking_change=change.breaking_change,
            )
            for change in version.changes
        ],
    )


def convert_ruleset_comparison(comparison: VersionComparisonReport) -> RulesetComparisonResponse:
    """Convert VersionComparisonReport to API response model."""
    return RulesetComparisonResponse(
        version_from=comparison.version_from,
        version_to=comparison.version_to,
        is_backward_compatible=comparison.is_backward_compatible,
        breaking_changes=[
            RuleChangeResponse(
                rule_id=change.rule_id,
                change_type=change.change_type,
                old_value=change.old_value,
                new_value=change.new_value,
                reason=change.reason,
                breaking_change=change.breaking_change,
            )
            for change in comparison.breaking_changes
        ],
        new_rules=comparison.new_rules,
        removed_rules=comparison.removed_rules,
        modified_rules=comparison.modified_rules,
        migration_notes=comparison.migration_notes,
    )
