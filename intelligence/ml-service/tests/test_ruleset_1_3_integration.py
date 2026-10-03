"""Integration test: RULESET_1.3.yaml must exist, be loadable, contain all 33
rules (26 from 1.2 + 7 new), every rule id must have a registered evaluator,
and a minimal valid IR must evaluate with no unexpected SERVICE_ERROR when
all LLM-backed semantic checks are mocked."""

from typing import Any
from unittest.mock import patch

from app.config import settings
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager

EXPECTED_NEW_RULE_IDS = {
    "GOAL_001",
    "CONCEPT_008",
    "PROGRESSION_006",
    "ESCALATION_005",
    "HOOK_004",
    "PERFORMANCE_001",
    "PRODUCIBILITY_003",
}

EXPECTED_1_2_RULE_IDS = {
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
    "CONCEPT_007",
    "BEAT_005",
    "PAYOFF_004",
    "PAYOFF_005",
    "REPETITION_004",
    "PAYOFF_006",
}

# Every LLM-backed semantic check function this ruleset's evaluators call,
# across all versions — must all be mocked together for a full-ruleset
# evaluate() run to avoid any real network/credential-dependent call.
_ALL_SEMANTIC_CHECK_MOCKS = {
    "app.rules.rule_engine.find_duplicate_strategy_pairs": [],
    "app.rules.rule_engine.check_twist_matches_rule": (True, "ok"),
    "app.rules.rule_engine.count_independent_mechanics": (1, "ok"),
    "app.rules.rule_engine.check_goal_is_natural": (True, "ok"),
    "app.rules.rule_engine.check_rule_is_predictable": (True, "ok"),
    "app.rules.rule_engine.check_opening_problem_legible": (True, "ok"),
    "app.rules.rule_engine.check_character_performance_readable": (True, "ok"),
}


def test_ruleset_1_3_file_exists() -> None:
    assert (settings.rules_dir / "RULESET_1.3.yaml").exists()


def test_ruleset_1_3_contains_all_33_rules() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.3.yaml"))
    rule_ids = {rule["id"] for rule in engine.ruleset["rules"]}
    assert rule_ids == EXPECTED_1_2_RULE_IDS | EXPECTED_NEW_RULE_IDS


def test_ruleset_1_3_summary_total_rules_matches_actual_count() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.3.yaml"))
    actual_count = len(engine.ruleset["rules"])
    assert actual_count == 33
    assert engine.ruleset["ruleset_summary"]["total_rules"] == 33


def test_ruleset_1_0_through_1_3_remain_independently_loadable() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    e10 = manager.load_version("1.0")
    e11 = manager.load_version("1.1")
    e12 = manager.load_version("1.2")
    e13 = manager.load_version("1.3")
    assert len(e10.ruleset["rules"]) == 10
    assert len(e11.ruleset["rules"]) == 20
    assert len(e12.ruleset["rules"]) == 26
    assert len(e13.ruleset["rules"]) == 33


def _minimal_valid_ir() -> dict[str, Any]:
    return {
        "metadata": {"duration": 15.0},
        "characters": {"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]},
        "setting": {"mainProps": ["cup", "rug"]},
        "hook": {
            "anomaly": "cup slides away",
            "startsMidAction": True,
            "visualStrength": 5,
            "soundOffClear": True,
        },
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
            "isHardCut": True,
            "loopsToOpening": False,
            "loopQuality": "none",
        },
        "producibility": {"overallComplexity": "low"},
    }


def test_ruleset_1_3_has_no_unexpected_service_error_on_minimal_valid_ir() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.3.yaml"))
    ir = _minimal_valid_ir()

    patches = [patch(target, return_value=value) for target, value in _ALL_SEMANTIC_CHECK_MOCKS.items()]
    for p in patches:
        p.start()
    try:
        report = engine.evaluate(ir)
    finally:
        for p in patches:
            p.stop()

    service_error_rule_ids = {e.rule_id for e in report.service_errors}
    assert service_error_rule_ids == set(), f"Unexpected SERVICE_ERROR rules: {service_error_rule_ids}"

    evaluated_rule_ids = {e.rule_id for e in report.evaluations}
    assert evaluated_rule_ids == EXPECTED_1_2_RULE_IDS | EXPECTED_NEW_RULE_IDS


def test_compare_versions_1_2_to_1_3_reports_only_additions() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    comparison = manager.compare_versions("1.2", "1.3")
    assert set(comparison.new_rules) == EXPECTED_NEW_RULE_IDS
    assert comparison.removed_rules == []
    assert comparison.is_backward_compatible is True
