"""Tests for the RULESET_1.3 new rule evaluators: GOAL_001, CONCEPT_008,
PROGRESSION_006, ESCALATION_005, HOOK_004, PERFORMANCE_001, PRODUCIBILITY_003.

Each test builds a minimal video_plan_ir dict containing only the fields the
evaluator under test reads, calls the engine's internal `_evaluate_*` method
directly (matching the direct-method-call style used throughout
test_rule_engine_new_rules.py), and asserts on the returned RuleEvaluation.
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
        "hook": {
            "anomaly": "box slides away",
            "startsMidAction": True,
            "visualStrength": 5,
            "soundOffClear": True,
        },
        "beats": [],
        "finalPayoff": {},
        "coreMechanic": {"physicalRule": "test rule", "consistency": "consistent"},
        "setting": {"mainProps": []},
        "producibility": {"overallComplexity": "low"},
    }
    ir.update(overrides)
    return ir


class TestGoal001GoalObstructionClarity:
    def test_pass_when_llm_confirms_natural_goal(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "reaches for slipper"}])
        with patch(
            "app.rules.rule_engine.check_goal_is_natural",
            return_value=(True, "Wanting to put on a slipper is an ordinary goal."),
        ):
            evaluation = engine._evaluate_goal_001(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_blocker_fail_when_llm_reports_arbitrary_goal(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "drops pencil repeatedly to test floating"}])
        with patch(
            "app.rules.rule_engine.check_goal_is_natural",
            return_value=(False, "No believable reason to keep trying; a magic-demo setup."),
        ):
            evaluation = engine._evaluate_goal_001(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.BLOCKER

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "reaches for cup"}])
        with patch(
            "app.rules.rule_engine.check_goal_is_natural",
            side_effect=SemanticCheckServiceError("boom"),
        ):
            evaluation = engine._evaluate_goal_001(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR
        assert evaluation.configured_severity is Severity.BLOCKER


class TestConcept008RuleReadability:
    def test_pass_when_llm_confirms_predictable_rule(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"consequence": "frame tilts sideways"}])
        with patch(
            "app.rules.rule_engine.check_rule_is_predictable",
            return_value=(True, "Simple one-trigger-one-consequence pattern."),
        ):
            evaluation = engine._evaluate_concept_008(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_critical_fail_when_llm_reports_unlearnable_rule(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"consequence": "object moves based on angle and speed combo"}])
        with patch(
            "app.rules.rule_engine.check_rule_is_predictable",
            return_value=(False, "Too many interacting factors to learn from observation."),
        ):
            evaluation = engine._evaluate_concept_008(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        ir = _minimal_ir(beats=[{"consequence": "x"}])
        with patch(
            "app.rules.rule_engine.check_rule_is_predictable",
            side_effect=SemanticCheckServiceError("boom"),
        ):
            evaluation = engine._evaluate_concept_008(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR


class TestProgression006ActivityIsNotProgression:
    def test_pass_with_fewer_than_two_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"isAttempt": True, "primaryVerb": "PUSH"}])
        evaluation = engine._evaluate_progression_006(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_critical_fail_when_verb_root_dominates(self) -> None:
        engine = _engine()
        beats = [
            {"isAttempt": True, "primaryVerb": v}
            for v in ["PUSH", "PUSH_HARDER", "PUSH_FROM_LEFT", "PUSH_WITH_BOTH_HANDS"]
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_progression_006(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL
        assert evaluation.details["dominant_root"] == "PUSH"

    def test_pass_when_verb_roots_are_varied(self) -> None:
        engine = _engine()
        beats = [{"isAttempt": True, "primaryVerb": v} for v in ["CATCH", "BLOCK", "TILT", "CONTAIN"]]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_progression_006(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_never_reaches_blocker(self) -> None:
        engine = _engine()
        beats = [{"isAttempt": True, "primaryVerb": "PUSH"} for _ in range(10)]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_progression_006(ir, {})
        assert evaluation.configured_severity in (Severity.PASS, Severity.CRITICAL)


class TestEscalation005MeaningfulAttemptEscalation:
    def test_pass_with_fewer_than_two_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"isAttempt": True, "intensity": 3}])
        evaluation = engine._evaluate_escalation_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_warning_fail_when_intensity_is_flat(self) -> None:
        engine = _engine()
        beats = [
            {"isAttempt": True, "intensity": 4},
            {"isAttempt": True, "intensity": 4},
            {"isAttempt": True, "intensity": 4},
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_escalation_005(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING

    def test_warning_fail_when_intensity_declines(self) -> None:
        engine = _engine()
        beats = [
            {"isAttempt": True, "intensity": 7},
            {"isAttempt": True, "intensity": 3},
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_escalation_005(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING

    def test_pass_when_intensity_rises(self) -> None:
        engine = _engine()
        beats = [
            {"isAttempt": True, "intensity": 3},
            {"isAttempt": True, "intensity": 5},
            {"isAttempt": True, "intensity": 8},
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_escalation_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_never_exceeds_warning(self) -> None:
        engine = _engine()
        beats = [{"isAttempt": True, "intensity": 9}, {"isAttempt": True, "intensity": 1}]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_escalation_005(ir, {})
        assert evaluation.configured_severity in (Severity.PASS, Severity.WARNING)


class TestHook004OpeningProblemLegibility:
    def test_pass_when_llm_confirms_legible_opening(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            hook={"anomaly": "cup slides away"},
            beats=[{"action": "reaches for cup", "consequence": "cup slides away from hand"}],
        )
        with patch(
            "app.rules.rule_engine.check_opening_problem_legible",
            return_value=(True, "Goal and obstruction both immediately legible."),
        ):
            evaluation = engine._evaluate_hook_004(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_critical_fail_when_llm_reports_illegible_opening(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            hook={"anomaly": "something odd happens"},
            beats=[{"action": "stands still", "consequence": "object behaves strangely"}],
        )
        with patch(
            "app.rules.rule_engine.check_opening_problem_legible",
            return_value=(False, "Odd visual event with no indication of character goal."),
        ):
            evaluation = engine._evaluate_hook_004(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "x", "consequence": "y"}])
        with patch(
            "app.rules.rule_engine.check_opening_problem_legible",
            side_effect=SemanticCheckServiceError("boom"),
        ):
            evaluation = engine._evaluate_hook_004(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR


class TestPerformance001CuteEmotionalReadability:
    def test_pass_when_llm_confirms_readable_performance(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "curious tilt of head", "consequence": "box wobbles"}])
        with patch(
            "app.rules.rule_engine.check_character_performance_readable",
            return_value=(True, "Reads as curious and engaged throughout."),
        ):
            evaluation = engine._evaluate_performance_001(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_warning_fail_when_llm_reports_unreadable_performance(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "stares blankly", "consequence": "nothing changes"}])
        with patch(
            "app.rules.rule_engine.check_character_performance_readable",
            return_value=(False, "Reads as blank/robotic throughout, not sympathetic."),
        ):
            evaluation = engine._evaluate_performance_001(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING

    def test_never_exceeds_warning_on_fail(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "x", "consequence": "y"}])
        with patch(
            "app.rules.rule_engine.check_character_performance_readable",
            return_value=(False, "unreadable"),
        ):
            evaluation = engine._evaluate_performance_001(ir, {})
        assert evaluation.configured_severity in (Severity.PASS, Severity.WARNING)

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        ir = _minimal_ir(beats=[{"action": "x", "consequence": "y"}])
        with patch(
            "app.rules.rule_engine.check_character_performance_readable",
            side_effect=SemanticCheckServiceError("boom"),
        ):
            evaluation = engine._evaluate_performance_001(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR


class TestProducibility003FragileInteractionRisk:
    def test_pass_with_no_risk_tags(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            setting={"mainProps": ["wooden block"]},
            beats=[{"action": "pushes block", "consequence": "block slides"}],
        )
        evaluation = engine._evaluate_producibility_003(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.details["riskTags"] == []

    def test_critical_fail_when_zipper_detected(self) -> None:
        engine = _engine()
        ir = _minimal_ir(setting={"mainProps": ["jacket with zipper"]}, beats=[])
        evaluation = engine._evaluate_producibility_003(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL
        assert "ZIPPER" in evaluation.details["riskTags"]

    def test_critical_fail_when_rope_detected_in_beat_text(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            setting={"mainProps": ["box"]},
            beats=[{"action": "pulls the rope", "consequence": "box tips over"}],
        )
        evaluation = engine._evaluate_producibility_003(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert "ROPE_STRING" in evaluation.details["riskTags"]

    def test_detects_multiple_tags_at_once(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            setting={"mainProps": ["shoelace", "watch clasp"]},
            beats=[{"action": "reaches toward face", "consequence": "nothing happens"}],
        )
        evaluation = engine._evaluate_producibility_003(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert "ROPE_STRING" in evaluation.details["riskTags"]
        assert "WATCH_CLASP" in evaluation.details["riskTags"]
        assert "FACE_CONTACT" in evaluation.details["riskTags"]

    def test_never_exceeds_critical(self) -> None:
        engine = _engine()
        ir = _minimal_ir(setting={"mainProps": ["zipper", "rope", "liquid", "cloth"]}, beats=[])
        evaluation = engine._evaluate_producibility_003(ir, {})
        assert evaluation.configured_severity in (Severity.PASS, Severity.CRITICAL)
