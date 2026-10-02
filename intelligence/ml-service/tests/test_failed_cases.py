"""
Validate the quality engine against the three documented failed cases.

Rewritten for the canonical quality contract (Slice A Task 5):
* prompts come from ``settings.test_cases_dir`` (the real shared data root),
  not a hardcoded ``ml-service/data`` path that does not exist;
* the engine is loaded from ``settings.rules_dir``;
* rule results are the explicit :class:`RuleOutcome` enum (no boolean/str
  truthiness), and the scorer is called with its single 3-argument signature.
"""

from pathlib import Path

import pytest

from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.contracts import (
    EnhancedQualityReport,
    FixStrategy,
    QualityReport,
    QualityStatus,
    RuleOutcome,
)
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

RULESET = str(settings.rules_dir / "RULESET_1.0.yaml")


def load_test_case(filename: str) -> str:
    """Load a documented failed-case prompt from the shared data root."""
    test_file = Path(settings.test_cases_dir) / filename
    return test_file.read_text(encoding="utf-8")


def _evaluate(filename: str) -> tuple[QualityReport, EnhancedQualityReport]:
    parsed = parse_prompt(load_test_case(filename))
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)
    return report, enhanced


def _failed_ids(report: QualityReport) -> set[str]:
    return {e.rule_id for e in report.evaluations if e.outcome is RuleOutcome.FAIL}


@pytest.mark.parametrize(
    "filename",
    [
        "FAIL_001_KIKO_STATIC_STATE_DOMINANCE.md",
        "FAIL_002_OPA_REPETITIVE_OPEN_CLOSE.md",
        "FAIL_003_ARDA_REPETITIVE_SHARPEN_DRAW.md",
    ],
)
def test_documented_failure_is_blocked(filename: str) -> None:
    report, enhanced = _evaluate(filename)

    # Every documented failure case must be caught as structurally unsound.
    assert report.status is QualityStatus.BLOCKED
    assert report.overall_score < 80

    # CONCEPT_006 (insufficient consequence capacity) is the shared root cause,
    # and its only sound remedy is concept replacement, not a controlled patch.
    assert "CONCEPT_006" in _failed_ids(report)
    concept_fix = next(f for f in enhanced.priority_fixes if f.rule_id == "CONCEPT_006")
    assert concept_fix.strategy is FixStrategy.REPLACE_CONCEPT


def test_failed_rules_use_explicit_outcome_enum() -> None:
    report, _ = _evaluate("FAIL_001_KIKO_STATIC_STATE_DOMINANCE.md")
    # Failed rules are those whose outcome is explicitly FAIL (identity check),
    # never "falsy" strings or booleans.
    assert report.failed_rules
    assert all(e.outcome is RuleOutcome.FAIL for e in report.failed_rules)
    assert report.blocker_count >= 1
