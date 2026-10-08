"""Task 3 production-level Family 7 aggregation contracts."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.quality.aggregation import EvaluationState
from app.quality.contracts import RuleEvaluation, RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine

RULESET = str(settings.rules_dir / "RULESET_1.7.yaml")
FAMILY = "family7_production_test"


def engine() -> RuleEngine:
    return RuleEngine(RULESET)


def evaluation(
    rule_id: str,
    outcome: RuleOutcome | None,
    *,
    severity: Severity = Severity.PASS,
    state: EvaluationState = EvaluationState.EVALUATED,
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=rule_id,
        family=FAMILY,
        outcome=outcome,
        configured_severity=severity,
        message="synthetic production aggregation fixture",
        evaluation_state=state,
    )


def aggregate(rows: list[RuleEvaluation]) -> tuple[dict[str, float | None], dict[str, Any], float | None]:
    rule_engine = engine()
    family_scores = rule_engine._calculate_family_scores(rows)
    family_assessments = rule_engine._calculate_family_assessments(rows)
    overall_score = rule_engine._calculate_overall_score(family_scores, rows)
    return family_scores, family_assessments[FAMILY], overall_score


def test_pass_fail_score_math_remains_the_existing_severity_weighted_behavior() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("pass", RuleOutcome.PASS, severity=Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, severity=Severity.CRITICAL),
    ])
    assert family_scores[FAMILY] == 70.0
    assert assessment["aggregation"]["scoredCount"] == 2
    assert assessment["aggregation"]["denominator"] == 2
    assert overall == 70.0


def test_unknown_preserves_existing_score_and_is_explicitly_aggregated() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("pass", RuleOutcome.PASS, severity=Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, severity=Severity.CRITICAL),
        evaluation("unknown", RuleOutcome.UNKNOWN),
    ])
    assert family_scores[FAMILY] == 70.0
    assert overall == 70.0
    assert assessment["aggregation"]["unknownCount"] == 1
    assert assessment["aggregation"]["scoredCount"] == 2
    assert assessment["aggregation"]["evaluationCoverage"] == 1.0


def test_not_applicable_does_not_penalize_score_or_coverage() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("pass", RuleOutcome.PASS, severity=Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, severity=Severity.CRITICAL),
        evaluation("na", RuleOutcome.NOT_APPLICABLE),
    ])
    assert family_scores[FAMILY] == 70.0
    assert overall == 70.0
    assert assessment["aggregation"]["notApplicableCount"] == 1
    assert assessment["aggregation"]["evaluationCoverage"] == 1.0


def test_service_error_preserves_valid_score_and_exposes_error_state() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("pass", RuleOutcome.PASS, severity=Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, severity=Severity.CRITICAL),
        evaluation("service", RuleOutcome.SERVICE_ERROR),
    ])
    assert family_scores[FAMILY] == 70.0
    assert overall == 70.0
    assert assessment["aggregation"]["serviceErrorCount"] == 1
    assert assessment["aggregation"]["aggregationState"] == "SERVICE_ERROR"


def test_not_evaluated_preserves_valid_score_and_coverage() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("pass", RuleOutcome.PASS, severity=Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, severity=Severity.CRITICAL),
        evaluation("missing", None, state=EvaluationState.NOT_EVALUATED),
    ])
    assert family_scores[FAMILY] == 70.0
    assert overall == 70.0
    assert assessment["aggregation"]["notEvaluatedCount"] == 1
    assert assessment["aggregation"]["evaluationCoverage"] == 2 / 3


def test_unknown_only_has_null_family_and_overall_score() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("unknown", RuleOutcome.UNKNOWN),
    ])
    assert family_scores[FAMILY] is None
    assert overall is None
    assert assessment["aggregation"]["aggregationState"] == "NO_SCORED_ITEMS"
    assert assessment["aggregation"]["score"] is None


def test_not_evaluated_only_has_no_evaluated_items_state() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("missing", None, state=EvaluationState.NOT_EVALUATED),
    ])
    assert family_scores[FAMILY] is None
    assert overall is None
    assert assessment["aggregation"]["aggregationState"] == "NO_EVALUATED_ITEMS"
    assert assessment["aggregation"]["score"] is None


def test_not_applicable_only_has_null_score_and_null_coverage() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("na", RuleOutcome.NOT_APPLICABLE),
    ])
    assert family_scores[FAMILY] is None
    assert overall is None
    assert assessment["aggregation"]["evaluationCoverage"] is None
    assert assessment["aggregation"]["aggregationState"] == "NOT_APPLICABLE"


def test_service_error_only_has_explicit_service_state_and_null_score() -> None:
    family_scores, assessment, overall = aggregate([
        evaluation("service", RuleOutcome.SERVICE_ERROR),
    ])
    assert family_scores[FAMILY] is None
    assert overall is None
    assert assessment["aggregation"]["serviceErrorCount"] == 1
    assert assessment["aggregation"]["aggregationState"] == "SERVICE_ERROR"


def test_mixed_statuses_preserve_every_category() -> None:
    _, assessment, overall = aggregate([
        evaluation("pass", RuleOutcome.PASS, severity=Severity.PASS),
        evaluation("fail", RuleOutcome.FAIL, severity=Severity.CRITICAL),
        evaluation("unknown", RuleOutcome.UNKNOWN),
        evaluation("missing", None, state=EvaluationState.NOT_EVALUATED),
        evaluation("na", RuleOutcome.NOT_APPLICABLE),
        evaluation("service", RuleOutcome.SERVICE_ERROR),
    ])
    counts = assessment["aggregation"]
    assert overall == 70.0
    assert counts["passCount"] == 1
    assert counts["failCount"] == 1
    assert counts["unknownCount"] == 1
    assert counts["notEvaluatedCount"] == 1
    assert counts["notApplicableCount"] == 1
    assert counts["serviceErrorCount"] == 1
    assert counts["scoredCount"] == 2
    assert counts["denominator"] == 2
    assert counts["evaluationCoverage"] == 3 / 5
