"""Cross-rule integration test: all 26 rules (20 pre-existing + 6 new from
RULESET 1.2) evaluate together against one realistic IR with zero
unexpected SERVICE_ERROR. Uses a YAML built in-memory listing all 26 rule
IDs, since this test runs before Task 11 generates the real
RULESET_1.2.yaml file on disk.
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import yaml

from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine

ALL_26_RULE_IDS = [
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
]


def _build_test_ruleset_yaml(tmp_path: Path) -> Path:
    ruleset_data = {
        "version": "1.2-test",
        "description": "In-memory test ruleset listing all 26 rule IDs",
        "rules": [
            {"id": rule_id, "name": rule_id, "family": "test", "severity": "WARNING"}
            for rule_id in ALL_26_RULE_IDS
        ],
    }
    path = tmp_path / "RULESET_1.2-test.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(ruleset_data, f)
    return path


def _realistic_ir() -> dict[str, Any]:
    return {
        "metadata": {"duration": 15.0},
        "characters": {"primary": "Mimi", "characterRefs": ["01-CHARACTERS/mimi.png"]},
        "setting": {"mainProps": ["cup", "rug"]},
        "hook": {"startsMidAction": True, "visualStrength": 5, "soundOffClear": True},
        "coreMechanic": {
            "physicalRule": "Objects on the rug slide toward the edge.",
            "consistency": "consistent",
            "mechanicCount": 1,
        },
        "beats": [
            {
                "startTime": 0.0,
                "endTime": 3.0,
                "duration": 3.0,
                "action": "catches sliding cup",
                "primaryVerb": "CATCH",
                "isAttempt": True,
                "relatesToCoreProblem": True,
                "isNewConsequence": True,
                "consequenceType": "new",
                "motionAmount": "high",
                "consequence": "cup stops",
                "intensity": 6,
            },
            {
                "startTime": 3.0,
                "endTime": 7.0,
                "duration": 4.0,
                "action": "blocks with a book",
                "primaryVerb": "BLOCK",
                "isAttempt": True,
                "relatesToCoreProblem": True,
                "isNewConsequence": True,
                "consequenceType": "new",
                "motionAmount": "moderate",
                "consequence": "cup redirects",
                "intensity": 7,
            },
            {
                "startTime": 7.0,
                "endTime": 10.0,
                "duration": 3.0,
                "action": "contains with a tray",
                "primaryVerb": "CONTAIN",
                "isAttempt": True,
                "relatesToCoreProblem": True,
                "isNewConsequence": True,
                "consequenceType": "fake_win",
                "motionAmount": "moderate",
                "consequence": "cup settles briefly",
                "intensity": 4,
            },
            {
                "startTime": 10.0,
                "endTime": 15.0,
                "duration": 5.0,
                "action": "whole rug slides away",
                "primaryVerb": "CHASE",
                "isAttempt": True,
                "relatesToCoreProblem": True,
                "isNewConsequence": True,
                "consequenceType": "escalation",
                "motionAmount": "high",
                "consequence": "rug slides out of the room",
                "intensity": 9,
            },
        ],
        "finalPayoff": {
            "startsAt": 10.0,
            "endsAt": 15.0,
            "isPeakIntensity": True,
            "isHardCut": True,
            "isRepeatOfOpening": False,
            "loopsToOpening": False,
            "loopQuality": "none",
        },
        "producibility": {"overallComplexity": "low"},
    }


def test_all_26_rules_evaluate_with_no_unexpected_service_error(tmp_path: Path) -> None:
    ruleset_path = _build_test_ruleset_yaml(tmp_path)
    engine = RuleEngine(str(ruleset_path))
    ir = _realistic_ir()

    with (
        patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]),
        patch(
            "app.rules.rule_engine.check_twist_matches_rule",
            return_value=(True, "Consistent with the rug rule."),
        ),
        patch(
            "app.rules.rule_engine.count_independent_mechanics",
            return_value=(1, "Single rug-sliding mechanic throughout."),
        ),
    ):
        report = engine.evaluate(ir)

    service_error_rule_ids = {e.rule_id for e in report.service_errors}
    # CONSISTENCY_002 legitimately reports UNKNOWN here (no _renderedVideoPath) — that's
    # correct, not a SERVICE_ERROR. Every other rule must have a registered evaluator.
    assert service_error_rule_ids == set(), f"Unexpected SERVICE_ERROR rules: {service_error_rule_ids}"

    evaluated_rule_ids = {e.rule_id for e in report.evaluations}
    assert evaluated_rule_ids == set(ALL_26_RULE_IDS)


def test_consistency_002_reports_unknown_not_service_error(tmp_path: Path) -> None:
    ruleset_path = _build_test_ruleset_yaml(tmp_path)
    engine = RuleEngine(str(ruleset_path))
    ir = _realistic_ir()  # no _renderedVideoPath key

    with (
        patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]),
        patch("app.rules.rule_engine.check_twist_matches_rule", return_value=(True, "ok")),
        patch("app.rules.rule_engine.count_independent_mechanics", return_value=(1, "ok")),
    ):
        report = engine.evaluate(ir)

    consistency_002_eval = next(e for e in report.evaluations if e.rule_id == "CONSISTENCY_002")
    assert consistency_002_eval.outcome is RuleOutcome.UNKNOWN
