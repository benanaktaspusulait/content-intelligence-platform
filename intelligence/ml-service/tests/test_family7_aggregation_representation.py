"""Task 5 ML/API aggregation representation contracts."""

from __future__ import annotations

from pathlib import Path

from app.api.quality import convert_quality_report
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
    ScoreBreakdown,
    Severity,
)
from app.scoring.quality_scorer import QualityScorer

RULESET = str(settings.rules_dir / "RULESET_1.7.yaml")
FIXTURE = Path(__file__).parent / "fixtures" / "luca_sticky_ball_prompt.txt"


def report_fixture() -> tuple[dict, QualityReport, ParserMetadata]:
    parsed = parse_prompt(FIXTURE.read_text(encoding="utf-8"))
    report = QualityReport(
        overall_score=70.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={"family7_test": 70.0},
        evaluations=(
            RuleEvaluation(
                rule_id="PASS_RULE",
                rule_name="Pass",
                family="family7_test",
                outcome=RuleOutcome.PASS,
                configured_severity=Severity.PASS,
                message="pass",
            ),
            RuleEvaluation(
                rule_id="FAIL_RULE",
                rule_name="Fail",
                family="family7_test",
                outcome=RuleOutcome.FAIL,
                configured_severity=Severity.CRITICAL,
                message="fail",
            ),
            RuleEvaluation(
                rule_id="UNKNOWN_RULE",
                rule_name="Unknown",
                family="family7_test",
                outcome=RuleOutcome.UNKNOWN,
                configured_severity=Severity.WARNING,
                message="unknown",
            ),
            RuleEvaluation(
                rule_id="NA_RULE",
                rule_name="Not applicable",
                family="family7_test",
                outcome=RuleOutcome.NOT_APPLICABLE,
                configured_severity=Severity.WARNING,
                message="not applicable",
            ),
            RuleEvaluation(
                rule_id="MISSING_RULE",
                rule_name="Missing",
                family="family7_test",
                outcome=None,
                evaluation_state=EvaluationState.NOT_EVALUATED,
                configured_severity=Severity.WARNING,
                message="did not run",
            ),
        ),
        ruleset_version="1.7",
        evaluated_at="GOLDEN_DETERMINISTIC",
    )
    return parsed.video_plan_ir, report, parsed.metadata


def test_pre_render_assessment_exposes_family7_aggregation_without_policy_rewrite() -> None:
    ir, report, parser_metadata = report_fixture()
    assessment = build_pre_render_assessment(ir, parser_metadata, report, "1.7")

    aggregation = assessment["aggregation"]
    assert aggregation["passCount"] == 1
    assert aggregation["failCount"] == 1
    assert aggregation["unknownCount"] == 1
    assert aggregation["notEvaluatedCount"] == 1
    assert aggregation["notApplicableCount"] == 1
    assert aggregation["serviceErrorCount"] == 0
    assert aggregation["scoredCount"] == 2
    assert aggregation["denominator"] == 2
    assert aggregation["evaluationCoverage"] == 3 / 4
    assert aggregation["score"] == 50.0
    assert assessment["creative_grade"] in {"A", "B", "C", "D", "F", "INCOMPLETE"}
    assert "render_authorization" in assessment


def test_quality_api_response_preserves_family7_aggregation_fields() -> None:
    ir, report, parser_metadata = report_fixture()
    enhanced = EnhancedQualityReport(
        base_report=report,
        score_breakdowns=(
            ScoreBreakdown(
                family="family7_test",
                score=70.0,
                weight=0.05,
                weighted_contribution=3.5,
                rules_passed=1,
                rules_failed=1,
                rules_warning=2,
            ),
        ),
        score_card={"score": 70.0, "label": "Acceptable", "color": "yellow"},
        timeline_data={"beats": [], "consequence_markers": [], "state_segments": []},
        family_radar={"labels": [], "scores": [], "thresholds": {}},
        top_3_strengths=(),
        top_3_weaknesses=(),
        priority_fixes=(),
        parser_metadata=parser_metadata,
    )

    response = convert_quality_report(enhanced, "1.7", video_plan_ir=ir)
    aggregation = response.pre_render_assessment.aggregation
    assert aggregation is not None
    assert aggregation["scoredCount"] == 2
    assert aggregation["notEvaluatedCount"] == 1
    assert aggregation["notApplicableCount"] == 1
    assert aggregation["evaluationCoverage"] == 3 / 4
