"""Canonical rule-engine contract (Slice A Task 5).

The engine must emit :class:`RuleEvaluation` objects carrying an explicit
:class:`RuleOutcome` and a :class:`QualityReport` whose counts are derived.
A missing registered evaluator must fail closed as ``SERVICE_ERROR``.
"""

from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.contracts import (
    QualityReport,
    QualityStatus,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)
from app.rules.rule_engine import RuleEngine

RULESET = str(settings.rules_dir / "RULESET_1.0.yaml")

STATIC_PROMPT = """
Title: Static Hero

15-second video

## Characters
- Hero: Brave

## Timeline
0.0-5.0 SEC: Hero — stands still
5.0-10.0 SEC: Hero — continues standing
10.0-15.0 SEC: Hero — still standing
"""


def _report() -> QualityReport:
    ir = parse_prompt(STATIC_PROMPT).video_plan_ir
    return RuleEngine(RULESET).evaluate(ir)


def test_evaluate_returns_quality_report() -> None:
    report = _report()
    assert isinstance(report, QualityReport)
    assert isinstance(report.status, QualityStatus)
    assert all(isinstance(e, RuleEvaluation) for e in report.evaluations)


def test_outcomes_are_rule_outcome_enum() -> None:
    report = _report()
    for ev in report.evaluations:
        assert isinstance(ev.outcome, RuleOutcome)
        assert isinstance(ev.configured_severity, Severity)


def test_fail_outcome_is_not_boolean_truthiness() -> None:
    # RuleOutcome.FAIL must be an explicit enum member, compared by identity.
    # mypy statically narrows each bare `RuleOutcome.X` reference to its own
    # Literal type, so comparing two different literals "by identity" is
    # flagged as an always-true/non-overlapping check even though this is a
    # genuine runtime enum-identity assertion. Routing both operands through
    # a same-typed variable keeps the real `is`/`is not` semantics under test
    # without that false positive.
    fail_outcome: RuleOutcome = RuleOutcome.FAIL
    assert fail_outcome is not RuleOutcome.PASS
    # It is a StrEnum, so it equals its label but is not a plain bool.
    assert RuleOutcome.FAIL == "FAIL"
    assert not isinstance(RuleOutcome.FAIL, bool)


def test_derived_counts_match_evaluations() -> None:
    report = _report()
    expected_failed = [e for e in report.evaluations if e.outcome is RuleOutcome.FAIL]
    assert list(report.failed_rules) == expected_failed
    expected_blockers = sum(
        1
        for e in report.evaluations
        if e.outcome is RuleOutcome.FAIL and e.configured_severity is Severity.BLOCKER
    )
    assert report.blocker_count == expected_blockers


def test_missing_evaluator_fails_closed_as_service_error() -> None:
    engine = RuleEngine(RULESET)
    # Simulate an unregistered rule by removing a known evaluator.
    engine.evaluators.pop("BEAT_004", None)
    ir = parse_prompt(STATIC_PROMPT).video_plan_ir
    report = engine.evaluate(ir)

    beat_004 = next(e for e in report.evaluations if e.rule_id == "BEAT_004")
    assert beat_004.outcome is RuleOutcome.SERVICE_ERROR
    assert report.service_error_count >= 1
    # Fail closed: a service error must not be reported as render-ready.
    assert not report.is_render_ready
