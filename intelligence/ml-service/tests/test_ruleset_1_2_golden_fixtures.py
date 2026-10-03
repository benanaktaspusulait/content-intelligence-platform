"""Golden fixture tests for RULESET 1.2's six new rules, built from
realistic Pompom-Hills-style concept narratives rather than minimal
synthetic dicts. Each test name states the narrative scenario and its
expected rule-level verdict, per the RULESET 1.2 design doc's golden
scenario table.
"""

from typing import Any
from unittest.mock import patch

from app.config import settings
from app.quality.contracts import RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine

RULESET_1_0 = str(settings.rules_dir / "RULESET_1.0.yaml")


def _engine() -> RuleEngine:
    return RuleEngine(RULESET_1_0)


def test_puddle_same_mechanic_escalating_depth_passes_concept_007() -> None:
    """Same mechanic + escalating consequences (toe/foot/both-feet depth
    increase) must PASS, regardless of how many distinct depth descriptions
    there are."""
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "coreMechanic": {
            "physicalRule": "Touching the puddle with more contact increases its depth.",
            "consistency": "consistent",
            "mechanicCount": 1,
        },
        "beats": [
            {"consequence": "toe touches puddle, ankle-deep"},
            {"consequence": "foot touches puddle, knee-deep"},
            {"consequence": "both feet touch puddle, waist-deep"},
        ],
    }
    with patch(
        "app.rules.rule_engine.count_independent_mechanics",
        return_value=(1, "All three beats escalate the same depth-contact rule."),
    ):
        evaluation = engine._evaluate_concept_007(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS


def test_puddle_plus_autonomous_chasing_blocks_concept_007() -> None:
    """Two unrelated physics rules (depth increase, then autonomous chasing)
    must FAIL at CRITICAL (exactly 2 mechanics)."""
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "coreMechanic": {
            "physicalRule": "Touching the puddle increases its depth.",
            "consistency": "consistent",
            "mechanicCount": 1,
        },
        "beats": [
            {"consequence": "toe touches puddle, ankle-deep"},
            {"consequence": "puddle grows legs and begins chasing the character on its own"},
        ],
    }
    with patch(
        "app.rules.rule_engine.count_independent_mechanics",
        return_value=(
            2,
            "Depth increase is the established rule; autonomous chasing is a new, unrelated rule.",
        ),
    ):
        evaluation = engine._evaluate_concept_007(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.CRITICAL


def test_push_harder_push_faster_same_consequence_fails_repetition_004() -> None:
    """PUSH -> PUSH HARDER -> PUSH FASTER with the same visual result is a
    dominant-ratio concern (all three normalize to one verb family) even
    though each is worded differently."""
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"isAttempt": True, "primaryVerb": "PUSH"},
            {"isAttempt": True, "primaryVerb": "PUSH"},
            {"isAttempt": True, "primaryVerb": "PUSH"},
            {"isAttempt": True, "primaryVerb": "TILT"},
        ],
    }
    evaluation = engine._evaluate_repetition_004(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL  # 3/4 = 0.75, above the 0.70 CRITICAL threshold


def test_same_verb_different_consequence_does_not_false_positive_alone() -> None:
    """REPETITION_004 alone must not treat same-verb-different-consequence as
    automatically bad when the ratio is still under threshold — the semantic
    duplicate-detection concern belongs to ATTEMPT_002, not this rule."""
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"isAttempt": True, "primaryVerb": "PUSH"},
            {"isAttempt": True, "primaryVerb": "TILT"},
            {"isAttempt": True, "primaryVerb": "CATCH"},
        ],
    }
    evaluation = engine._evaluate_repetition_004(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS


def test_fake_win_followed_by_same_size_repeat_is_weak_escalation() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"startTime": 0.0, "endTime": 8.0, "consequenceType": "new", "intensity": 5},
            {"startTime": 8.0, "endTime": 10.0, "consequenceType": "fake_win", "intensity": 3},
            {"startTime": 10.0, "endTime": 15.0, "consequenceType": "repeat", "intensity": 3},
        ],
    }
    evaluation = engine._evaluate_payoff_005(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.WARNING


def test_fake_win_followed_by_larger_same_rule_consequence_passes() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"startTime": 0.0, "endTime": 8.0, "consequenceType": "new", "intensity": 5},
            {"startTime": 8.0, "endTime": 10.0, "consequenceType": "fake_win", "intensity": 3},
            {"startTime": 10.0, "endTime": 15.0, "consequenceType": "escalation", "intensity": 9},
        ],
    }
    evaluation = engine._evaluate_payoff_005(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS


def test_biggest_event_early_weaker_ending_warns_payoff_004() -> None:
    """The biggest event happening at second 5 with a weaker ending at
    second 15 must FAIL (WARNING-severity, optimization-level, not a
    blocker)."""
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "finalPayoff": {"startsAt": 12.0, "isPeakIntensity": False},
        "beats": [
            {"startTime": 0.0, "endTime": 5.0, "intensity": 4},
            {"startTime": 5.0, "endTime": 6.0, "intensity": 10},  # the real peak, early
            {"startTime": 6.0, "endTime": 12.0, "intensity": 5},
            {"startTime": 12.0, "endTime": 15.0, "intensity": 6},  # weaker ending
        ],
    }
    evaluation = engine._evaluate_payoff_004(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.WARNING


def test_final_is_maximum_same_rule_consequence_passes_payoff_004() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "finalPayoff": {"startsAt": 12.0, "isPeakIntensity": True},
        "beats": [
            {"startTime": 0.0, "endTime": 5.0, "intensity": 4},
            {"startTime": 5.0, "endTime": 12.0, "intensity": 6},
            {"startTime": 12.0, "endTime": 15.0, "intensity": 10},
        ],
    }
    evaluation = engine._evaluate_payoff_004(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS
    assert evaluation.configured_severity is Severity.PASS


def test_hard_cut_no_loop_is_acceptable_payoff_006() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "finalPayoff": {"loopsToOpening": False, "loopQuality": "none", "isHardCut": True},
        "beats": [
            {
                "startTime": 12.0,
                "endTime": 15.0,
                "action": "slides into stack",
                "consequence": "dominoes fall",
            }
        ],
    }
    evaluation = engine._evaluate_payoff_006(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS
    assert evaluation.configured_severity is Severity.PASS


def test_natural_loop_is_strong_pass_bonus_payoff_006() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "finalPayoff": {"loopsToOpening": True, "loopQuality": "strong", "isHardCut": False},
        "beats": [
            {
                "startTime": 12.0,
                "endTime": 15.0,
                "action": "returns to starting pose",
                "consequence": "scene resets",
            }
        ],
    }
    evaluation = engine._evaluate_payoff_006(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS
    assert evaluation.configured_severity is Severity.PASS


def test_character_actively_solving_throughout_passes_beat_005() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "finalPayoff": {"startsAt": 12.0},
        "beats": [
            {
                "startTime": 0.0,
                "endTime": 4.0,
                "duration": 4.0,
                "isAttempt": True,
                "relatesToCoreProblem": True,
            },
            {
                "startTime": 4.0,
                "endTime": 8.0,
                "duration": 4.0,
                "isAttempt": True,
                "relatesToCoreProblem": True,
            },
            {
                "startTime": 8.0,
                "endTime": 12.0,
                "duration": 4.0,
                "isAttempt": True,
                "relatesToCoreProblem": True,
            },
        ],
    }
    evaluation = engine._evaluate_beat_005(ir, {})
    assert evaluation.outcome is RuleOutcome.PASS


