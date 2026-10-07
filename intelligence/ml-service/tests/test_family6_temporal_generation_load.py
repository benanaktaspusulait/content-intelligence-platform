"""TDD contract tests for Family 6 temporal generation load evidence."""

from __future__ import annotations

from typing import Any

from app.quality.canonical_evidence import temporal_generation_load_evidence

AXES = {
    "temporal_packing",
    "state_breadth",
    "continuity_memory",
    "action_concurrency",
}


def beat(
    beat_id: str,
    *,
    start: float,
    end: float,
    actor: str = "Mimi",
    held_objects: list[str] | None = None,
    object_states: dict[str, str] | None = None,
    camera: str = "locked",
    environment: str = "room",
    unresolved_action: str | None = None,
    action: str = "Mimi observes one box",
    visual_state_id: str = "one_local_state",
) -> dict[str, Any]:
    return {
        "id": beat_id,
        "startTime": start,
        "endTime": end,
        "duration": end - start,
        "majorBeat": True,
        "beatRole": "ATTEMPT",
        "action": action,
        "consequence": "The local object state continues.",
        "visualStateId": visual_state_id,
        "actor": actor,
        "heldObjects": ["box"] if held_objects is None else held_objects,
        "objectStates": {"box": "closed"} if object_states is None else object_states,
        "camera": camera,
        "environment": environment,
        "unresolvedAction": unresolved_action,
    }


def structured_ir(
    *,
    generation_mode: str = "SINGLE_15S",
    duration: float = 15.0,
    beats: list[dict[str, Any]] | None = None,
    characters: dict[str, Any] | None = None,
    setting: dict[str, Any] | None = None,
    split_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ir: dict[str, Any] = {
        "metadata": {"duration": duration, "generationMode": generation_mode},
        "characters": characters or {"primary": "Mimi"},
        "setting": setting or {"mainProps": ["one box"]},
        "coreMechanic": {"physicalRule": "one stable rule"},
        "beats": beats or [],
    }
    if split_plan is not None:
        ir["splitPlan"] = split_plan
    return ir


def sequential_single_object_beats(count: int) -> list[dict[str, Any]]:
    return [
        beat(
            f"beat_{index:02d}",
            start=float(index - 1) * 1.5,
            end=float(index) * 1.5,
            action="Mimi performs the next sequential local action.",
        )
        for index in range(1, count + 1)
    ]


def severely_packed_coupled_beats() -> list[dict[str, Any]]:
    return [
        beat(
            "beat_01",
            start=0.0,
            end=1.0,
            actor="Mimi and Cat",
            held_objects=["ball", "box"],
            object_states={"ball": "airborne", "box": "open"},
            action="Mimi catches the ball while Cat enters the box.",
            unresolved_action="catch and enter simultaneously",
        ),
        beat(
            "beat_02",
            start=1.0,
            end=2.0,
            actor="Mimi and Cat",
            held_objects=["ball", "box"],
            object_states={"ball": "bouncing", "box": "occupied"},
            action="Mimi dodges the bouncing ball while Cat reclaims the box.",
            unresolved_action="dodge and reclaim simultaneously",
        ),
    ]


def target_switching_state_breadth_beats() -> list[dict[str, Any]]:
    return [
        beat(
            "spot_01",
            start=0.0,
            end=3.0,
            held_objects=["spot_a"],
            object_states={"spot_a": "targeted", "spot_b": "open", "spot_c": "open"},
            environment="room_three_spots",
            action="Kiko commits to spot A while Cat claims it.",
            visual_state_id="spot_a_claim",
        ),
        beat(
            "spot_02",
            start=3.0,
            end=6.0,
            held_objects=["spot_b"],
            object_states={"spot_a": "occupied", "spot_b": "targeted", "spot_c": "open"},
            environment="room_three_spots",
            action="Kiko changes to spot B while Cat tracks the new target.",
            visual_state_id="spot_b_claim",
        ),
        beat(
            "spot_03",
            start=6.0,
            end=9.0,
            held_objects=["spot_c"],
            object_states={"spot_a": "occupied", "spot_b": "occupied", "spot_c": "targeted"},
            environment="room_three_spots",
            action="Kiko decoys toward spot B and commits to spot C.",
            visual_state_id="spot_c_decoy",
        ),
    ]


def matching_continuation_contract() -> dict[str, Any]:
    state = {
        "character": "Mimi",
        "characterPoseIntent": "standing",
        "heldObjects": ["box"],
        "objectStates": {"box": "closed"},
        "camera": "locked",
        "environment": "room",
        "unresolvedAction": "observe",
    }
    return {"part1": {"endState": state}, "part2": {"startState": state.copy()}}


def test_one_severe_axis_is_high() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=severely_packed_coupled_beats())
    )
    assert evidence.status == "HIGH"
    assert evidence.high_basis == "SEVERE_AXIS:action_concurrency"


def test_two_elevated_axes_are_high() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=target_switching_state_breadth_beats())
    )
    assert evidence.status == "HIGH"
    assert evidence.severe_axis_count == 0
    assert evidence.elevated_axis_count >= 2


def test_many_beats_with_sequential_local_state_are_manageable() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=sequential_single_object_beats(count=7))
    )
    assert evidence.status == "MANAGEABLE"
    assert {axis.axis for axis in evidence.axes} == AXES


