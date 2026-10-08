"""RED contract tests for Family 7 status-aware aggregation."""

from __future__ import annotations

from app.quality.aggregation import AggregationRow, EvaluationState, summarize_aggregation
from app.quality.contracts import RuleOutcome


def evaluated(rule_id: str, outcome: RuleOutcome) -> AggregationRow:
    return AggregationRow(
        rule_id=rule_id,
        outcome=outcome,
        evaluation_state=EvaluationState.EVALUATED,
        family="family7-test",
        reason="synthetic boundary fixture",
    )


def not_evaluated(rule_id: str) -> AggregationRow:
    return AggregationRow(
        rule_id=rule_id,
        outcome=None,
        evaluation_state=EvaluationState.NOT_EVALUATED,
        family="family7-test",
        reason="synthetic evaluation did not run",
    )


def test_pass_pass_fail_scores_all_three_rows() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.PASS),
        evaluated("r2", RuleOutcome.PASS),
        evaluated("r3", RuleOutcome.FAIL),
    ])
    assert summary.pass_count == 2
    assert summary.fail_count == 1
    assert summary.scored_count == 3
    assert summary.denominator == 3
    assert summary.score is not None
    assert summary.evaluation_coverage == 1.0
    assert summary.aggregation_state == "EVALUATED"


def test_unknown_is_not_scored_but_counts_as_semantically_evaluated_for_coverage() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.PASS),
        evaluated("r2", RuleOutcome.PASS),
        evaluated("r3", RuleOutcome.UNKNOWN),
    ])
    assert summary.scored_count == 2
    assert summary.denominator == 2
    assert summary.score is not None
    assert summary.unknown_count == 1
    assert summary.evaluation_coverage == 1.0
    assert summary.aggregation_state == "PARTIAL"


def test_not_evaluated_is_not_unknown_or_zero() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.PASS),
        evaluated("r2", RuleOutcome.PASS),
        not_evaluated("r3"),
    ])
    assert summary.scored_count == 2
    assert summary.score is not None
    assert summary.not_evaluated_count == 1
    assert summary.unknown_count == 0
    assert summary.evaluation_coverage == 2 / 3
    assert summary.aggregation_state == "PARTIAL"


def test_not_applicable_is_excluded_from_coverage() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.PASS),
        evaluated("r2", RuleOutcome.PASS),
        evaluated("r3", RuleOutcome.NOT_APPLICABLE),
    ])
    assert summary.scored_count == 2
    assert summary.not_applicable_count == 1
    assert summary.evaluation_coverage == 1.0
    assert summary.aggregation_state == "EVALUATED"


def test_service_error_does_not_erase_available_score() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.PASS),
        evaluated("r2", RuleOutcome.PASS),
        evaluated("r3", RuleOutcome.SERVICE_ERROR),
    ])
    assert summary.scored_count == 2
    assert summary.score is not None
    assert summary.service_error_count == 1
    assert summary.evaluation_coverage == 2 / 3
    assert summary.aggregation_state == "SERVICE_ERROR"


def test_unknown_only_is_no_scored_items_not_no_evaluated_items() -> None:
    summary = summarize_aggregation([evaluated("r1", RuleOutcome.UNKNOWN)])
    assert summary.scored_count == 0
    assert summary.score is None
    assert summary.evaluation_coverage == 1.0
    assert summary.aggregation_state == "NO_SCORED_ITEMS"


def test_not_evaluated_only_is_no_evaluated_items() -> None:
    summary = summarize_aggregation([not_evaluated("r1")])
    assert summary.scored_count == 0
    assert summary.score is None
    assert summary.evaluation_coverage == 0.0
    assert summary.aggregation_state == "NO_EVALUATED_ITEMS"


def test_not_applicable_only_has_null_coverage_and_no_score() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.NOT_APPLICABLE),
    ])
    assert summary.scored_count == 0
    assert summary.score is None
    assert summary.evaluation_coverage is None
    assert summary.aggregation_state == "NOT_APPLICABLE"


def test_service_error_only_is_not_no_evaluated_items() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.SERVICE_ERROR),
    ])
    assert summary.scored_count == 0
    assert summary.score is None
    assert summary.evaluation_coverage == 0.0
    assert summary.aggregation_state == "SERVICE_ERROR"


def test_mixed_statuses_keep_score_coverage_and_counts_separate() -> None:
    summary = summarize_aggregation([
        evaluated("r1", RuleOutcome.PASS),
        evaluated("r2", RuleOutcome.FAIL),
        evaluated("r3", RuleOutcome.UNKNOWN),
        not_evaluated("r4"),
        evaluated("r5", RuleOutcome.NOT_APPLICABLE),
        evaluated("r6", RuleOutcome.SERVICE_ERROR),
    ])
    assert summary.pass_count == 1
    assert summary.fail_count == 1
    assert summary.scored_count == 2
    assert summary.denominator == 2
    assert summary.unknown_count == 1
    assert summary.not_evaluated_count == 1
    assert summary.not_applicable_count == 1
    assert summary.service_error_count == 1
    assert summary.evaluation_coverage == 3 / 5
    assert summary.score is not None
    assert summary.aggregation_state == "SERVICE_ERROR"
