"""RED tests for RULESET 1.7 STUBBORN_RETURN_LOOP policy exceptions."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.quality.canonical_evidence import engine_profile_evidence
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager

RULESET = str(settings.rules_dir / "RULESET_1.7.yaml")


def engine() -> RuleEngine:
    return RuleEngine(RULESET)


def spoon_ir(*, explicit: bool = False, weak: bool = False, final_stalemate: bool = True) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "engineProfile": "STUBBORN_RETURN_LOOP" if explicit else None,
        "engineProfileSource": "EXPLICIT" if explicit else None,
        "engineProfileConfidence": "HIGH" if explicit else None,
        "boundary": {"type": "TABLE_EDGE", "safeState": "INWARD_FROM_EDGE", "dangerState": "AT_EDGE"},
        "autonomousReturn": True,
        "recurrenceCount": 3,
        "resistanceEscalation": not weak,
        "emotionalEscalation": not weak,
    }
    if not explicit:
        profile = {}
    beats = [
        {"id": "b1", "startTime": 0, "endTime": 2, "duration": 2, "majorBeat": True, "beatRole": "HOOK", "action": "Mimi reaches for the spoon at the table edge", "consequence": "the danger is already visible", "visualStateId": "edge"},
        {"id": "b2", "startTime": 2, "endTime": 5, "duration": 3, "majorBeat": True, "beatRole": "ATTEMPT", "action": "Mimi pulls the spoon inward", "consequence": "spoon is safe for a moment", "visualStateId": "safe", "isAttempt": True, "primaryVerb": "PULL", "strategyFamily": "PULL", "intensity": 4},
        {"id": "b3", "startTime": 5, "endTime": 8, "duration": 3, "majorBeat": True, "beatRole": "ESCALATION", "action": "spoon slides back to the table edge by itself", "consequence": "Mimi grabs it again", "visualStateId": "edge", "isAttempt": False, "intensity": 6},
        {"id": "b4", "startTime": 8, "endTime": 11, "duration": 3, "majorBeat": True, "beatRole": "ESCALATION", "action": "Mimi pulls faster and holds the spoon with both hands", "consequence": "spoon still resists and returns toward the edge", "visualStateId": "edge", "isAttempt": True, "primaryVerb": "PULL", "strategyFamily": "PULL", "intensity": 8},
        {"id": "b5", "startTime": 11, "endTime": 15, "duration": 4, "majorBeat": True, "beatRole": "TWIST", "action": "Mimi pins the spoon with both hands at the cut", "consequence": "the same return rule remains active but the struggle is strongest", "visualStateId": "edge", "intensity": 9},
    ]
    if weak:
        beats[3]["action"] = "Mimi looks at the spoon again"
        beats[3]["consequence"] = "nothing changes"
        beats[3]["intensity"] = 4
        beats[4]["action"] = "Mimi waits"
        beats[4]["consequence"] = "the scene resets"
        beats[4]["intensity"] = 4
    if final_stalemate:
        final_payoff = {"startsAt": 11, "endsAt": 15, "isPeakIntensity": True}
    else:
        final_payoff = {}
    return {
        "metadata": {"duration": 15.0, "generationMode": "SINGLE_15S"},
        "characters": {"primary": "Mimi"},
        "coreMechanic": {"physicalRule": "The spoon returns toward the table edge.", "primaryObject": "spoon", "engineProfile": profile},
        "engineProfile": profile,
        "goalEvidence": {"goalExplicitness": "IMPLICIT_BUT_OBSERVABLE", "goalType": "RETRIEVE_OR_CONTROL_OBJECT", "description": "Keep the spoon safely on the table", "targetObject": "spoon", "obstruction": "spoon returns toward the edge"},
        "beats": beats,
        "finalPayoff": final_payoff,
    }


def test_explicit_profile_is_active_and_has_all_required_evidence() -> None:
    evidence = engine_profile_evidence(spoon_ir(explicit=True))
    assert evidence.profile == "STUBBORN_RETURN_LOOP"
    assert evidence.source == "EXPLICIT"
    assert evidence.confidence == "HIGH"
    assert evidence.active is True


def test_high_inference_is_active_only_when_all_mandatory_signals_exist() -> None:
    evidence = engine_profile_evidence(spoon_ir())
    assert evidence.source == "INFERRED"
    assert evidence.confidence == "HIGH"
    assert evidence.active is True
    assert all(evidence.signals.values())


def test_medium_inference_is_candidate_only_and_does_not_activate_exception() -> None:
    evidence = engine_profile_evidence(spoon_ir(weak=True))
    assert evidence.confidence == "MEDIUM"
    assert evidence.active is False
    assert evidence.candidate_only is True


def test_attempt_diversity_exception_allows_repeated_pull_only_with_escalation() -> None:
    result = engine()._evaluate_attempt_002(spoon_ir(), {})
    assert result.outcome is RuleOutcome.PASS
    assert result.details["exception"] == "STUBBORN_RETURN_LOOP"


def test_attempt_diversity_exception_does_not_allow_flat_repetition() -> None:
    result = engine()._evaluate_attempt_002(spoon_ir(weak=True), {})
    assert result.outcome is RuleOutcome.FAIL


def test_stalemate_payoff_passes_only_when_same_rule_is_stronger_and_active() -> None:
    result = engine()._evaluate_stubborn_return_payoff(spoon_ir(), {})
    assert result.outcome is RuleOutcome.PASS
    weak = engine()._evaluate_stubborn_return_payoff(spoon_ir(weak=True), {})
    assert weak.outcome is not RuleOutcome.PASS


def test_hook_accepts_immediate_visible_threat_without_static_impossibility() -> None:
    ir = spoon_ir()
    ir["hook"] = {"startsAt": 0.0, "visibleProblem": True, "characterAlreadyEngaged": True}
    result = engine()._evaluate_stubborn_return_hook(ir, {})
    assert result.outcome is RuleOutcome.PASS


def test_state_memory_cost_is_low_for_boundary_return_and_high_for_containment_chain() -> None:
    low = engine_profile_evidence(spoon_ir())
    high_ir = spoon_ir()
    high_ir["engineProfile"] = {}
    high_ir["beats"] = high_ir["beats"] + [
        {"id": "b6", "majorBeat": True, "action": "reinsert the spoon inside the box", "consequence": "catch it outside again", "visualStateId": "inside"},
        {"id": "b7", "majorBeat": True, "action": "catch and reinsert the spoon", "consequence": "the object exits again", "visualStateId": "outside"},
    ]
    high = engine_profile_evidence(high_ir)
    assert low.state_memory_cost == "LOW"
    assert high.state_memory_cost == "HIGH"


def test_ruleset_1_6_remains_immutable_and_1_7_is_latest() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    assert manager.get_latest_version() == "1.7"
    stable = RuleEngine(str(settings.rules_dir / "RULESET_1.6.yaml"))
    latest = RuleEngine(RULESET)
    assert "STUBBORN_RETURN_LOOP" not in {rule["id"] for rule in stable.ruleset["rules"]}
    assert "STUBBORN_RETURN_LOOP" in {rule["id"] for rule in latest.ruleset["rules"]}
