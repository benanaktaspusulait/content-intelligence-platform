"""Integration test: RULESET_1.1.yaml must exist, be loadable, contain all 20
rules (10 original + 10 new), and every rule id must have a registered
evaluator (no SERVICE_ERROR from a missing registration)."""

from app.config import settings
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager

EXPECTED_NEW_RULE_IDS = {
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

EXPECTED_ORIGINAL_RULE_IDS = {
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
}


def test_ruleset_1_1_file_exists() -> None:
    assert (settings.rules_dir / "RULESET_1.1.yaml").exists()


def test_ruleset_1_1_contains_all_20_rules() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.1.yaml"))
    rule_ids = {rule["id"] for rule in engine.ruleset["rules"]}
    assert rule_ids == EXPECTED_ORIGINAL_RULE_IDS | EXPECTED_NEW_RULE_IDS


def test_ruleset_1_1_has_no_service_errors_on_minimal_valid_ir() -> None:
    """Every rule id in the YAML must have a registered evaluator — a
    well-formed IR run through 1.1 must produce zero SERVICE_ERROR results
    purely from missing registrations (individual rules may still FAIL on
    content, that's expected and fine; SERVICE_ERROR specifically means
    "no evaluator registered for this id" and must not happen).

    ATTEMPT_002 and PAYOFF_003 call out to an LLM provider for semantic
    duplicate-strategy / twist-consistency judgment (see
    app.llm.semantic_checks). This test has no live OpenAI credentials
    (consistent with the rest of the suite — see test_semantic_checks.py and
    test_rule_engine_new_rules.py, which always mock this boundary rather
    than making a real network call), so the two LLM entry points are
    patched to deterministic "no duplicates / twist matches" responses.
    This isolates the test to its actual purpose: confirming no rule id is
    missing from the evaluator registry, not exercising LLM judgment
    quality."""
    from unittest.mock import patch

    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.1.yaml"))
    ir = {
        "metadata": {"duration": 15.0},
        "characters": {"primary": "Kiko", "characterRefs": ["01-CHARACTERS/kiko.png"]},
        "setting": {"mainProps": ["cup", "rug"]},
        "hook": {"startsMidAction": True, "visualStrength": 5, "soundOffClear": True},
        "coreMechanic": {"physicalRule": "test rule", "consistency": "consistent"},
        "beats": [
            {
                "startTime": 0.0,
                "endTime": 3.0,
                "duration": 3.0,
                "action": "catches cup",
                "primaryVerb": "CATCH",
                "isAttempt": True,
                "isNewConsequence": True,
                "consequenceType": "new",
                "motionAmount": "high",
                "consequence": "stops",
            },
            {
                "startTime": 3.0,
                "endTime": 15.0,
                "duration": 12.0,
                "action": "blocks with book",
                "primaryVerb": "BLOCK",
                "isAttempt": True,
                "isNewConsequence": True,
                "consequenceType": "new",
                "motionAmount": "moderate",
                "consequence": "redirects",
            },
        ],
        "finalPayoff": {"startsAt": 12.0, "isRepeatOfOpening": False},
        "producibility": {"overallComplexity": "low"},
    }
    with (
        patch("app.rules.rule_engine.find_duplicate_strategy_pairs", return_value=[]),
        patch("app.rules.rule_engine.check_twist_matches_rule", return_value=(True, "mocked: consistent")),
    ):
        report = engine.evaluate(ir)
    service_error_rule_ids = {e.rule_id for e in report.service_errors}
    # CONSISTENCY_002 legitimately reports UNKNOWN (not SERVICE_ERROR) here
    # since no _renderedVideoPath is present — that's correct, not a bug.
    assert service_error_rule_ids == set(), f"Unexpected SERVICE_ERROR rules: {service_error_rule_ids}"


def test_compare_versions_1_0_to_1_1_reports_only_additions() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    comparison = manager.compare_versions("1.0", "1.1")
    assert set(comparison.new_rules) == EXPECTED_NEW_RULE_IDS
    assert comparison.removed_rules == []
    assert comparison.is_backward_compatible is True
