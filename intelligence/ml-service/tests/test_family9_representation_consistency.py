"""Family 9 RED-phase representation consistency contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.api.quality import convert_quality_report
from app.assessment.family8_projection import render_admission_allowed
from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.aggregation import EvaluationState
from app.quality.contracts import (
    EnhancedQualityReport,
    ParserMetadata,
    QualityReport,
    QualityStatus,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer


RULESET = str(settings.rules_dir / "RULESET_1.7.yaml")
FIXTURE = Path(__file__).parent / "fixtures" / "luca_sticky_ball_prompt.txt"


def evaluation(
    rule_id: str,
    outcome: RuleOutcome | None,
    severity: Severity,
    *,
    family: str,
    state: EvaluationState = EvaluationState.EVALUATED,
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=rule_id,
        family=family,
        outcome=outcome,
        configured_severity=severity,
        message=f"Family 9 deterministic fixture: {rule_id}",
        evaluation_state=state,
    )


def enhanced_fixture(
    *,
    overall_score: float | None,
    family_scores: dict[str, float | None],
    evaluations: tuple[RuleEvaluation, ...],
    status: QualityStatus = QualityStatus.NEEDS_REVISION,
    family_assessments: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], ParserMetadata, QualityReport, EnhancedQualityReport]:
    parsed = parse_prompt(FIXTURE.read_text(encoding="utf-8"))
    report = QualityReport(
        overall_score=overall_score,
        status=status,
        family_scores=family_scores,
        evaluations=evaluations,
        ruleset_version="1.7",
        evaluated_at="FAMILY9_DETERMINISTIC",
        family_assessments=family_assessments or {},
    )
    enhanced = QualityScorer().create_enhanced_report(
        report,
        parsed.video_plan_ir,
        parsed.metadata,
    )
    return parsed.video_plan_ir, parsed.metadata, report, enhanced


def test_numeric_overall_score_survives_assessment_and_api_representation() -> None:
    ir, parser_metadata, report, enhanced = enhanced_fixture(
        overall_score=82.5,
        family_scores={"family9_representation": 82.5},
        evaluations=(
            evaluation(
                "FAMILY9_SCORE",
                RuleOutcome.PASS,
                Severity.PASS,
                family="family9_representation",
            ),
        ),
    )

    assessment = build_pre_render_assessment(ir, parser_metadata, report, "1.7")
    response = convert_quality_report(enhanced, "1.7", video_plan_ir=ir)

    assert assessment["creative_score"] == 82.5
    assert assessment["family8"]["creativeQuality"]["creativeScore"] == 82.5
    assert response.overall_score == 82.5
    assert response.score_card.score == 82.5
    assert response.pre_render_assessment.creative_score == 82.5
    assert response.family_scores["family9_representation"] == 82.5


def test_nullable_overall_and_family_scores_survive_the_full_assessment_api_path() -> None:
    ir, parser_metadata, report, enhanced = enhanced_fixture(
        overall_score=None,
        family_scores={"family9_unscored": None},
        evaluations=(
            evaluation(
                "FAMILY9_UNKNOWN",
                RuleOutcome.UNKNOWN,
                Severity.WARNING,
                family="family9_unscored",
            ),
        ),
    )

    # The scorer already has a nullable score-card contract; this test deliberately
    # continues through assessment and API conversion rather than stopping at Family 8.
    assert enhanced.score_card["score"] is None
    assessment = build_pre_render_assessment(ir, parser_metadata, report, "1.7")
    response = convert_quality_report(enhanced, "1.7", video_plan_ir=ir)

    assert assessment["creative_score"] is None
    assert assessment["family8"]["creativeQuality"]["creativeScore"] is None
    assert assessment["family8"]["creativeQuality"]["familyScores"]["family9_unscored"] is None
    assert response.overall_score is None
    assert response.score_card.score is None
    assert response.family_scores["family9_unscored"] is None


def mixed_evaluations() -> tuple[RuleEvaluation, ...]:
    return (
        evaluation("FAMILY9_PASS", RuleOutcome.PASS, Severity.PASS, family="family9_scored"),
        evaluation("FAMILY9_FAIL", RuleOutcome.FAIL, Severity.CRITICAL, family="family9_scored"),
        evaluation("FAMILY9_UNKNOWN", RuleOutcome.UNKNOWN, Severity.WARNING, family="family9_evidence"),
        evaluation(
            "FAMILY9_NOT_EVALUATED",
            None,
            Severity.WARNING,
            family="family9_evidence",
            state=EvaluationState.NOT_EVALUATED,
        ),
        evaluation(
            "FAMILY9_NOT_APPLICABLE",
            RuleOutcome.NOT_APPLICABLE,
            Severity.WARNING,
            family="family9_applicability",
        ),
        evaluation(
            "FAMILY9_SERVICE_ERROR",
            RuleOutcome.SERVICE_ERROR,
            Severity.BLOCKER,
            family="family9_runtime",
        ),
    )


def mixed_fixture() -> tuple[dict[str, Any], ParserMetadata, QualityReport, EnhancedQualityReport]:
    evaluations = mixed_evaluations()
    family_assessments = RuleEngine(RULESET)._calculate_family_assessments(list(evaluations))
    return enhanced_fixture(
        overall_score=70.0,
        family_scores={
            "family9_scored": 70.0,
            "family9_evidence": None,
            "family9_applicability": None,
            "family9_runtime": None,
        },
        evaluations=evaluations,
        family_assessments=family_assessments,
    )


def test_mixed_outcomes_preserve_top_level_and_per_family_counts() -> None:
    ir, parser_metadata, report, enhanced = mixed_fixture()

    assessment = build_pre_render_assessment(ir, parser_metadata, report, "1.7")
    response = convert_quality_report(enhanced, "1.7", video_plan_ir=ir)
    aggregation = assessment["aggregation"]

    assert aggregation["passCount"] == 1
    assert aggregation["failCount"] == 1
    assert aggregation["unknownCount"] == 1
    assert aggregation["notEvaluatedCount"] == 1
    assert aggregation["notApplicableCount"] == 1
    assert aggregation["serviceErrorCount"] == 1
    assert aggregation["scoredCount"] == 2
    assert aggregation["denominator"] == 2

    families = response.family_assessments
    assert families["family9_scored"]["counts"]["PASS"] == 1
    assert families["family9_scored"]["counts"]["FAIL"] == 1
    assert families["family9_evidence"]["counts"]["UNKNOWN"] == 1
    assert families["family9_evidence"]["counts"]["NOT_EVALUATED"] == 1
    assert families["family9_evidence"]["aggregation"]["notEvaluatedCount"] == 1
    assert families["family9_applicability"]["counts"]["NOT_APPLICABLE"] == 1
    assert families["family9_runtime"]["counts"]["SERVICE_ERROR"] == 1

    api_aggregation = response.pre_render_assessment.aggregation
    assert api_aggregation is not None
    assert api_aggregation["unknownCount"] == 1
    assert api_aggregation["notEvaluatedCount"] == 1
    assert api_aggregation["notApplicableCount"] == 1


def test_aggregation_ratio_and_legacy_assessment_percent_keep_distinct_units() -> None:
    ir, parser_metadata, report, enhanced = mixed_fixture()

    assessment = build_pre_render_assessment(ir, parser_metadata, report, "1.7")
    response = convert_quality_report(enhanced, "1.7", video_plan_ir=ir)
    aggregation = assessment["aggregation"]

    assert aggregation["evaluationCoverage"] == 3 / 5
    assert assessment["assessment_coverage_percent"] == 40
    assert type(assessment["assessment_coverage_percent"]) is int
    assert aggregation["evaluationCoverage"] != assessment["assessment_coverage_percent"]
    assert response.pre_render_assessment.aggregation["evaluationCoverage"] == 3 / 5
    assert response.pre_render_assessment.assessment_coverage_percent == 40


def test_family8_sticky_ball_axes_and_authorization_reasons_remain_independent() -> None:
    evaluations = tuple(
        evaluation(
            f"FAMILY9_STICKY_PASS_{index}",
            RuleOutcome.PASS,
            Severity.PASS,
            family="family9_sticky_ball",
        )
        for index in range(4)
    ) + (
        evaluation(
            "FAMILY9_STICKY_PENDING",
            RuleOutcome.UNKNOWN,
            Severity.WARNING,
            family="family9_sticky_ball",
        ),
    )
    ir, parser_metadata, report, enhanced = enhanced_fixture(
        overall_score=82.5,
        family_scores={"family9_sticky_ball": 82.5},
        evaluations=evaluations,
    )

    assessment = build_pre_render_assessment(ir, parser_metadata, report, "1.7")
    response = convert_quality_report(enhanced, "1.7", video_plan_ir=ir)
    family8 = assessment["family8"]
    authorization = family8["renderAuthorization"]

    assert family8["creativeQuality"]["creativeGrade"] == "A"
    assert family8["evidenceCompleteness"]["status"] == "PARTIAL"
    assert authorization["status"] == "BLOCKED_PENDING_EVIDENCE"
    assert len(authorization["reasons"]) >= 2
    assert all(
        set(reason) >= {"code", "source", "message", "references"}
        and reason["code"]
        and reason["source"]
        and reason["message"]
        and reason["references"]
        for reason in authorization["reasons"]
    )

    api_family8 = response.pre_render_assessment.family8
    assert api_family8 is not None
    assert api_family8["creativeQuality"]["creativeGrade"] == "A"
    assert api_family8["evidenceCompleteness"]["status"] == "PARTIAL"
    assert api_family8["renderAuthorization"]["status"] == "BLOCKED_PENDING_EVIDENCE"
    assert api_family8["renderAuthorization"]["reasons"] == authorization["reasons"]

    # Compatibility readiness is intentionally not an admission decision.
    assert family8["legacy"]["readiness"] == "READY_TO_RENDER"
    arbitrary_status = {**authorization, "status": "READY_TO_RENDER"}
    assert render_admission_allowed(arbitrary_status) is False
