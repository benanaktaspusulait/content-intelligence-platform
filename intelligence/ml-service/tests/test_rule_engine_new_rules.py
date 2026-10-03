"""Tests for the RULESET_1.1 new rule evaluators.

Each test builds a minimal video_plan_ir dict containing only the fields the
evaluator under test reads, calls the engine's internal `_evaluate_*` method
directly (matching the direct-method-call style used to unit test the
existing 10 evaluators), and asserts on the returned RuleEvaluation.
"""

from typing import Any
from unittest.mock import patch

import pytest

from app.config import settings
from app.quality.contracts import RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine

RULESET_1_0 = str(settings.rules_dir / "RULESET_1.0.yaml")


def _engine() -> RuleEngine:
    return RuleEngine(RULESET_1_0)


def _minimal_ir(**overrides: Any) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "hook": {
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


class TestDurationTier:
    def test_short_tier_at_boundary(self) -> None:
        assert _engine()._get_duration_tier(20.0) == "short"

    def test_long_tier_just_above_boundary(self) -> None:
        assert _engine()._get_duration_tier(20.1) == "long"

    def test_short_tier_for_15s(self) -> None:
        assert _engine()._get_duration_tier(15.0) == "short"

    def test_long_tier_for_40s(self) -> None:
        assert _engine()._get_duration_tier(40.0) == "long"


class TestHook002FirstFrameAnomaly:
    def test_pass_when_mid_action_and_strong(self) -> None:
        engine = _engine()
        ir = _minimal_ir(hook={"startsMidAction": True, "visualStrength": 5, "soundOffClear": True})
        evaluation = engine._evaluate_hook_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_when_not_mid_action(self) -> None:
        engine = _engine()
        ir = _minimal_ir(hook={"startsMidAction": False, "visualStrength": 5, "soundOffClear": True})
        evaluation = engine._evaluate_hook_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL

    def test_fail_when_visual_strength_too_low(self) -> None:
        engine = _engine()
        ir = _minimal_ir(hook={"startsMidAction": True, "visualStrength": 2, "soundOffClear": True})
        evaluation = engine._evaluate_hook_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL


class TestHook003SoundIndependence:
    def test_pass_when_sound_off_clear(self) -> None:
        engine = _engine()
        ir = _minimal_ir(hook={"startsMidAction": True, "visualStrength": 5, "soundOffClear": True})
        evaluation = engine._evaluate_hook_003(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_when_sound_off_not_clear(self) -> None:
        engine = _engine()
        ir = _minimal_ir(hook={"startsMidAction": True, "visualStrength": 5, "soundOffClear": False})
        evaluation = engine._evaluate_hook_003(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL


class TestMotion001NoDeadAir:
    def test_pass_when_no_long_static_beat(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            beats=[
                {"motionAmount": "high", "duration": 2.0},
                {"motionAmount": "none", "duration": 1.0},
                {"motionAmount": "moderate", "duration": 3.0},
            ]
        )
        evaluation = engine._evaluate_motion_001(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_when_dead_air_exceeds_1_5s(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            beats=[
                {"motionAmount": "none", "duration": 2.5},
                {"motionAmount": "high", "duration": 1.0},
            ]
        )
        evaluation = engine._evaluate_motion_001(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.actual_value == 2.5

    def test_pass_with_no_beats(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[])
        evaluation = engine._evaluate_motion_001(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS


class TestAttempt001AttemptCount:
    def test_pass_short_tier_with_3_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 15.0},
            beats=[
                {"isAttempt": True, "primaryVerb": "CATCH"},
                {"isAttempt": True, "primaryVerb": "BLOCK"},
                {"isAttempt": True, "primaryVerb": "TILT"},
                {"isAttempt": False, "primaryVerb": ""},
            ],
        )
        evaluation = engine._evaluate_attempt_001(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_short_tier_with_2_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 15.0},
            beats=[
                {"isAttempt": True, "primaryVerb": "CATCH"},
                {"isAttempt": True, "primaryVerb": "BLOCK"},
            ],
        )
        evaluation = engine._evaluate_attempt_001(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.required_value == 3

    def test_fail_long_tier_with_6_attempts(self) -> None:
        engine = _engine()
        beats = [{"isAttempt": True, "primaryVerb": f"VERB{i}"} for i in range(6)]
        ir = _minimal_ir(metadata={"duration": 40.0}, beats=beats)
        evaluation = engine._evaluate_attempt_001(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.required_value == 7

    def test_pass_long_tier_with_7_attempts(self) -> None:
        engine = _engine()
        beats = [{"isAttempt": True, "primaryVerb": f"VERB{i}"} for i in range(7)]
        ir = _minimal_ir(metadata={"duration": 40.0}, beats=beats)
        evaluation = engine._evaluate_attempt_001(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_beats_without_isattempt_key_count_as_not_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=[{"action": "stands"}, {"action": "waits"}])
        evaluation = engine._evaluate_attempt_001(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.actual_value == 0


class TestChar002ActiveCharacter:
    def test_pass_short_tier_above_50_percent_active(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 10.0},
            beats=[
                {"isAttempt": True, "duration": 6.0},
                {"isAttempt": False, "duration": 4.0},
            ],
        )
        evaluation = engine._evaluate_char_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_short_tier_below_50_percent_active(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 10.0},
            beats=[
                {"isAttempt": True, "duration": 3.0},
                {"isAttempt": False, "duration": 7.0},
            ],
        )
        evaluation = engine._evaluate_char_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL

    def test_fail_long_tier_below_60_percent_active(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 30.0},
            beats=[
                {"isAttempt": True, "duration": 15.0},
                {"isAttempt": False, "duration": 15.0},
            ],
        )
        evaluation = engine._evaluate_char_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL

    def test_pass_with_no_beats_treated_as_zero_active(self) -> None:
        engine = _engine()
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=[])
        evaluation = engine._evaluate_char_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.actual_value == 0.0


class TestProducibility002PropEconomy:
    def test_pass_short_tier_at_2_props(self) -> None:
        engine = _engine()
        ir = _minimal_ir(setting={"mainProps": ["cup", "rug"]}, beats=[])
        evaluation = engine._evaluate_producibility_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_short_tier_at_3_props(self) -> None:
        engine = _engine()
        ir = _minimal_ir(setting={"mainProps": ["cup", "rug", "book"]}, beats=[])
        evaluation = engine._evaluate_producibility_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.required_value == 2

    def test_pass_long_tier_at_4_props(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 35.0}, setting={"mainProps": ["cup", "rug", "book", "tray"]}, beats=[]
        )
        evaluation = engine._evaluate_producibility_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_long_tier_at_5_props(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 35.0},
            setting={"mainProps": ["cup", "rug", "book", "tray", "lamp"]},
            beats=[],
        )
        evaluation = engine._evaluate_producibility_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.required_value == 4


