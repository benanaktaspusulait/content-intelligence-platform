"""Tests for GENERATION_EXECUTABLE_ATTEMPTS.

Covers the four scenarios from the rule's design spec (positive, two
negatives, positive-with-character-performance), plus the deterministic
pre-filter layers (abstract-intent keywords, vague-magnitude phrasing, beat
budget) and the service-error/fail-closed path, following the same
direct-method-call test style used throughout test_rule_engine_new_rules.py
and test_ruleset_1_3_new_rules.py.
"""

from typing import Any
from unittest.mock import patch

from app.config import settings
from app.quality.contracts import RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine

RULESET_1_0 = str(settings.rules_dir / "RULESET_1.0.yaml")


def _engine() -> RuleEngine:
    return RuleEngine(RULESET_1_0)


def _minimal_ir(**overrides: Any) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "characters": {"primary": "Arda"},
        "beats": [],
        "finalPayoff": {},
        "coreMechanic": {"physicalRule": "test rule", "consistency": "consistent"},
        "setting": {"mainProps": []},
        "producibility": {"overallComplexity": "low"},
    }
    ir.update(overrides)
    return ir


def _all_executable_judgments(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"index": i, "is_executable": True, "problem": "", "suggested_rewrite": ""}
        for i in range(len(attempts))
    ]


class TestFewerThanTwoAttempts:
    def test_pass_without_calling_llm_when_zero_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[])
        with patch("app.rules.rule_engine.check_attempts_are_generation_executable") as mock_check:
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        mock_check.assert_not_called()

    def test_pass_without_calling_llm_when_one_attempt(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            beats=[{"isAttempt": True, "primaryVerb": "STEP", "action": "steps forward", "consequence": "x"}]
        )
        with patch("app.rules.rule_engine.check_attempts_are_generation_executable") as mock_check:
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        mock_check.assert_not_called()


class TestPositiveCase:
    def test_pass_when_all_attempts_are_concrete_action_result_pairs(self) -> None:
        """From the rule's design spec: three literal, generation-friendly
        attempts (front foot step, side step, backward heel step), each with
        an explicit visible action-result pair."""
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": "STEP",
                "action": "lowers his right foot toward the box",
                "consequence": "box slides right one box-width, foot lands on floor",
            },
            {
                "isAttempt": True,
                "primaryVerb": "SIDE_STEP",
                "action": "walks around to the opposite side and lowers his left foot",
                "consequence": "box slides left one box-width, foot lands on floor",
            },
            {
                "isAttempt": True,
                "primaryVerb": "BACKWARD_HEEL",
                "action": "turns his back and lowers his heel backward",
                "consequence": "box slides forward one box-width, heel lands on floor",
            },
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=_all_executable_judgments(beats),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.configured_severity is Severity.PASS


class TestNegativeCaseAbstractStrategies:
    def test_blocker_fail_when_all_attempts_are_abstract_and_llm_confirms(self) -> None:
        """From the rule's design spec: four attempts that are semantically
        different on paper (confident retry, outsmart, block escape route,
        clever angle) but lack deterministic visual choreography. Expected:
        HIGH or CRITICAL per the spec; mapped here to this engine's severity
        scale as CRITICAL (some attempts unexecutable) or BLOCKER (all
        unexecutable) -- this fixture has all four fail, so BLOCKER."""
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": "RETRY",
                "action": "confidently tries again",
                "consequence": "",
            },
            {
                "isAttempt": True,
                "primaryVerb": "OUTSMART",
                "action": "tries to outsmart the box",
                "consequence": "",
            },
            {
                "isAttempt": True,
                "primaryVerb": "BLOCK",
                "action": "positions himself to block the box's escape direction",
                "consequence": "",
            },
            {
                "isAttempt": True,
                "primaryVerb": "ANGLE",
                "action": "approaches cleverly from another angle",
                "consequence": "",
            },
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        all_unexecutable = [
            {
                "index": i,
                "is_executable": False,
                "problem": "Describes intention or spatial strategy, not a deterministic physical action.",
                "suggested_rewrite": "character moves to a specific side and lowers a foot toward the box",
            }
            for i in range(len(beats))
        ]
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=all_unexecutable,
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.BLOCKER

    def test_critical_fail_when_deterministic_abstract_intent_keyword_matches(self) -> None:
        """The deterministic pre-filter alone (block the escape route) must
        flag CRITICAL even if the LLM judges the attempts individually
        executable -- abstract-intent language is a standalone signal, not
        gated behind the LLM call agreeing."""
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": "STEP",
                "action": "lowers right foot toward the box",
                "consequence": "box slides right",
            },
            {
                "isAttempt": True,
                "primaryVerb": "BLOCK",
                "action": "positions himself to block the escape route",
                "consequence": "box has nowhere to go",
            },
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=_all_executable_judgments(beats),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        beats = [
            {"isAttempt": True, "primaryVerb": "A", "action": "a", "consequence": "a"},
            {"isAttempt": True, "primaryVerb": "B", "action": "b", "consequence": "b"},
        ]
        ir = _minimal_ir(beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            side_effect=SemanticCheckServiceError("boom"),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR
        assert evaluation.configured_severity is Severity.BLOCKER


class TestNegativeCaseBeatBudget:
    def test_warning_for_too_many_attempts_in_too_little_duration(self) -> None:
        """From the rule's design spec: four attempts in 8 seconds, each
        requiring repositioning + reaction + setup + physical interaction.
        Expected: WARNING/HIGH for beat load -- mapped here as WARNING, since
        each attempt individually is judged executable by the LLM; only the
        timing budget is under pressure."""
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": v,
                "action": f"{v.lower()} action",
                "consequence": f"{v.lower()} result",
            }
            for v in ["STEP", "SIDE_STEP", "PUSH", "LIFT"]
        ]
        ir = _minimal_ir(metadata={"duration": 8.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=_all_executable_judgments(beats),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING

    def test_pass_when_attempt_count_fits_duration_comfortably(self) -> None:
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": v,
                "action": f"{v.lower()} action with explicit result",
                "consequence": f"{v.lower()} result",
            }
            for v in ["STEP", "SIDE_STEP", "PUSH"]
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=_all_executable_judgments(beats),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS


class TestVagueMagnitudePhrasing:
    def test_warning_when_primary_gag_movement_is_vague(self) -> None:
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": "STEP",
                "action": "lowers right foot toward the box",
                "consequence": "box slightly moves",
            },
            {
                "isAttempt": True,
                "primaryVerb": "SIDE_STEP",
                "action": "lowers left foot from the other side",
                "consequence": "box slides one box-width left",
            },
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=_all_executable_judgments(beats),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING


class TestPositiveCaseWithCharacterPerformance:
    def test_pass_when_performance_cue_accompanies_explicit_physical_action(self) -> None:
        """From the rule's design spec: a tiny confident smile is an
        intention cue, but the primary physical action (turns back, two
        backward steps, lowers heel) remains explicit -- this must PASS,
        not be penalized for the performance detail."""
        engine = _engine()
        beats = [
            {
                "isAttempt": True,
                "primaryVerb": "APPROACH",
                "action": "lowers right foot toward the box",
                "consequence": "box slides right one box-width",
            },
            {
                "isAttempt": True,
                "primaryVerb": "BACKWARD_HEEL",
                "action": (
                    "turns his back to the box and gives a tiny confident smile, then takes two "
                    "small backward steps and lowers his heel"
                ),
                "consequence": "the box slides away before contact",
            },
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.check_attempts_are_generation_executable",
            return_value=_all_executable_judgments(beats),
        ):
            evaluation = engine._evaluate_generation_executable_attempts(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
