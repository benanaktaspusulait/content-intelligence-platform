"""Tests for RuleOutcome.NOT_APPLICABLE and its QualityReport accessors.

NOT_APPLICABLE and UNKNOWN are deliberately distinct outcomes:
- UNKNOWN = the rule applies but evidence is currently missing (e.g. no
  rendered video yet for CONSISTENCY_002).
- NOT_APPLICABLE = the rule does not apply to this concept at all, by
  design (e.g. PAYOFF_005 on a concept with no fake-win beat).
Conflating them corrupts rule-coverage and rule-effectiveness measurement
downstream, per the RULESET 1.2 design doc.
"""

from app.quality.contracts import (
    QualityReport,
    QualityStatus,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)


def _evaluation(rule_id: str, outcome: RuleOutcome, severity: Severity = Severity.WARNING) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=rule_id,
        family="test_family",
        outcome=outcome,
        configured_severity=severity,
        message="test",
    )


def test_not_applicable_is_a_distinct_outcome_value() -> None:
    assert RuleOutcome.NOT_APPLICABLE == "NOT_APPLICABLE"
    not_applicable: RuleOutcome = RuleOutcome.NOT_APPLICABLE
    assert not_applicable is not RuleOutcome.UNKNOWN
    assert not_applicable is not RuleOutcome.PASS
    assert not_applicable is not RuleOutcome.FAIL


def test_quality_report_not_applicable_rules_accessor() -> None:
    evaluations = (
        _evaluation("PAYOFF_005", RuleOutcome.NOT_APPLICABLE),
        _evaluation("CONSISTENCY_002", RuleOutcome.UNKNOWN),
        _evaluation("HOOK_002", RuleOutcome.PASS, Severity.PASS),
    )
    report = QualityReport(
        overall_score=90.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={},
        evaluations=evaluations,
        ruleset_version="1.2",
        evaluated_at="2026-10-02T00:00:00Z",
    )

    assert len(report.not_applicable_rules) == 1
    assert report.not_applicable_rules[0].rule_id == "PAYOFF_005"
    assert report.not_applicable_count == 1


def test_quality_report_unknown_rules_accessor_is_separate_from_not_applicable() -> None:
    evaluations = (
        _evaluation("PAYOFF_005", RuleOutcome.NOT_APPLICABLE),
        _evaluation("CONSISTENCY_002", RuleOutcome.UNKNOWN),
    )
    report = QualityReport(
        overall_score=90.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={},
        evaluations=evaluations,
        ruleset_version="1.2",
        evaluated_at="2026-10-02T00:00:00Z",
    )

    assert len(report.unknown_rules) == 1
    assert report.unknown_rules[0].rule_id == "CONSISTENCY_002"
    assert report.unknown_count == 1
    # NOT_APPLICABLE must never show up in unknown_rules and vice versa.
    assert "PAYOFF_005" not in [e.rule_id for e in report.unknown_rules]
    assert "CONSISTENCY_002" not in [e.rule_id for e in report.not_applicable_rules]


def test_quality_report_zero_not_applicable_and_unknown_when_absent() -> None:
    evaluations = (_evaluation("HOOK_002", RuleOutcome.PASS, Severity.PASS),)
    report = QualityReport(
        overall_score=100.0,
        status=QualityStatus.RENDER_READY,
        family_scores={},
        evaluations=evaluations,
        ruleset_version="1.2",
        evaluated_at="2026-10-02T00:00:00Z",
    )

    assert report.not_applicable_count == 0
    assert report.unknown_count == 0
    assert report.not_applicable_rules == ()
    assert report.unknown_rules == ()
