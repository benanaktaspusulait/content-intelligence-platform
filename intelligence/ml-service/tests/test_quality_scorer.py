"""Canonical scorer contract (Slice A Task 5).

``create_enhanced_report`` has exactly one signature taking the quality report,
the video plan IR, and parser metadata, and returns an
:class:`EnhancedQualityReport` with a ``base_report`` plus typed
:class:`PriorityFix` entries.
"""

from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.contracts import (
    EnhancedQualityReport,
    FixStrategy,
    ParserMetadata,
    PriorityFix,
    QualityReport,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

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


def _enhanced() -> tuple[EnhancedQualityReport, QualityReport]:
    parsed = parse_prompt(STATIC_PROMPT)
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)
    return enhanced, report


def test_create_enhanced_report_wraps_base_report() -> None:
    enhanced, report = _enhanced()
    assert isinstance(enhanced, EnhancedQualityReport)
    assert enhanced.base_report is report
    assert enhanced.overall_score == report.overall_score
    assert isinstance(enhanced.parser_metadata, ParserMetadata)


def test_priority_fixes_are_typed() -> None:
    enhanced, _ = _enhanced()
    assert isinstance(enhanced.priority_fixes, tuple)
    assert all(isinstance(fix, PriorityFix) for fix in enhanced.priority_fixes)


def test_concept_006_fix_uses_replace_concept_strategy() -> None:
    enhanced, _ = _enhanced()
    concept_fixes = [f for f in enhanced.priority_fixes if f.rule_id == "CONCEPT_006"]
    # The static prompt yields too few consequences -> CONCEPT_006 fails.
    assert concept_fixes, "Expected CONCEPT_006 among priority fixes for a static prompt"
    assert concept_fixes[0].strategy is FixStrategy.REPLACE_CONCEPT


def test_timeline_data_keys_align_with_response_dto() -> None:
    enhanced, _ = _enhanced()
    beats = enhanced.timeline_data["beats"]
    assert beats, "Expected timeline beats"
    first = beats[0]
    for key in ("start_time", "end_time", "action", "consequence", "intensity", "is_new_consequence"):
        assert key in first
    for seg in enhanced.timeline_data["state_segments"]:
        assert {"state_id", "start_time", "end_time", "percentage"} <= set(seg)


def test_score_breakdowns_are_tuple() -> None:
    enhanced, _ = _enhanced()
    assert isinstance(enhanced.score_breakdowns, tuple)


def test_recommendation_generation_handles_list_diagnostics() -> None:
    evaluation = RuleEvaluation(
        rule_id="PRODUCIBILITY_003",
        rule_name="Generation Risk Tags",
        family="producibility",
        outcome=RuleOutcome.FAIL,
        configured_severity=Severity.CRITICAL,
        message="Cloth simulation risk detected.",
        actual_value=["CLOTH"],
        details={"recommendation": "Review cloth simulation risk."},
    )

    recommendation = QualityScorer()._get_rule_recommendation("PRODUCIBILITY_003", evaluation)

    assert recommendation == "Review cloth simulation risk."