def test_unresolved_problem_with_2s_unrelated_cutaway_fails_beat_005() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "finalPayoff": {"startsAt": 12.0},
        "beats": [
            {
                "startTime": 0.0,
                "endTime": 4.0,
                "duration": 4.0,
                "isAttempt": True,
                "relatesToCoreProblem": True,
            },
            {
                "startTime": 4.0,
                "endTime": 6.0,
                "duration": 2.0,
                "isAttempt": False,
                "relatesToCoreProblem": False,
            },
            {
                "startTime": 6.0,
                "endTime": 12.0,
                "duration": 6.0,
                "isAttempt": True,
                "relatesToCoreProblem": True,
            },
        ],
    }
    evaluation = engine._evaluate_beat_005(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL
    assert evaluation.configured_severity is Severity.CRITICAL


def test_grab_yank_semantic_duplicate_still_caught_by_attempt_002_alongside_repetition_004() -> None:
    """Design-doc regression check: a GRAB/YANK pair that ATTEMPT_002 already
    catches as a semantic duplicate (different wording, same underlying
    strategy) must still FAIL via ATTEMPT_002 even with REPETITION_004 now
    registered in the same ruleset -- the two rules are independent and must
    not interfere with each other. REPETITION_004 alone would not flag this
    case (each primaryVerb is distinct, so the dominant-ratio is low); the
    semantic-duplicate detection is ATTEMPT_002's job, not REPETITION_004's."""
    engine = _engine()
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "beats": [
            {"isAttempt": True, "primaryVerb": "GRAB", "action": "grabs", "consequence": "pulls object away"},
            {"isAttempt": True, "primaryVerb": "YANK", "action": "yanks", "consequence": "pulls object away"},
        ],
    }

    with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[(0, 1)]):
        attempt_002_evaluation = engine._evaluate_attempt_002(ir, {})
    repetition_004_evaluation = engine._evaluate_repetition_004(ir, {})

    assert attempt_002_evaluation.outcome is RuleOutcome.FAIL
    # REPETITION_004 sees 2 distinct verbs (GRAB, YANK) at a 0.5 dominant ratio,
    # which is below its own 0.55 WARNING threshold -- it correctly stays PASS,
    # confirming the two rules don't double-count or interfere with each other.
    assert repetition_004_evaluation.outcome is RuleOutcome.PASS