def test_missing_axis_evidence_is_unknown_not_not_applicable() -> None:
    evidence = temporal_generation_load_evidence(structured_ir())
    assert evidence.status == "UNKNOWN"
    assert all(axis.level == "UNKNOWN" for axis in evidence.axes)


def test_explicit_non_short_generation_mode_is_not_applicable() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(generation_mode="STILL_IMAGE")
    )
    assert evidence.status == "NOT_APPLICABLE"


def test_family6_serialization_uses_stable_camel_case_keys() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=sequential_single_object_beats(count=4))
    )
    payload = evidence.to_dict()
    assert set(payload) == {
        "status",
        "axes",
        "severeAxisCount",
        "elevatedAxisCount",
        "highBasis",
        "evidenceStatus",
        "version",
    }
    assert {axis["axis"] for axis in payload["axes"]} == AXES


def test_raw_beat_count_does_not_determine_family6_status() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=sequential_single_object_beats(count=7))
    )
    assert evidence.status == "MANAGEABLE"


def test_continuation_equality_does_not_make_family6_high_or_low() -> None:
    evidence = temporal_generation_load_evidence(
        structured_ir(
            generation_mode="SPLIT_2X15S",
            beats=sequential_single_object_beats(count=4),
            split_plan=matching_continuation_contract(),
        )
    )
    assert evidence.status in {"MANAGEABLE", "UNKNOWN"}
    continuity_axis = next(axis for axis in evidence.axes if axis.axis == "continuity_memory")
    assert continuity_axis.level != "SEVERE"



def test_partial_timing_ir_is_unknown_for_unrepresented_state_axes() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [{
            "id": "beat_01",
            "startTime": 0.0,
            "endTime": 3.0,
            "duration": 3.0,
            "action": "Mimi acts",
        }],
    }
    evidence = temporal_generation_load_evidence(ir)
    assert evidence.status == "UNKNOWN"
    assert next(axis for axis in evidence.axes if axis.axis == "action_concurrency").level == "UNKNOWN"
    assert {axis.level for axis in evidence.axes} >= {"UNKNOWN"}


def test_sequential_multi_actor_actions_are_not_severe_concurrency() -> None:
    beats = [
        beat(
            "beat_01",
            start=0.0,
            end=3.0,
            actor="Mimi and Cat",
            held_objects=["box", "ball"],
            unresolved_action="Mimi moves, then Cat moves",
        )
    ]
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=beats, setting={"mainProps": []})
    )
    concurrency = next(axis for axis in evidence.axes if axis.axis == "action_concurrency")
    assert concurrency.level != "SEVERE"
    assert evidence.status != "HIGH"



def test_structured_state_without_concurrency_fields_is_unknown_not_manageable() -> None:
    ir = structured_ir(
        beats=[{
            "id": "beat_01",
            "startTime": 0.0,
            "endTime": 3.0,
            "duration": 3.0,
            "objectStates": {"box": "closed"},
            "camera": "locked",
            "environment": "room",
        }]
    )
    evidence = temporal_generation_load_evidence(ir)
    concurrency = next(axis for axis in evidence.axes if axis.axis == "action_concurrency")
    assert concurrency.level == "UNKNOWN"
    assert evidence.status != "MANAGEABLE"



def test_negated_simultaneous_text_is_not_coupled_evidence() -> None:
    beats = [
        beat(
            "beat_01",
            start=0.0,
            end=3.0,
            actor="Mimi and Cat",
            held_objects=["box", "ball"],
            unresolved_action="Mimi and Cat do not act simultaneously",
        )
    ]
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=beats, setting={"mainProps": []})
    )
    concurrency = next(axis for axis in evidence.axes if axis.axis == "action_concurrency")
    assert concurrency.level != "SEVERE"
    assert evidence.status != "HIGH"



def test_coupling_signals_must_share_the_same_beat() -> None:
    beats = [
        beat(
            "actor_beat",
            start=0.0,
            end=3.0,
            actor="Mimi and Cat",
            held_objects=["box"],
            unresolved_action="Mimi moves, then Cat moves",
        ),
        beat(
            "object_beat",
            start=3.0,
            end=6.0,
            actor="Mimi",
            held_objects=["box", "ball"],
            unresolved_action="actions occur simultaneously",
        ),
    ]
    evidence = temporal_generation_load_evidence(
        structured_ir(beats=beats, setting={"mainProps": []})
    )
    concurrency = next(axis for axis in evidence.axes if axis.axis == "action_concurrency")
    assert concurrency.level != "SEVERE"
    assert evidence.status != "HIGH"


def test_common_negative_simultaneous_phrasings_are_not_coupled_evidence() -> None:
    for phrase in (
        "Mimi and Cat act non-simultaneously",
        "Mimi and Cat act sequentially rather than simultaneously",
        "Mimi and Cat act instead of simultaneously",
    ):
        beats = [
            beat(
                "beat_01",
                start=0.0,
                end=3.0,
                actor="Mimi and Cat",
                held_objects=["box", "ball"],
                unresolved_action=phrase,
            )
        ]
        evidence = temporal_generation_load_evidence(
            structured_ir(beats=beats, setting={"mainProps": []})
        )
        concurrency = next(axis for axis in evidence.axes if axis.axis == "action_concurrency")
        assert concurrency.level != "SEVERE"
        assert evidence.status != "HIGH"
