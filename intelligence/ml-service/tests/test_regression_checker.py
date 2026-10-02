"""Canonical regression contract (Slice A Task 5).

``RegressionChecker.check`` is the single comparison entry point and returns a
``RegressionReport`` whose ``decision`` is a :class:`RegressionDecision`. The
legacy ``check_regression``/``decide_acceptance`` methods must not exist.
"""

from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.contracts import QualityReport, RegressionDecision
from app.rules.rule_engine import RuleEngine
from app.validation.regression_checker import RegressionChecker, RegressionSeverity

RULESET = str(settings.rules_dir / "RULESET_1.0.yaml")

PROMPT_V1 = """
Title: Test Prompt V1

15-second video

## Characters
- Character: Test

## Timeline
0.0-3.0 SEC: Character — spots a glowing orb
3.0-6.0 SEC: Character — pokes the orb and it splits
6.0-9.0 SEC: Character — the halves start spinning
9.0-12.0 SEC: Character — orbs form a bright ring
12.0-15.0 SEC: Character — ring bursts into confetti
"""

PROMPT_V2 = """
Title: Test Prompt V2

15-second video

## Characters
- Character: Test

## Timeline
0.0-5.0 SEC: Character — stands still
5.0-10.0 SEC: Character — keeps standing
10.0-15.0 SEC: Character — still standing
"""


def _report(prompt: str) -> QualityReport:
    ir = parse_prompt(prompt).video_plan_ir
    return RuleEngine(RULESET).evaluate(ir)


def test_check_returns_regression_decision() -> None:
    checker = RegressionChecker()
    report = checker.check(_report(PROMPT_V1), _report(PROMPT_V2), "v1", "v2")
    assert isinstance(report.decision, RegressionDecision)
    assert report.version_before == "v1"
    assert report.version_after == "v2"


def test_legacy_methods_removed() -> None:
    checker = RegressionChecker()
    assert not hasattr(checker, "check_regression")
    assert not hasattr(checker, "decide_acceptance")


def test_default_version_labels() -> None:
    checker = RegressionChecker()
    report = checker.check(_report(PROMPT_V1), _report(PROMPT_V1))
    assert report.version_before == "before"
    assert report.version_after == "after"
    # Comparing a report to itself must not be a rejection.
    assert report.decision is not RegressionDecision.REJECT


def test_regression_severity_string_contract() -> None:
    """``RegressionSeverity`` must behave as a plain string value.

    Pins the behavior relied on across the codebase (equality against raw
    strings and ``.value`` access for messages/API payloads) so that the
    underlying enum base class can be modernized without silently changing
    serialization or comparison semantics.
    """
    assert RegressionSeverity.CRITICAL == "CRITICAL"
    assert RegressionSeverity.WARNING == "WARNING"
    assert RegressionSeverity.CONCERN == "CONCERN"
    assert RegressionSeverity.CRITICAL.value == "CRITICAL"
    assert isinstance(RegressionSeverity.CRITICAL, str)
