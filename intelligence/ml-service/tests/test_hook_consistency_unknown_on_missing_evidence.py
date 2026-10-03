"""HOOK_002, HOOK_003, and CONSISTENCY_001 must report UNKNOWN, not crash and
not fabricate a PASS, when the parser could not find explicit evidence for
visualStrength/soundOffClear/consistency (Plan A, Phase 5/1)."""

from typing import Any

from app.config import settings
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine

RULESET_1_0 = str(settings.rules_dir / "RULESET_1.0.yaml")


def _engine() -> RuleEngine:
    return RuleEngine(RULESET_1_0)


def test_hook_002_returns_unknown_when_visual_strength_is_none() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "hook": {"startsMidAction": True, "visualStrength": None, "soundOffClear": True, "startsAt": 0.0},
        "beats": [],
    }
    evaluation = engine._evaluate_hook_002(ir, {})
    assert evaluation.outcome is RuleOutcome.UNKNOWN


def test_hook_002_still_fails_on_verified_non_mid_action_start() -> None:
    """A verified (not missing) False for startsMidAction is still a real FAIL,
    not UNKNOWN -- this task only changes handling of missing visualStrength."""
    engine = _engine()
    ir: dict[str, Any] = {
        "hook": {"startsMidAction": False, "visualStrength": None, "soundOffClear": True, "startsAt": 0.0},
        "beats": [],
    }
    evaluation = engine._evaluate_hook_002(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL


def test_hook_003_returns_unknown_when_sound_off_clear_is_none() -> None:
    engine = _engine()
    ir: dict[str, Any] = {"hook": {"soundOffClear": None}, "beats": []}
    evaluation = engine._evaluate_hook_003(ir, {})
    assert evaluation.outcome is RuleOutcome.UNKNOWN


def test_consistency_001_returns_unknown_when_consistency_is_none() -> None:
    engine = _engine()
    ir: dict[str, Any] = {"coreMechanic": {"consistency": None}, "beats": []}
    evaluation = engine._evaluate_consistency_001(ir, {})
    assert evaluation.outcome is RuleOutcome.UNKNOWN


def test_consistency_001_still_fails_on_verified_breaking_consistency() -> None:
    engine = _engine()
    ir: dict[str, Any] = {"coreMechanic": {"consistency": "breaking"}, "beats": []}
    evaluation = engine._evaluate_consistency_001(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL
