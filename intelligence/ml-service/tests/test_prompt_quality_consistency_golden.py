"""Golden consistency regression for the pre-render Prompt Quality pipeline.

Case: "Luca Sticky Ball" (``fixtures/luca_sticky_ball_prompt.txt``), a real production
prompt. Its historical platform performance is deliberately NOT an input to any
assertion here. The prompt is used only because the runtime showed contradictions:
the timeline parsed as seven labelled beats while attempt-aware rules reported zero
attempts, zero active-character time and no evaluable escalation.

These tests assert CONSISTENCY (every consumer reads the same canonical evidence) and
the separation of creative assessment from evidence completeness. They do not assert
that the prompt is good or bad, and they call no LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.config import settings
from app.parser.prompt_parser import parse_prompt
from app.quality.canonical_evidence import attempt_beats, attempt_evidence
from app.quality.contracts import (
    ParseResult,
    QualityReport,
    QualityStatus,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer

FIXTURE = Path(__file__).parent / "fixtures" / "luca_sticky_ball_prompt.txt"

EXPECTED_LABELS = [
    "HARD HOOK",
    "REACTION",
    "FIRST ATTEMPT",
    "ESCALATION",
    "SECOND ATTEMPT",
    "FAKE RESOLUTION",
    "FINAL TWIST",
]
EXPECTED_ROLES = ["HOOK", "REACTION", "ATTEMPT", "ESCALATION", "ATTEMPT", "FAKE_RESOLUTION", "TWIST"]


@pytest.fixture(scope="module")
def parsed() -> ParseResult:
    return parse_prompt(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def engine() -> RuleEngine:
    return RuleEngine(str(settings.rules_dir / "RULESET_1.5.yaml"))


def _canonical(evaluation: Any) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=evaluation.rule_id,
        rule_name=evaluation.rule_name,
        family=evaluation.family,
        outcome=evaluation.outcome,
        configured_severity=evaluation.configured_severity,
        message=evaluation.message,
        actual_value=evaluation.actual_value,
        required_value=evaluation.required_value,
        threshold_value=evaluation.threshold_value,
        details=dict(evaluation.details),
    )


def _evaluation(
    rule_id: str,
    family: str,
    outcome: RuleOutcome,
    severity: Severity,
    message: str = "",
    actual_value: Any = None,
    **details: Any,
) -> RuleEvaluation:
    return RuleEvaluation(
        rule_id=rule_id,
        rule_name=rule_id,
        family=family,
        outcome=outcome,
        configured_severity=severity,
        message=message,
        actual_value=actual_value,
        details=dict(details),
    )


# --------------------------------------------------------------------------- parser


def test_timeline_is_parsed_as_seven_labelled_beats_with_canonical_roles(parsed: ParseResult) -> None:
    beats = parsed.video_plan_ir["beats"]
    assert [b["beatLabel"] for b in beats] == EXPECTED_LABELS
    assert [b["beatRole"] for b in beats] == EXPECTED_ROLES


def test_beat_action_is_the_described_action_not_the_structural_label(parsed: ParseResult) -> None:
    beats = parsed.video_plan_ir["beats"]
    assert beats[0]["action"] == "Luca has JUST thrown the red ball at the wooden wall."
    assert beats[2]["action"] == "Luca pulls harder."
    for beat in beats:
        assert beat["action"].upper() != beat["beatLabel"]
        assert not beat["consequence"].upper().startswith(beat["beatLabel"])
    assert parsed.video_plan_ir["hook"]["anomaly"] == beats[0]["action"]


def test_attempts_are_recognised_with_explicit_provenance(parsed: ParseResult) -> None:
    ir = parsed.video_plan_ir
    attempts = attempt_beats(ir)
    assert [b["beatLabel"] for b in attempts] == ["FIRST ATTEMPT", "SECOND ATTEMPT"]
    assert [b["attemptSource"] for b in attempts] == [
        "STRUCTURED_PLAN_ROLE",
        "STRUCTURED_PLAN_ROLE",
    ]
    escalation = next(b for b in ir["beats"] if b["beatRole"] == "ESCALATION")
    assert escalation["isAttempt"] is False
    assert escalation["attemptCandidate"]["source"] == "LEADING_VERB_INFERENCE"
    evidence = attempt_evidence(ir)
    assert evidence.count == 2
    assert evidence.active_attempt_count == 2
    assert evidence.verbs == ("PULLS", "CATCHES")
    assert evidence.strategy_families == ("PULL", "CATCH")
    assert evidence.distinct_strategy_count == 2
    assert evidence.active_seconds == pytest.approx(6.0)
    assert evidence.active_ratio == pytest.approx(0.4)


def test_author_declared_non_attempt_roles_are_never_inferred_as_attempts(parsed: ParseResult) -> None:
    by_role = {b["beatRole"]: b for b in parsed.video_plan_ir["beats"] if b["beatRole"] != "ATTEMPT"}
    for role in ("HOOK", "REACTION", "FAKE_RESOLUTION", "TWIST"):
        assert by_role[role]["isAttempt"] is False
        assert by_role[role]["attemptSource"] == "NONE"


# ------------------------------------------------------------ one evidence, every consumer


def test_every_attempt_consumer_reads_the_same_canonical_evidence(
    parsed: ParseResult, engine: RuleEngine
) -> None:
    ir = parsed.video_plan_ir
    evidence = attempt_evidence(ir)

    count_rule = engine._evaluate_attempt_001(ir, {})
    active_rule = engine._evaluate_char_002(ir, {})
    with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]):
        distinct_rule = engine._evaluate_attempt_002(ir, {})
    escalation_rule = engine._evaluate_escalation_005(ir, {})

    assert count_rule.actual_value == evidence.active_attempt_count
    assert active_rule.actual_value == pytest.approx(evidence.active_ratio)
    assert distinct_rule.actual_value == evidence.distinct_strategy_count
    assert escalation_rule.outcome.value in {"PASS", "FAIL", "UNKNOWN"}
    assert "Fewer than two attempts" not in escalation_rule.message

    for rule in (count_rule, active_rule, distinct_rule):
        assert "0 active" not in rule.message
        assert "only 0" not in rule.message.lower()


def test_assessment_dimensions_agree_with_the_rule_results(parsed: ParseResult, engine: RuleEngine) -> None:
    ir = parsed.video_plan_ir
    with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]):
        evaluations = tuple(
            _canonical(e)
            for e in (
                engine._evaluate_attempt_001(ir, {}),
                engine._evaluate_char_002(ir, {}),
                engine._evaluate_attempt_002(ir, {}),
                engine._evaluate_escalation_005(ir, {}),
            )
        )
    report = QualityReport(
        overall_score=80.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={},
        evaluations=evaluations,
        ruleset_version="1.5",
        evaluated_at="unknown",
    )

    assessment = build_pre_render_assessment(ir, parsed.metadata, report, "1.5")
    dimensions = {d["key"]: d for d in assessment["dimensions"]}

    attempts = dimensions["ATTEMPT_DIVERSITY"]
    assert "2 attempt(s)" in attempts["observed"]
    assert "2 distinct" in attempts["observed"]
    assert attempts["evidence_status"] == "AVAILABLE"

    escalation = dimensions["ESCALATION"]
    assert escalation["status"] != "UNKNOWN"
    assert "cannot be evaluated" not in escalation["summary"]


# ------------------------------------------- creative assessment vs evidence completeness


def _mixed_report(ir: dict[str, Any]) -> QualityReport:
    evaluations = (
        _evaluation("ATTEMPT_001", "concept_strength", RuleOutcome.PASS, Severity.PASS, actual_value=3),
        _evaluation("CHAR_002", "progression", RuleOutcome.PASS, Severity.PASS, actual_value=0.6),
        _evaluation("HOOK_002", "hook_strength", RuleOutcome.FAIL, Severity.CRITICAL, "weak opening"),
        _evaluation(
            "INSTANT_VISUAL_ABSURDITY_GATE",
            "hook_strength",
            RuleOutcome.FAIL,
            Severity.BLOCKER,
            "First-frame absurdity evidence is incomplete.",
            failureBasis="EVIDENCE_INCOMPLETE",
        ),
        _evaluation("CONSISTENCY_001", "consistency", RuleOutcome.UNKNOWN, Severity.WARNING, "not stated"),
    )
    return QualityReport(
        overall_score=70.0,
        status=QualityStatus.BLOCKED,
        family_scores={
            "concept_strength": 100.0,
            "progression": 100.0,
            "hook_strength": 20.0,
            "consistency": None,
        },
        evaluations=evaluations,
        ruleset_version="1.5",
        evaluated_at="unknown",
    )


def test_creative_grade_ignores_evidence_gaps_while_evidence_completeness_reports_them(
    parsed: ParseResult,
) -> None:
    ir = parsed.video_plan_ir
    assessment = build_pre_render_assessment(ir, parsed.metadata, _mixed_report(ir), "1.5")

    # The overall grade keeps its fail-closed meaning (a blocker exists)...
    assert assessment["grade"] == "INCOMPLETE"
    # ...but the creative grade only reflects creative failures (one CRITICAL).
    assert assessment["creative_grade"] == "D"

    completeness = assessment["evidence_completeness"]
    assert completeness["status"] == "INCOMPLETE"
    gaps = {g["rule_id"]: g["kind"] for g in completeness["gaps"]}
    assert gaps == {
        "INSTANT_VISUAL_ABSURDITY_GATE": "EVIDENCE_INCOMPLETE_FAIL",
        "CONSISTENCY_001": "UNKNOWN",
    }
    assert [f["family"] for f in completeness["unscored_families"]] == ["consistency"]
    assert completeness["canonical_evidence"]["attempts"]["count"] == 2


def test_family_without_evaluable_evidence_is_not_reported_as_a_creative_weakness(
    parsed: ParseResult,
) -> None:
    ir = parsed.video_plan_ir
    enhanced = QualityScorer().create_enhanced_report(_mixed_report(ir), ir, parsed.metadata)
    assert not any("Consistency" in weakness for weakness in enhanced.top_3_weaknesses)
    assert any("Hook Strength" in weakness for weakness in enhanced.top_3_weaknesses)


# ------------------------------------------------------------------- visual state shares


def test_visual_state_percentages_are_percent_of_duration_and_never_exceed_100(parsed: ParseResult) -> None:
    timeline = QualityScorer()._create_timeline_data(parsed.video_plan_ir)
    shares = [segment["percentage"] for segment in timeline["state_segments"]]

    assert shares == pytest.approx(
        [0.8 / 15 * 100, 2.2 / 15 * 100, 20.0, 20.0, 20.0, 2.0 / 15 * 100, 1.0 / 15 * 100]
    )
    assert sum(shares) == pytest.approx(100.0)
    assert max(shares) == pytest.approx(20.0)
    assert all(0.0 <= share <= 100.0 for share in shares)
