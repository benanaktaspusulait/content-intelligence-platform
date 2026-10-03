"""Integration test: RULESET_1.2.yaml must exist, be loadable, contain all 26
rules (20 from 1.1 + 6 new), every rule id must have a registered evaluator,
and a pre-1.2-shaped IR (missing relatesToCoreProblem, mechanicCount,
loopsToOpening/loopQuality, and isPeakIntensity entirely) must evaluate
without raising and without a false FAIL purely from their absence."""

from typing import Any
from unittest.mock import patch

from app.config import settings
from app.quality.contracts import RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager

EXPECTED_NEW_RULE_IDS = {
    "CONCEPT_007",
    "BEAT_005",
    "PAYOFF_004",
    "PAYOFF_005",
    "REPETITION_004",
    "PAYOFF_006",
}

EXPECTED_1_1_RULE_IDS = {
    "CONCEPT_006",
    "BEAT_004",
    "REPETITION_002",
    "REPETITION_003",
    "NOVELTY_001",
    "PROGRESSION_005",
    "ESCALATION_004",
    "PAYOFF_001",
    "PRODUCIBILITY_001",
    "CONSISTENCY_001",
    "HOOK_002",
    "HOOK_003",
    "MOTION_001",
    "ATTEMPT_001",
    "CHAR_002",
    "PRODUCIBILITY_002",
    "PAYOFF_002",
    "ATTEMPT_002",
    "PAYOFF_003",
    "CONSISTENCY_002",
}


def test_ruleset_1_2_file_exists() -> None:
    assert (settings.rules_dir / "RULESET_1.2.yaml").exists()


def test_ruleset_1_2_contains_all_26_rules() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.2.yaml"))
    rule_ids = {rule["id"] for rule in engine.ruleset["rules"]}
    assert rule_ids == EXPECTED_1_1_RULE_IDS | EXPECTED_NEW_RULE_IDS


def test_ruleset_1_2_summary_total_rules_matches_actual_count() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.2.yaml"))
    actual_count = len(engine.ruleset["rules"])
    assert actual_count == 26
    assert engine.ruleset["ruleset_summary"]["total_rules"] == 26


def test_ruleset_1_0_and_1_1_remain_unmodified_and_independently_loadable() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    e10 = manager.load_version("1.0")
    e11 = manager.load_version("1.1")
    e12 = manager.load_version("1.2")
    assert len(e10.ruleset["rules"]) == 10
    assert len(e11.ruleset["rules"]) == 20
    assert len(e12.ruleset["rules"]) == 26


def test_ruleset_1_2_has_no_unexpected_service_error_on_minimal_valid_ir() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.2.yaml"))
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "characters": {"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]},
        "setting": {"mainProps": ["cup", "rug"]},
        "hook": {"startsMidAction": True, "visualStrength": 5, "soundOffClear": True},
        "coreMechanic": {"physicalRule": "test rule", "consistency": "consistent", "mechanicCount": 1},
        "beats": [
            {
                "startTime": 0.0,
                "endTime": 3.0,
                "duration": 3.0,
                "action": "catches cup",
                "primaryVerb": "CATCH",
                "isAttempt": True,
                "relatesToCoreProblem": True,
                "isNewConsequence": True,
                "consequenceType": "new",
                "motionAmount": "high",
                "consequence": "stops",
                "intensity": 6,
            },
            {
                "startTime": 3.0,
                "endTime": 15.0,
                "duration": 12.0,
                "action": "blocks with book",
                "primaryVerb": "BLOCK",
                "isAttempt": True,
                "relatesToCoreProblem": True,
                "isNewConsequence": True,
                "consequenceType": "new",
                "motionAmount": "moderate",
                "consequence": "redirects",
                "intensity": 8,
            },
        ],
        "finalPayoff": {
            "startsAt": 12.0,
            "isRepeatOfOpening": False,
            "isPeakIntensity": True,
            "loopsToOpening": False,
            "loopQuality": "none",
        },
        "producibility": {"overallComplexity": "low"},
    }
    with (
        patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]),
        patch("app.rules.rule_engine.check_twist_matches_rule", return_value=(True, "ok")),
        patch("app.rules.rule_engine.count_independent_mechanics", return_value=(1, "ok")),
    ):
        report = engine.evaluate(ir)
    service_error_rule_ids = {e.rule_id for e in report.service_errors}
    assert service_error_rule_ids == set(), f"Unexpected SERVICE_ERROR rules: {service_error_rule_ids}"


