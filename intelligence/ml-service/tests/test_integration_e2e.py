"""
End-to-end integration tests for the quality pipeline.

Rewritten for the canonical contract (Slice A Task 5):
Parse -> Validate -> Score -> Auto-Fix -> Regression -> Feedback, all using the
typed :mod:`app.quality.contracts` values and the single scorer/regression
signatures.
"""

from datetime import datetime
from typing import TypedDict

from app.autofix.iteration_loop import AutoFixIterationLoop
from app.config import settings
from app.feedback.feedback_collector import FeedbackCollector
from app.feedback.performance_analyzer import PerformanceAnalyzer
from app.feedback.performance_metrics import PerformanceTier
from app.parser.prompt_parser import parse_prompt
from app.quality.contracts import (
    EnhancedQualityReport,
    QualityReport,
    QualityStatus,
    RegressionDecision,
    RuleOutcome,
)
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer
from app.validation.regression_checker import RegressionChecker

RULESET = str(settings.rules_dir / "RULESET_1.0.yaml")

SAMPLE_PROMPT = """
Title: Kiko's Discovery

15-second video

## Characters
- Kiko: Curious, energetic

## Timeline
0.0-3.0 SEC: Kiko — spots a shiny box
3.0-6.0 SEC: Kiko — opens the box with excitement
6.0-9.0 SEC: Kiko — finds colorful ribbons inside
9.0-12.0 SEC: Kiko — pulls ribbons creating patterns
12.0-15.0 SEC: Kiko — ribbons form a rainbow arch
"""


def test_e2e_validation_workflow() -> None:
    parsed = parse_prompt(SAMPLE_PROMPT)
    ir = parsed.video_plan_ir
    assert len(ir["beats"]) == 5

    report = RuleEngine(RULESET).evaluate(ir)
    assert isinstance(report, QualityReport)
    assert 0 <= report.overall_score <= 100
    assert isinstance(report.status, QualityStatus)

    enhanced = QualityScorer().create_enhanced_report(report, ir, parsed.metadata)
    assert isinstance(enhanced, EnhancedQualityReport)
    assert enhanced.base_report is report
    # family_scores covers the families actually exercised by the ruleset;
    # the radar chart always presents the fixed 11-family layout.
    assert len(report.family_scores) >= 1
    assert len(enhanced.family_radar["labels"]) == 11
    assert len(report.evaluations) > 0
    assert len(enhanced.timeline_data["beats"]) == len(ir["beats"])
    assert enhanced.score_card["score"] == report.overall_score


def test_e2e_autofix_workflow() -> None:
    failed_prompt = (settings.test_cases_dir / "FAIL_001_KIKO_STATIC_STATE_DOMINANCE.md").read_text(
        encoding="utf-8"
    )
    loop = AutoFixIterationLoop(ruleset_version="1.0", max_iterations=3)
    result = loop.run(failed_prompt)

    # Canonical behavior: the loop never regresses the score, even when the
    # only available fix is a rejected REPLACE_CONCEPT.
    assert result.final_score >= result.initial_score
    for fix in result.applied_fixes:
        assert fix.accepted


def test_e2e_regression_checking() -> None:
    strong = SAMPLE_PROMPT
    weak = """
Title: Static

15-second video

## Characters
- Character: Test

## Timeline
0.0-5.0 SEC: Character — stands still
5.0-10.0 SEC: Character — keeps standing
10.0-15.0 SEC: Character — still standing
"""
    engine = RuleEngine(RULESET)
    report_strong = engine.evaluate(parse_prompt(strong).video_plan_ir)
    report_weak = engine.evaluate(parse_prompt(weak).video_plan_ir)

    checker = RegressionChecker()
    regression = checker.check(report_strong, report_weak)

    assert isinstance(regression.decision, RegressionDecision)
    # Degrading from a stronger to a weaker plan must not be ACCEPT.
    assert regression.decision is not RegressionDecision.ACCEPT


class _TestVideoFixture(TypedDict):
    video_id: str
    score: int
    status: str
    views: int
    retention: float
    tier: PerformanceTier


