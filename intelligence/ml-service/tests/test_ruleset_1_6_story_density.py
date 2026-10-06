"""RED tests for the immutable RULESET_1.6 mini-story and temporal policy."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.quality.canonical_evidence import story_density_evidence
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager

RULESET = str(settings.rules_dir / "RULESET_1.6.yaml")


def engine() -> RuleEngine:
    return RuleEngine(RULESET)


def structured_ir(
    *,
    goal_explicitness: str = "IMPLICIT_BUT_OBSERVABLE",
    generation_mode: str = "SINGLE_15S",
    major_beats: int = 4,
    micro_beats: int = 0,
    transitions: int | None = None,
) -> dict[str, Any]:
    beats: list[dict[str, Any]] = []
    for index in range(major_beats):
        role = ["HOOK", "ATTEMPT", "REALIZATION", "PAYOFF"][min(index, 3)]
        beats.append(
            {
                "id": f"beat_{index + 1:02d}",
                "startTime": float(index * 3),
                "endTime": float((index + 1) * 3),
                "duration": 3.0,
                "majorBeat": True,
                "beatRole": role,
                "action": f"Mimi performs major action {index}",
                "consequence": f"Object changes state {index}",
                "visualStateId": f"state_{index}",
                "consequenceType": "new",
                "intensity": index + 4,
                "isAttempt": index in {1, 2},
                "primaryVerb": "PULL" if index == 1 else "PUSH" if index == 2 else "",
                "strategyFamily": "PULL" if index == 1 else "PUSH" if index == 2 else "",
                "relatesToCoreProblem": True,
            }
        )
    for index in range(micro_beats):
        beats.append(
            {
                "id": f"micro_{index + 1:02d}",
                "startTime": 0.0,
                "endTime": 0.2,
                "duration": 0.2,
                "majorBeat": False,
                "beatRole": "REACTION",
                "action": "Mimi blinks",
                "consequence": "Mimi changes expression",
                "visualStateId": "micro",
                "consequenceType": "continuation",
                "intensity": 4,
                "isAttempt": False,
                "primaryVerb": "",
                "strategyFamily": "",
            }
        )
    ir: dict[str, Any] = {
        "metadata": {"duration": 15.0, "generationMode": generation_mode},
        "characters": {"primary": "Mimi"},
        "goalEvidence": {
            "goalExplicitness": goal_explicitness,
            "goalType": "RETRIEVE_OR_CONTROL_OBJECT" if goal_explicitness != "UNSUPPORTED" else None,
            "description": "Put the red ball in the box" if goal_explicitness != "UNSUPPORTED" else None,
            "targetObject": "red ball",
            "obstruction": "The ball sticks to the wall",
            "intendedEffect": "restore_or_control_normal_object_use",
        },
        "coreMechanic": {
            "physicalRule": "The red ball sticks to surfaces instead of bouncing.",
            "abnormalProperty": "STICKS_TO_SURFACES",
        },
        "beats": beats,
        "finalPayoff": {"startsAt": 12.0, "endsAt": 15.0},
        "setting": {"mainProps": ["red ball", "box"]},
    }
    if transitions is not None:
        ir["storyEvidence"] = {"stateTransitionCount": transitions}
    return ir


def split_ir(part1_end: dict[str, Any], part2_start: dict[str, Any]) -> dict[str, Any]:
    ir = structured_ir(generation_mode="SPLIT_2X15S", major_beats=5, transitions=5)
    ir["splitPlan"] = {
        "part1": {"endState": part1_end},
        "part2": {"startState": part2_start},
    }
    return ir


def test_story_lock_accepts_readable_story_without_fake_resolution() -> None:
    result = engine()._evaluate_mini_story_lock(structured_ir(), {})
    assert result.outcome is RuleOutcome.PASS
    assert result.details["fake_resolution"] == "OPTIONAL"
    assert result.details["recurrence"] == "OPTIONAL"


def test_story_lock_fails_when_no_believable_goal_exists() -> None:
    result = engine()._evaluate_mini_story_lock(
        structured_ir(goal_explicitness="UNSUPPORTED"), {}
    )
    assert result.outcome is RuleOutcome.FAIL


def test_major_beat_filter_excludes_micro_actions() -> None:
    evidence = story_density_evidence(structured_ir(major_beats=4, micro_beats=3))
    assert evidence.major_beat_count == 4
    assert evidence.micro_beat_count == 3


def test_seven_raw_entries_with_four_major_beats_are_not_overblocked() -> None:
    ir = structured_ir(major_beats=4, micro_beats=3, transitions=4)
    evidence = story_density_evidence(ir)
    assert len(ir["beats"]) == 7
    assert evidence.major_beat_count == 4
    result = engine()._evaluate_temporal_complexity_split_gate(ir, {})
    assert result.outcome is not RuleOutcome.FAIL


def test_temporal_overload_blocks_single_generation_and_recommends_split() -> None:
    ir = structured_ir(generation_mode="SINGLE_15S", major_beats=7, transitions=8)
    result = engine()._evaluate_temporal_complexity_split_gate(ir, {})
    assert result.outcome is RuleOutcome.FAIL
    assert result.actual_value == "BLOCK_SINGLE_GENERATION"
    assert result.details["recommendation"] == "RECOMMEND_SPLIT_2X15"


def test_temporal_overload_passes_when_explicitly_split() -> None:
    ir = structured_ir(generation_mode="SPLIT_2X15S", major_beats=7, transitions=8)
    result = engine()._evaluate_temporal_complexity_split_gate(ir, {})
    assert result.outcome is RuleOutcome.PASS
    assert result.details["mode"] == "SPLIT_2X15S"


def test_beat_density_requires_four_major_beats_but_allows_micro_actions() -> None:
    low = engine()._evaluate_beat_density_rule(structured_ir(major_beats=3), {})
    good = engine()._evaluate_beat_density_rule(structured_ir(major_beats=4, micro_beats=3), {})
    high = engine()._evaluate_beat_density_rule(structured_ir(major_beats=7), {})
    assert low.outcome is RuleOutcome.FAIL
    assert good.outcome is RuleOutcome.PASS
    assert high.outcome is RuleOutcome.FAIL


def test_goal_visible_early_fails_late_or_unsupported_goal() -> None:
    late = structured_ir(goal_explicitness="UNSUPPORTED")
    late["beats"][0]["goalEvidence"] = {"goalExplicitness": "UNSUPPORTED"}
    result = engine()._evaluate_goal_visible_early(late, {})
    assert result.outcome is RuleOutcome.FAIL


def test_continuation_lock_compares_planned_states_only() -> None:
    mismatch = split_ir({"objectState": "STUCK"}, {"objectState": "NORMAL"})
    result = engine()._evaluate_continuation_lock(mismatch, {})
    assert result.outcome is RuleOutcome.FAIL
    assert result.details["analysisStage"] == "PRE_RENDER_PLAN_CONTRACT"


def test_continuation_lock_is_not_applicable_for_single_generation() -> None:
    result = engine()._evaluate_continuation_lock(structured_ir(), {})
    assert result.outcome is RuleOutcome.NOT_APPLICABLE


def test_ruleset_1_5_remains_immutable_and_1_6_is_latest() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    assert manager.get_latest_version() == "1.7"
    old = RuleEngine(str(settings.rules_dir / "RULESET_1.5.yaml"))
    new = RuleEngine(RULESET)
    assert "MINI_STORY_LOCK" not in {rule["id"] for rule in old.ruleset["rules"]}
    assert "MINI_STORY_LOCK" in {rule["id"] for rule in new.ruleset["rules"]}