def test_backward_compat_pre_1_2_ir_missing_new_fields_does_not_false_fail() -> None:
    """A pre-1.2-shaped IR (no relatesToCoreProblem, no mechanicCount, no
    loopsToOpening/loopQuality, and no isPeakIntensity anywhere) run through
    the 1.2 ruleset must not produce a false FAIL on BEAT_005, CONCEPT_007,
    PAYOFF_006, or PAYOFF_004 purely from the missing fields. Reuses the
    structure of the existing FAIL_001 Kiko fixture's shape
    (duration/beats/finalPayoff), with none of the 4 new/pre-1.2-era-optional
    fields present anywhere. PAYOFF_004 is included because, although
    isPeakIntensity existed before this plan, its evaluator (added in this
    plan) never trusts it for the verdict -- the verdict is always derived
    from beat.intensity, so this must also hold with the claim absent."""
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.2.yaml"))
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0},
        "characters": {"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]},
        "setting": {"mainProps": ["floor", "mat"]},
        "hook": {"startsMidAction": True, "visualStrength": 5, "soundOffClear": True},
        "coreMechanic": {
            "physicalRule": "Smooth floor = slide, rough mat = stop",
            "consistency": "consistent",
            # no mechanicCount key at all
        },
        "beats": [
            {
                "id": "beat_01",
                "startTime": 0.0,
                "endTime": 1.0,
                "duration": 1.0,
                "action": "slides on glossy floor",
                "consequence": "shoe glides forward",
                "consequenceType": "new",
                "intensity": 8,
                "motionAmount": "high",
                "isNewConsequence": True,
                "isAttempt": True,
                "primaryVerb": "SLIDE",
                # no relatesToCoreProblem key at all
            },
            {
                "id": "beat_02",
                "startTime": 1.0,
                "endTime": 15.0,
                "duration": 14.0,
                "action": "reaches rough mat, stops sliding",
                "consequence": "sliding stops",
                "consequenceType": "new",
                "intensity": 7,
                "motionAmount": "moderate",
                "isNewConsequence": True,
                "isAttempt": True,
                "primaryVerb": "STOP",
            },
        ],
        "finalPayoff": {
            "startsAt": 13.0,
            "endsAt": 15.0,
            "isHardCut": True,
            "isRepeatOfOpening": False,
            # no isPeakIntensity, loopsToOpening, or loopQuality keys at all
        },
        "producibility": {"overallComplexity": "low"},
    }
    with (
        patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]),
        patch("app.rules.rule_engine.check_twist_matches_rule", return_value=(True, "ok")),
        patch("app.rules.rule_engine.count_independent_mechanics", return_value=(1, "ok")),
    ):
        report = engine.evaluate(ir)

    beat_005 = next(e for e in report.evaluations if e.rule_id == "BEAT_005")
    concept_007 = next(e for e in report.evaluations if e.rule_id == "CONCEPT_007")
    payoff_006 = next(e for e in report.evaluations if e.rule_id == "PAYOFF_006")
    payoff_004 = next(e for e in report.evaluations if e.rule_id == "PAYOFF_004")

    # None of these should FAIL purely because the new optional fields are absent.
    assert beat_005.outcome is RuleOutcome.PASS
    assert concept_007.outcome is RuleOutcome.PASS
    assert payoff_006.outcome in (RuleOutcome.PASS,)  # hard cut, no loop claim -> neutral PASS
    # beat_02 (startTime 1.0-15.0, intensity 7) straddles payoff_starts_at (13.0) and
    # is the only beat with endTime > 13.0, so it alone defines final_intensity (7);
    # prior_beats is just beat_01 (intensity 8). 7 < 8 -> correctly FAILs on the
    # merits of the actual intensities, with no isPeakIntensity claim involved at all.
    assert payoff_004.outcome is RuleOutcome.FAIL
    assert payoff_004.configured_severity is Severity.WARNING


def test_compare_versions_1_1_to_1_2_reports_only_additions() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    comparison = manager.compare_versions("1.1", "1.2")
    assert set(comparison.new_rules) == EXPECTED_NEW_RULE_IDS
    assert comparison.removed_rules == []
    assert comparison.is_backward_compatible is True