def test_e2e_feedback_loop() -> None:
    collector = FeedbackCollector()
    test_videos: list[_TestVideoFixture] = [
        {
            "video_id": "v1",
            "score": 95,
            "status": "RENDER_READY",
            "views": 3000,
            "retention": 75.0,
            "tier": PerformanceTier.EXCELLENT,
        },
        {
            "video_id": "v2",
            "score": 92,
            "status": "RENDER_READY",
            "views": 2500,
            "retention": 70.0,
            "tier": PerformanceTier.GOOD,
        },
        {
            "video_id": "v3",
            "score": 88,
            "status": "NEEDS_REVISION",
            "views": 1500,
            "retention": 65.0,
            "tier": PerformanceTier.GOOD,
        },
        {
            "video_id": "v4",
            "score": 85,
            "status": "NEEDS_REVISION",
            "views": 1200,
            "retention": 60.0,
            "tier": PerformanceTier.ACCEPTABLE,
        },
        {
            "video_id": "v5",
            "score": 78,
            "status": "NEEDS_REVISION",
            "views": 800,
            "retention": 50.0,
            "tier": PerformanceTier.ACCEPTABLE,
        },
        {
            "video_id": "v6",
            "score": 72,
            "status": "BLOCKED",
            "views": 500,
            "retention": 40.0,
            "tier": PerformanceTier.WEAK,
        },
        {
            "video_id": "v7",
            "score": 68,
            "status": "BLOCKED",
            "views": 300,
            "retention": 35.0,
            "tier": PerformanceTier.POOR,
        },
        {
            "video_id": "v8",
            "score": 90,
            "status": "RENDER_READY",
            "views": 400,
            "retention": 45.0,
            "tier": PerformanceTier.WEAK,
        },
        {
            "video_id": "v9",
            "score": 75,
            "status": "BLOCKED",
            "views": 2000,
            "retention": 68.0,
            "tier": PerformanceTier.GOOD,
        },
        {
            "video_id": "v10",
            "score": 93,
            "status": "RENDER_READY",
            "views": 2800,
            "retention": 72.0,
            "tier": PerformanceTier.EXCELLENT,
        },
    ]
    for video in test_videos:
        perf = collector.record_performance(
            video_id=video["video_id"],
            title=f"Test Video {video['video_id']}",
            platform="youtube",
            published_at=datetime.now(),
            duration_seconds=15,
            metrics={
                "views_7d": video["views"],
                "retention_avg_pct": video["retention"],
                "likes": int(video["views"] * 0.03),
                "comments": int(video["views"] * 0.01),
            },
            predicted_score=video["score"],
            predicted_status=video["status"],
        )
        perf.performance_tier = video["tier"]
        perf.compare_with_prediction(video["score"], video["status"])

    insights = PerformanceAnalyzer().analyze_performance_data(collector.performance_data, min_samples=5)
    assert insights.total_videos == len(test_videos)
    assert -1.0 <= insights.correlation_score_views <= 1.0


def test_e2e_full_pipeline() -> None:
    parsed = parse_prompt(SAMPLE_PROMPT)
    ir = parsed.video_plan_ir
    report = RuleEngine(RULESET).evaluate(ir)

    loop = AutoFixIterationLoop(ruleset_version="1.0", max_iterations=2)
    autofix_result = loop.run(SAMPLE_PROMPT)
    assert autofix_result.final_score >= report.overall_score

    collector = FeedbackCollector()
    perf = collector.record_performance(
        video_id="pipeline_test_001",
        title="Complete Pipeline Test",
        platform="youtube",
        published_at=datetime.now(),
        duration_seconds=15,
        metrics={"views_7d": 2000, "retention_avg_pct": 65.0, "likes": 60},
        prompt_id="prompt_001",
        predicted_score=autofix_result.final_score,
        predicted_status=str(autofix_result.final_status),
    )
    assert perf.predicted_score == autofix_result.final_score
    # The failed rules remain explicit RuleOutcome.FAIL values end to end.
    assert all(e.outcome is RuleOutcome.FAIL for e in report.failed_rules)
