"""Canonical API conversion contract (Slice A Task 5).

The quality API conversion layer consumes the canonical contracts
(``enhanced.base_report`` + typed ``priority_fixes`` + DTO-aligned timeline)
and the ``/validate`` endpoint returns a well-formed report. The ``/auto-fix``
module imports cleanly now that the scorer/contract drift is repaired.
"""

from fastapi.testclient import TestClient

from app.api.quality import convert_quality_report
from app.config import settings
from app.main import app
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

RULESET = str(settings.rules_dir / "RULESET_1.0.yaml")

STATIC_PROMPT = (
    "Title: Static Hero\n\n15-second video\n\n## Characters\n- Hero: Brave\n\n"
    "## Timeline\n0.0-5.0 SEC: Hero — stands still\n5.0-10.0 SEC: Hero — keeps standing\n"
    "10.0-15.0 SEC: Hero — still standing\n"
)


def test_autofix_module_imports_without_lazy_hack() -> None:
    # The contract drift is gone, so a normal module-level import must succeed.
    from app.autofix.iteration_loop import AutoFixIterationLoop

    assert AutoFixIterationLoop is not None


def test_convert_quality_report_uses_base_report_and_typed_fixes() -> None:
    parsed = parse_prompt(STATIC_PROMPT)
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    assert response.overall_score == report.overall_score
    assert response.ruleset_version == "1.0"
    # Failed rules are rendered with their explicit FAIL outcome, never a
    # collapsed boolean that can't distinguish FAIL from UNKNOWN/SERVICE_ERROR.
    assert all(fr.outcome == "FAIL" for fr in response.failed_rules)
    # Timeline beats carried through the DTO-aligned conversion layer.
    assert len(response.timeline_data.beats) == len(parsed.video_plan_ir["beats"])


def test_validate_endpoint_returns_report() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/quality/validate",
        json={"prompt": STATIC_PROMPT, "ruleset_version": "latest"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"RENDER_READY", "NEEDS_REVISION", "BLOCKED", "SERVICE_ERROR"}
    assert "priority_fixes" in body
    assert "timeline_data" in body


def test_validate_unknown_ruleset_is_404_not_500() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/quality/validate",
        json={"prompt": STATIC_PROMPT, "ruleset_version": "nope-9.9"},
    )
    assert response.status_code == 404


def test_convert_quality_report_exposes_outcome_not_bool_result() -> None:
    parsed = parse_prompt(STATIC_PROMPT)
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    # Every failed rule now carries its explicit outcome string, not a
    # collapsed boolean that can't distinguish FAIL from UNKNOWN/SERVICE_ERROR.
    for fr in response.failed_rules:
        assert fr.outcome == "FAIL"
        assert not hasattr(fr, "result")


def test_convert_quality_report_separates_unknown_not_applicable_service_error() -> None:
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

    base_report = QualityReport(
        overall_score=70.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={"progression": 70.0},
        evaluations=(
            RuleEvaluation(
                rule_id="PAYOFF_005",
                rule_name="Fake Win Escalation",
                family="progression",
                outcome=RuleOutcome.NOT_APPLICABLE,
                configured_severity=Severity.WARNING,
                message="No fake-win beat present.",
            ),
            RuleEvaluation(
                rule_id="CONSISTENCY_002",
                rule_name="Character Continuity Lock",
                family="consistency",
                outcome=RuleOutcome.UNKNOWN,
                configured_severity=Severity.CRITICAL,
                message="No rendered video available yet.",
            ),
            RuleEvaluation(
                rule_id="GOAL_001",
                rule_name="Goal-Obstruction Clarity",
                family="concept_strength",
                outcome=RuleOutcome.SERVICE_ERROR,
                configured_severity=Severity.BLOCKER,
                message="LLM provider unavailable: OPENAI_API_KEY not set",
            ),
        ),
        ruleset_version="1.3",
        evaluated_at="2026-10-03T00:00:00Z",
    )
    enhanced = EnhancedQualityReport(
        base_report=base_report,
        score_breakdowns=(
            ScoreBreakdown(
                family="progression",
                score=70.0,
                weight=0.11,
                weighted_contribution=7.7,
                rules_passed=0,
                rules_failed=0,
                rules_warning=0,
            ),
        ),
        score_card={
            "score": 70.0,
            "label": "Acceptable",
            "color": "yellow",
            "status": "NEEDS_REVISION",
            "blockers": 0,
            "criticals": 0,
            "warnings": 0,
            "passes": 0,
            "is_render_ready": False,
        },
        timeline_data={"duration": 15.0, "beats": [], "consequence_markers": [], "state_segments": []},
        family_radar={"labels": [], "scores": [], "thresholds": {}},
        top_3_strengths=(),
        top_3_weaknesses=(),
        priority_fixes=(),
        parser_metadata=ParserMetadata(confidence=1.0),
    )

    response = convert_quality_report(enhanced, "1.3")

    assert len(response.unknown_rules) == 1
    assert response.unknown_rules[0].rule_id == "CONSISTENCY_002"
    assert response.unknown_rules[0].outcome == "UNKNOWN"

    assert len(response.not_applicable_rules) == 1
    assert response.not_applicable_rules[0].rule_id == "PAYOFF_005"
    assert response.not_applicable_rules[0].outcome == "NOT_APPLICABLE"

    assert len(response.service_errors) == 1
    assert response.service_errors[0].rule_id == "GOAL_001"
    assert response.service_errors[0].outcome == "SERVICE_ERROR"

    # None of these three leak into failed_rules (which stays FAIL-only).
    failed_ids = {fr.rule_id for fr in response.failed_rules}
    assert failed_ids.isdisjoint({"PAYOFF_005", "CONSISTENCY_002", "GOAL_001"})
