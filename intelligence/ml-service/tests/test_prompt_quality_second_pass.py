"""Second-pass semantic/policy regressions for the pre-render quality pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import (
    attempt_evidence,
    strategy_family_for_beat,
)
from app.quality.contracts import QualityReport, QualityStatus, RuleEvaluation, RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine

FIXTURE = Path(__file__).parent / "fixtures" / "luca_sticky_ball_prompt.txt"
RULESET = str(settings.rules_dir / "RULESET_1.5.yaml")


def _engine() -> RuleEngine:
    return RuleEngine(RULESET)


def _ir(timeline: str, *, duration: float = 15.0) -> dict:
    result = parse_prompt(
        f"Title: Synthetic\n\n{duration:g}-second video\n\n"
        "## Characters\n- Mimi\n\n## Timeline\n" + timeline
    )
    return result.video_plan_ir


def _report(ir: dict, evaluations: tuple[RuleEvaluation, ...]) -> QualityReport:
    return QualityReport(
        overall_score=75.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={"concept_strength": 75.0},
        evaluations=evaluations,
        ruleset_version="1.5",
        evaluated_at="unknown",
    )


def test_luca_escalation_is_escalation_evidence_but_not_a_new_attempt() -> None:
    ir = parse_prompt(FIXTURE.read_text(encoding="utf-8")).video_plan_ir
    evidence = attempt_evidence(ir)
    escalation = next(beat for beat in ir["beats"] if beat["beatRole"] == "ESCALATION")

    assert evidence.active_attempt_count == 2
    assert evidence.distinct_strategy_count == 2
    assert escalation["isAttempt"] is False
    assert escalation["escalationEvidence"]["newTarget"] is True
    assert escalation["escalationEvidence"]["reason"]


def test_repeated_pull_wording_is_one_strategy_family() -> None:
    ir = _ir(
        "0.0-5.0 SEC — FIRST ATTEMPT\nMimi pulls the rope.\n"
        "5.0-10.0 SEC — SECOND ATTEMPT\nMimi yanks the rope harder.\n"
        "10.0-15.0 SEC — THIRD ATTEMPT\nMimi tugs the rope from another angle.\n"
    )
    evidence = attempt_evidence(ir)
    assert evidence.active_attempt_count == 3
    assert evidence.strategy_families == ("PULL", "PULL", "PULL")
    assert evidence.distinct_strategy_count == 1
    assert [item["distinctFromPreviousAttempt"] for item in evidence.attempts] == [True, False, False]

    with patch("app.rules.rule_engine.find_duplicate_strategy_pairs") as duplicate_check:
        result = _engine()._evaluate_attempt_002(ir, {})
    assert result.outcome is RuleOutcome.FAIL
    assert result.actual_value == 1
    duplicate_check.assert_not_called()


def test_three_different_strategy_families_are_distinct_without_verb_counting() -> None:
    ir = _ir(
        "0.0-5.0 SEC — FIRST ATTEMPT\nMimi pulls the rope.\n"
        "5.0-10.0 SEC — SECOND ATTEMPT\nMimi pushes the box.\n"
        "10.0-15.0 SEC — THIRD ATTEMPT\nMimi squeezes the cup.\n"
    )
    evidence = attempt_evidence(ir)
    assert evidence.strategy_families == ("PULL", "PUSH", "SQUEEZE")
    assert evidence.distinct_strategy_count == 3

    with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]) as duplicate_check:
        result = _engine()._evaluate_attempt_002(ir, {})
    assert result.outcome is RuleOutcome.PASS
    assert result.actual_value == 3
    duplicate_check.assert_called_once()


def test_escalation_rule_can_pass_from_new_target_without_new_attempt() -> None:
    ir = _ir(
        "0.0-5.0 SEC — FIRST ATTEMPT\nMimi pulls the rope.\n"
        "5.0-10.0 SEC — ESCALATION\nThe rope pulls the box, and the whole wall flexes.\n"
        "10.0-15.0 SEC — FINAL TWIST\nThe box sticks to Mimi's cheek.\n"
    )
    result = _engine()._evaluate_escalation_005(ir, {})
    assert result.outcome is RuleOutcome.PASS
    assert result.details["evidence"]["new_target"] is True


def test_escalation_without_comparable_evidence_is_unknown_not_pass() -> None:
    ir = _ir("0.0-15.0 SEC — REACTION\nMimi watches the rope.\n")
    result = _engine()._evaluate_escalation_005(ir, {})
    assert result.outcome is RuleOutcome.UNKNOWN


def test_goal_evidence_is_implicit_but_observable_for_sticky_ball() -> None:
    ir = parse_prompt(FIXTURE.read_text(encoding="utf-8")).video_plan_ir
    goal = ir["goalEvidence"]
    assert goal["goalExplicitness"] == "IMPLICIT_BUT_OBSERVABLE"
    assert goal["goalType"] == "RETRIEVE_OR_CONTROL_OBJECT"
    assert goal["targetObject"]
    assert goal["obstruction"]


def test_unsupported_goal_remains_a_creative_failure() -> None:
    ir = _ir(
        "0.0-5.0 SEC — FIRST ATTEMPT\nMimi waves at the empty sky.\n"
        "5.0-10.0 SEC — SECOND ATTEMPT\nMimi smiles at the empty sky.\n"
        "10.0-15.0 SEC — THIRD ATTEMPT\nMimi waits.\n"
    )
    rule = _engine().ruleset["rules"]
    goal_rule = next(item for item in rule if item["id"] == "GOAL_001")
    with patch("app.rules.rule_engine.check_goal_is_natural", return_value=(False, "No observable local goal.")):
        result = _engine()._evaluate_goal_001(ir, goal_rule)
    assert result.outcome is RuleOutcome.FAIL
    assert result.configured_severity is Severity.BLOCKER


def test_textual_first_frame_pass_is_not_visual_verification() -> None:
    ir = parse_prompt(FIXTURE.read_text(encoding="utf-8")).video_plan_ir
    assessment = build_pre_render_assessment(
        ir,
        parse_prompt(FIXTURE.read_text(encoding="utf-8")).metadata,
        _report(
            ir,
            (
                RuleEvaluation(
                    rule_id="INSTANT_VISUAL_ABSURDITY_GATE",
                    rule_name="Instant Visual Absurdity Gate",
                    family="hook_strength",
                    outcome=RuleOutcome.FAIL,
                    configured_severity=Severity.BLOCKER,
                    message="missing image",
                    details={"failureBasis": "EVIDENCE_INCOMPLETE"},
                ),
            ),
        ),
    )
    assert assessment["first_frame"]["textual_intent"]["status"] == "PASS"
    assert assessment["first_frame"]["visual_verification"]["status"] == "PENDING"
    assert assessment["render_authorization"]["status"] == "BLOCKED_PENDING_EVIDENCE"
    assert assessment["prompt_stage"] == "READY_FOR_FIRST_FRAME"


def test_vague_first_frame_text_fails_textual_precheck() -> None:
    ir = _ir("0.0-15.0 SEC — HARD HOOK\nMimi walks into a sunny garden.\n")
    assessment = build_pre_render_assessment(
        ir,
        parse_prompt("Title: Synthetic\n\n15-second video\n\n## Timeline\n0.0-15.0 SEC: Mimi walks into a sunny garden").metadata,
        _report(ir, ()),
        "1.5",
    )
    assert assessment["first_frame"]["textual_intent"]["status"] == "FAIL"
    assert assessment["prompt_stage"] == "BLOCKED_CREATIVE_FAILURE"


def test_missing_family_score_is_nullable_and_status_based() -> None:
    engine = _engine()
    unknown = RuleEvaluation(
        rule_id="CONSISTENCY_001",
        rule_name="Physics Rule Consistency",
        family="consistency",
        outcome=RuleOutcome.UNKNOWN,
        configured_severity=Severity.WARNING,
        message="missing",
    )
    scores = engine._calculate_family_scores([unknown])
    assessments = engine._calculate_family_assessments([unknown])
    assert scores["consistency"] is None
    assert assessments["consistency"]["status"] == "UNKNOWN"
    assert assessments["consistency"]["score"] is None


def test_fake_resolution_is_not_automatic_consistency_failure() -> None:
    ir = _ir(
        "0.0-5.0 SEC — FIRST ATTEMPT\nMimi pulls the rope.\n"
        "5.0-10.0 SEC — FAKE RESOLUTION\nThe rope behaves normally for a moment.\n"
        "10.0-15.0 SEC — FINAL TWIST\nThe rope pulls Mimi back again.\n"
    )
    fake = next(beat for beat in ir["beats"] if beat["beatRole"] == "FAKE_RESOLUTION")
    assert fake["consequenceType"] == "fake_win"
    assert ir["coreMechanic"]["abnormalProperty"]
    assert ir["coreMechanic"]["recurrence"] is True


def test_generation_audit_exposes_per_attempt_concrete_risks() -> None:
    ir = parse_prompt(FIXTURE.read_text(encoding="utf-8")).video_plan_ir
    result = _engine()._evaluate_generation_executable_attempts(ir, {})
    attempts = result.details["attempts"]
    assert {item["riskLevel"] for item in attempts} <= {"LOW", "MODERATE", "HIGH"}
    assert all(item["risks"] for item in attempts)
    assert result.details["policy"] == "CRITICAL_ON_PARTIAL_UNEXECUTABILITY"