class TestPayoff002FakeResolution:
    def test_pass_when_fake_win_beat_present(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.5},
            beats=[
                {"startTime": 0.0, "consequenceType": "new"},
                {"startTime": 10.5, "consequenceType": "fake_win"},
            ],
        )
        evaluation = engine._evaluate_payoff_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.configured_severity is Severity.PASS

    def test_pass_as_bonus_when_no_fake_win_beat(self) -> None:
        """Fake resolution is a bonus, not a blocking requirement — its
        absence still PASSes, just without the bonus framing."""
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.5},
            beats=[{"startTime": 0.0, "consequenceType": "new"}],
        )
        evaluation = engine._evaluate_payoff_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.configured_severity is Severity.WARNING


class TestAttempt002DistinctAttempts:
    def test_fail_on_literal_verb_repetition_without_calling_llm(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 15.0},
            beats=[
                {"isAttempt": True, "primaryVerb": "PULL", "action": "pulls", "consequence": "moves"},
                {
                    "isAttempt": True,
                    "primaryVerb": "PULL",
                    "action": "pulls harder",
                    "consequence": "moves more",
                },
                {
                    "isAttempt": True,
                    "primaryVerb": "PULL",
                    "action": "pulls again",
                    "consequence": "moves again",
                },
            ],
        )
        with patch("app.rules.rule_engine.find_duplicate_strategy_pairs") as mock_find:
            evaluation = engine._evaluate_attempt_002(ir, {})
        mock_find.assert_not_called()
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.actual_value == 1  # all 3 collapse to 1 distinct verb

    def test_pass_when_verbs_distinct_and_llm_confirms_no_duplicates(self) -> None:
        engine = _engine()
        beats = [
            {"isAttempt": True, "primaryVerb": v, "action": f"{v.lower()}s", "consequence": "result"}
            for v in ["CATCH", "BLOCK", "TILT"]
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]) as mock_find:
            evaluation = engine._evaluate_attempt_002(ir, {})
        mock_find.assert_called_once()
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.actual_value == 3

    def test_fail_when_llm_flags_a_semantic_duplicate_pair(self) -> None:
        engine = _engine()
        beats = [
            {"isAttempt": True, "primaryVerb": v, "action": f"{v.lower()}s", "consequence": "result"}
            for v in ["GRAB", "BLOCK"]
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[(0, 1)]):
            evaluation = engine._evaluate_attempt_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.actual_value == 1  # 2 verb-distinct attempts minus 1 collapsed pair

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        beats = [
            {"isAttempt": True, "primaryVerb": v, "action": f"{v.lower()}s", "consequence": "result"}
            for v in ["CATCH", "BLOCK", "TILT"]
        ]
        ir = _minimal_ir(metadata={"duration": 15.0}, beats=beats)
        with patch(
            "app.rules.rule_engine.find_duplicate_strategy_pairs",
            side_effect=SemanticCheckServiceError("boom"),
        ):
            evaluation = engine._evaluate_attempt_002(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR

    def test_pass_with_fewer_than_2_attempts_without_calling_llm(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            metadata={"duration": 15.0},
            beats=[{"isAttempt": True, "primaryVerb": "CATCH", "action": "catches", "consequence": "stops"}],
        )
        with patch("app.rules.rule_engine.find_duplicate_strategy_pairs") as mock_find:
            evaluation = engine._evaluate_attempt_002(ir, {})
        mock_find.assert_not_called()
        assert evaluation.actual_value == 1


class TestPayoff003RuleConsistentTwist:
    def test_pass_when_llm_confirms_match(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            coreMechanic={
                "physicalRule": "Objects on the rug slide to the edge.",
                "consistency": "consistent",
            },
            finalPayoff={"type": "twist", "startsAt": 12.0},
            beats=[{"startTime": 12.0, "consequence": "The whole rug slides away with Mimi on it."}],
        )
        with patch(
            "app.rules.rule_engine.check_twist_matches_rule",
            return_value=(True, "Same rule, bigger scale."),
        ):
            evaluation = engine._evaluate_payoff_003(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_when_llm_reports_mismatch(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            coreMechanic={
                "physicalRule": "Objects on the rug slide to the edge.",
                "consistency": "consistent",
            },
            finalPayoff={"type": "twist", "startsAt": 12.0},
            beats=[{"startTime": 12.0, "consequence": "An elephant appears."}],
        )
        with patch(
            "app.rules.rule_engine.check_twist_matches_rule",
            return_value=(False, "Unrelated to the established rule."),
        ):
            evaluation = engine._evaluate_payoff_003(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL

    def test_service_error_on_llm_failure(self) -> None:
        from app.llm.semantic_checks import SemanticCheckServiceError

        engine = _engine()
        ir = _minimal_ir(
            coreMechanic={"physicalRule": "rule", "consistency": "consistent"},
            finalPayoff={"type": "twist", "startsAt": 12.0},
            beats=[{"startTime": 12.0, "consequence": "twist"}],
        )
        with patch(
            "app.rules.rule_engine.check_twist_matches_rule", side_effect=SemanticCheckServiceError("boom")
        ):
            evaluation = engine._evaluate_payoff_003(ir, {})
        assert evaluation.outcome is RuleOutcome.SERVICE_ERROR


class TestConsistency002CharacterContinuityLock:
    def test_unknown_when_no_rendered_video_path_present(self) -> None:
        """Pure concept-stage validation (no video yet) must report UNKNOWN,
        not FAIL and not a silent skip."""
        engine = _engine()
        ir = _minimal_ir(characters={"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]})
        evaluation = engine._evaluate_consistency_002(ir, {})
        assert evaluation.outcome is RuleOutcome.UNKNOWN

    def test_pass_when_rendered_video_path_present_and_continuity_verified(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            characters={"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]},
            _renderedVideoPath="/tmp/fake_video.mp4",
        )
        mock_result: dict[str, object] = {
            "character_continuity_verified": True,
            "confidence": 0.9,
            "frame_issues": {"first": None, "middle": None, "last": None},
            "reasoning": "all good",
        }
        with patch("app.rules.rule_engine.CharacterVerifier") as mock_verifier_cls:
            mock_verifier_cls.return_value.verify_continuity.return_value = mock_result
            evaluation = engine._evaluate_consistency_002(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_when_continuity_check_reports_drift(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            characters={"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]},
            _renderedVideoPath="/tmp/fake_video.mp4",
        )
        mock_result: dict[str, object] = {
            "character_continuity_verified": False,
            "confidence": 0.3,
            "frame_issues": {"first": None, "middle": "wrong outfit color", "last": None},
            "reasoning": "drift detected",
        }
        with patch("app.rules.rule_engine.CharacterVerifier") as mock_verifier_cls:
            mock_verifier_cls.return_value.verify_continuity.return_value = mock_result
            evaluation = engine._evaluate_consistency_002(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL


class TestFamilyScoreExcludesNotApplicableAndUnknown:
    def test_not_applicable_outcome_excluded_from_family_score(self) -> None:
        from app.quality.contracts import RuleEvaluation as CanonicalRuleEvaluation
        from app.quality.contracts import RuleOutcome, Severity

        engine = _engine()
        evaluations = [
            CanonicalRuleEvaluation(
                rule_id="A",
                rule_name="A",
                family="test_family",
                outcome=RuleOutcome.PASS,
                configured_severity=Severity.PASS,
                message="",
            ),
            CanonicalRuleEvaluation(
                rule_id="B",
                rule_name="B",
                family="test_family",
                outcome=RuleOutcome.NOT_APPLICABLE,
                configured_severity=Severity.WARNING,
                message="",
            ),
        ]
        scores = engine._calculate_family_scores(evaluations)
        # Only the PASS evaluation should count: 100 / 1 = 100, not 100 / 2 = 50.
        assert scores["test_family"] == 100.0

    def test_unknown_outcome_excluded_from_family_score(self) -> None:
        from app.quality.contracts import RuleEvaluation as CanonicalRuleEvaluation
        from app.quality.contracts import RuleOutcome, Severity

        engine = _engine()
        evaluations = [
            CanonicalRuleEvaluation(
                rule_id="A",
                rule_name="A",
                family="test_family",
                outcome=RuleOutcome.PASS,
                configured_severity=Severity.PASS,
                message="",
            ),
            CanonicalRuleEvaluation(
                rule_id="B",
                rule_name="B",
                family="test_family",
                outcome=RuleOutcome.UNKNOWN,
                configured_severity=Severity.WARNING,
                message="",
            ),
        ]
        scores = engine._calculate_family_scores(evaluations)
        assert scores["test_family"] == 100.0

    def test_family_with_only_not_applicable_scores_zero_with_zero_count(self) -> None:
        from app.quality.contracts import RuleEvaluation as CanonicalRuleEvaluation
        from app.quality.contracts import RuleOutcome, Severity

        engine = _engine()
        evaluations = [
            CanonicalRuleEvaluation(
                rule_id="A",
                rule_name="A",
                family="test_family",
                outcome=RuleOutcome.NOT_APPLICABLE,
                configured_severity=Severity.WARNING,
                message="",
            ),
        ]
        scores = engine._calculate_family_scores(evaluations)
        # count == 0 for this family -> the existing "count > 0 else 0" branch applies.
        assert scores["test_family"] == 0


class TestBeat005StoryDetachedGap:
    def test_pass_when_all_beats_relate_to_core_problem(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {
                    "startTime": 0.0,
                    "endTime": 5.0,
                    "duration": 5.0,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
                {
                    "startTime": 5.0,
                    "endTime": 12.0,
                    "duration": 7.0,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
            ],
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_pass_when_detached_stretch_under_threshold(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {
                    "startTime": 0.0,
                    "endTime": 5.0,
                    "duration": 5.0,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
                {
                    "startTime": 5.0,
                    "endTime": 5.3,
                    "duration": 0.3,
                    "isAttempt": False,
                    "relatesToCoreProblem": False,
                },
                {
                    "startTime": 5.3,
                    "endTime": 12.0,
                    "duration": 6.7,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
            ],
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_fail_when_detached_stretch_exceeds_threshold(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {
                    "startTime": 0.0,
                    "endTime": 5.0,
                    "duration": 5.0,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
                {
                    "startTime": 5.0,
                    "endTime": 6.0,
                    "duration": 1.0,
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
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL

    def test_pass_when_no_attempt_beats_yet_problem_not_established(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {
                    "startTime": 0.0,
                    "endTime": 12.0,
                    "duration": 12.0,
                    "isAttempt": False,
                    "relatesToCoreProblem": False,
                },
            ],
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_backward_compat_missing_field_treated_as_true(self) -> None:
        """A pre-1.2 beat with no relatesToCoreProblem key at all must never
        be treated as detached — the field defaults to True when absent."""
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {"startTime": 0.0, "endTime": 5.0, "duration": 5.0, "isAttempt": True},
                {"startTime": 5.0, "endTime": 12.0, "duration": 7.0, "isAttempt": True},
            ],
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_backward_compat_single_beat_missing_field_among_explicit_ones(self) -> None:
        """A single pre-1.2 beat with the field entirely absent, sitting between
        beats that do set it explicitly, must default to True (not detached) —
        isolating the default from any other beat's explicit value."""
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {
                    "startTime": 0.0,
                    "endTime": 5.0,
                    "duration": 5.0,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
                {"startTime": 5.0, "endTime": 5.3, "duration": 0.3, "isAttempt": False},
                {
                    "startTime": 5.3,
                    "endTime": 12.0,
                    "duration": 6.7,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
            ],
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_detached_beat_straddling_payoff_start_only_counts_pre_payoff_portion(self) -> None:
        """A detached beat that starts before the payoff but keeps playing past
        finalPayoff.startsAt must only have its pre-payoff portion counted toward
        the detached run — detachment occurring after the payoff has already
        begun is not "detachment while the core problem is still unresolved."""
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 12.0},
            beats=[
                {
                    "startTime": 0.0,
                    "endTime": 11.8,
                    "duration": 11.8,
                    "isAttempt": True,
                    "relatesToCoreProblem": True,
                },
                # Detached beat spans the payoff boundary: only 0.2s (11.8 -> 12.0)
                # is pre-payoff and within tolerance; the remaining 4.8s (12.0 -> 16.6)
                # occurs during/after the payoff. The *full* beat duration (4.8s) would
                # fail against the 0.5s cap, but the clipped pre-payoff portion (0.2s)
                # must not -- proving detachment after the payoff starts doesn't count.
                {
                    "startTime": 11.8,
                    "endTime": 16.6,
                    "duration": 4.8,
                    "isAttempt": False,
                    "relatesToCoreProblem": False,
                },
            ],
        )
        evaluation = engine._evaluate_beat_005(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.actual_value == pytest.approx(0.2)


class TestPayoff004FinalPeakIntensity:
    def test_pass_when_final_is_strictly_most_intense(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 10.0, "isPeakIntensity": True},
            beats=[
                {"startTime": 0.0, "endTime": 5.0, "intensity": 5},
                {"startTime": 5.0, "endTime": 10.0, "intensity": 6},
                {"startTime": 10.0, "endTime": 15.0, "intensity": 9},
            ],
        )
        evaluation = engine._evaluate_payoff_004(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.configured_severity is Severity.PASS

    def test_warning_pass_when_final_ties_the_peak(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 10.0, "isPeakIntensity": True},
            beats=[
                {"startTime": 0.0, "endTime": 10.0, "intensity": 9},
                {"startTime": 10.0, "endTime": 15.0, "intensity": 9},
            ],
        )
        evaluation = engine._evaluate_payoff_004(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
        assert evaluation.configured_severity is Severity.WARNING

    def test_fail_when_final_is_weaker_than_an_earlier_beat(self) -> None:
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 10.0, "isPeakIntensity": True},
            beats=[
                {"startTime": 0.0, "endTime": 10.0, "intensity": 9},
                {"startTime": 10.0, "endTime": 15.0, "intensity": 4},
            ],
        )
        evaluation = engine._evaluate_payoff_004(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING

    def test_ispeakintensity_claim_never_overrides_computed_result(self) -> None:
        """A producer writing isPeakIntensity=true must not force a PASS when
        the computed intensities say otherwise."""
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 10.0, "isPeakIntensity": True},  # claim: true
            beats=[
                {"startTime": 0.0, "endTime": 10.0, "intensity": 9},
                {"startTime": 10.0, "endTime": 15.0, "intensity": 2},  # computed: not peak
            ],
        )
        evaluation = engine._evaluate_payoff_004(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL  # computed result wins, not the claim

    def test_beat_straddling_payoff_start_counts_toward_final_not_dropped(self) -> None:
        """A beat that starts before finalPayoff.startsAt but is still playing
        when the payoff begins (endTime > startsAt) must count toward the final
        intensity, not be silently dropped from both partitions. Verifies the
        beat is not excluded entirely: without it, final_intensity would default
        to 0 and this would incorrectly PASS as "strictly the peak"."""
        engine = _engine()
        ir = _minimal_ir(
            finalPayoff={"startsAt": 10.0},
            beats=[
                {"startTime": 0.0, "endTime": 8.0, "intensity": 9},
                # Straddles the boundary: starts at 5 (before startsAt) but ends at 15
                # (after startsAt) -> must land in final_beats, not be dropped.
                {"startTime": 5.0, "endTime": 15.0, "intensity": 3},
            ],
        )
        evaluation = engine._evaluate_payoff_004(ir, {})
        # final_intensity should be 3 (from the straddling beat), prior max 9 -> FAIL,
        # not a false PASS from both beats being excluded and defaulting to 0 == 0.
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.actual_value == 3
        assert evaluation.required_value == 9


class TestRepetition004DominantActionRatio:
    def test_pass_below_warning_threshold(self) -> None:
        engine = _engine()
        beats = [{"isAttempt": True, "primaryVerb": v} for v in ["CATCH", "BLOCK", "TILT", "CONTAIN", "SIT"]]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_repetition_004(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_warning_fail_at_exactly_above_0_55(self) -> None:
        engine = _engine()
        # 6 of 10 attempts share one verb -> ratio 0.6, strictly above 0.55.
        beats = [{"isAttempt": True, "primaryVerb": "PUSH"} for _ in range(6)] + [
            {"isAttempt": True, "primaryVerb": v} for v in ["A", "B", "C", "D"]
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_repetition_004(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.WARNING

    def test_critical_fail_above_0_70(self) -> None:
        engine = _engine()
        # 8 of 10 attempts share one verb -> ratio 0.8, strictly above 0.70.
        beats = [{"isAttempt": True, "primaryVerb": "PUSH"} for _ in range(8)] + [
            {"isAttempt": True, "primaryVerb": v} for v in ["A", "B"]
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_repetition_004(ir, {})
        assert evaluation.outcome is RuleOutcome.FAIL
        assert evaluation.configured_severity is Severity.CRITICAL

    def test_pass_at_exactly_0_55_boundary(self) -> None:
        engine = _engine()
        # 11 of 20 attempts share one verb -> ratio 0.55 exactly, not > 0.55.
        beats = [{"isAttempt": True, "primaryVerb": "PUSH"} for _ in range(11)] + [
            {"isAttempt": True, "primaryVerb": f"V{i}"} for i in range(9)
        ]
        ir = _minimal_ir(beats=beats)
        evaluation = engine._evaluate_repetition_004(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS

    def test_pass_with_no_attempts(self) -> None:
        engine = _engine()
        ir = _minimal_ir(beats=[])
        evaluation = engine._evaluate_repetition_004(ir, {})
        assert evaluation.outcome is RuleOutcome.PASS
