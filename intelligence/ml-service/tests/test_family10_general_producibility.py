"""RED contract tests for Family 10 general producibility evidence.

The implementation is intentionally absent in the RED phase.  These tests define the
structured IR signals and the future public projection that should evaluate them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from app.quality.general_producibility import (
    GENERAL_PRODUCIBILITY_DIMENSIONS,
    GENERAL_PRODUCIBILITY_STATUSES,
    general_producibility_evidence,
)

REQUIRED_DIMENSIONS = (
    "ENTITY_LOAD",
    "OBJECT_IDENTITY_CONTINUITY",
    "CHARACTER_IDENTITY_CONTINUITY",
    "FINE_MOTOR_PRECISION",
    "CONTACT_PHYSICS_COMPLEXITY",
    "OCCLUSION_HIDDEN_STATE",
    "EXACT_COUNT_DEPENDENCY",
    "MULTI_ENTITY_CONCURRENCY",
    "TRANSFORMATION_COMPLEXITY",
    "LIQUID_CLOTH_PARTICLE",
    "SPATIAL_RELATIONSHIP_COMPLEXITY",
    "CAMERA_ACTION_COUPLING",
    "MULTI_SCENE_CONTINUITY",
    "TEXT_LIP_SYNC_SYMBOL",
    "SEGMENT_CONTINUITY",
)
REQUIRED_STATUSES = {
    "PRODUCIBLE",
    "RISKY",
    "NOT_PRODUCIBLE",
    "UNKNOWN",
    "NOT_APPLICABLE",
}


def beat(
    beat_id: str,
    *,
    start: float,
    end: float,
    action: str,
    actors: tuple[str, ...] = ("Mimi",),
    objects: tuple[str, ...] = ("box",),
    **evidence: Any,
) -> dict[str, Any]:
    """Build one timestamped, structured beat with optional risk evidence."""
    return {
        "id": beat_id,
        "startTime": start,
        "endTime": end,
        "duration": end - start,
        "majorBeat": True,
        "beatRole": "ATTEMPT",
        "actors": list(actors),
        "objects": list(objects),
        "action": action,
        "consequence": "The described local state continues.",
        **evidence,
    }


def structured_ir(
    *,
    duration: float = 6.0,
    beats: list[dict[str, Any]] | None = None,
    generation_mode: str = "SINGLE",
    **overrides: Any,
) -> dict[str, Any]:
    """Build the smallest general-purpose video-plan IR used by these contracts."""
    ir: dict[str, Any] = {
        "metadata": {"duration": duration, "generationMode": generation_mode},
        "characters": {"primary": "Mimi", "count": 1},
        "setting": {"mainProps": ["box"], "objectCount": 1},
        "coreMechanic": {"physicalRule": "Direct contact moves one local object."},
        "beats": beats or [],
    }
    ir.update(overrides)
    return ir


def simple_sequential_ir(*, duration: float = 6.0) -> dict[str, Any]:
    return structured_ir(
        duration=duration,
        beats=[
            beat(
                "push_box",
                start=0.0,
                end=2.0,
                action="Mimi pushes the box across the table.",
                contactType="PUSH",
            ),
            beat(
                "pull_box",
                start=2.0,
                end=4.0,
                action="Mimi pulls the same box back.",
                contactType="PULL",
            ),
        ],
    )


def _read(value: Any, *names: str) -> Any:
    for name in names:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if hasattr(value, name):
            return getattr(value, name)
    raise AssertionError(f"Expected one of {names!r} on {value!r}")


def _status(evidence: Any) -> str:
    return str(_read(evidence, "status"))


def _dimensions(evidence: Any) -> Mapping[str, Any]:
    dimensions = _read(evidence, "dimensions")
    assert isinstance(dimensions, Mapping)
    return dimensions


def _dimension(evidence: Any, key: str) -> Any:
    dimensions = _dimensions(evidence)
    assert key in dimensions
    return dimensions[key]


def _level(evidence: Any, key: str) -> str:
    return str(_read(_dimension(evidence, key), "level", "status"))


def _references(evidence: Any, key: str) -> Any:
    return _read(_dimension(evidence, key), "evidence_references", "evidenceReferences")


def _payload(evidence: Any) -> Mapping[str, Any]:
    if isinstance(evidence, Mapping):
        payload = evidence
    else:
        serializer = getattr(evidence, "to_dict", None)
        assert callable(serializer), "Evidence must expose a structured mapping or to_dict()."
        payload = serializer()
    assert isinstance(payload, Mapping)
    return payload


def _contains_key(value: Any, key: str) -> bool:
    if isinstance(value, Mapping):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_key(item, key) for item in value)
    return False


def _assert_risk_dimension(evidence: Any, key: str) -> None:
    assert _status(evidence) in {"RISKY", "NOT_PRODUCIBLE"}
    assert _level(evidence, key) not in {"LOW", "UNKNOWN", "NOT_APPLICABLE"}


def test_general_producibility_exposes_all_dimensions_and_exact_status_vocabulary() -> None:
    evidence = general_producibility_evidence(simple_sequential_ir())

    assert set(GENERAL_PRODUCIBILITY_DIMENSIONS) == set(REQUIRED_DIMENSIONS)
    assert set(GENERAL_PRODUCIBILITY_STATUSES) == REQUIRED_STATUSES
    assert _status(evidence) in REQUIRED_STATUSES

    payload = _payload(evidence)
    assert "status" in payload
    assert "dimensions" in payload
    dimensions = _dimensions(evidence)
    assert set(dimensions) == set(REQUIRED_DIMENSIONS)
    for key in REQUIRED_DIMENSIONS:
        dimension = dimensions[key]
        level = _read(dimension, "level", "status")
        references = _references(evidence, key)
        reason = _read(dimension, "reason")
        assert isinstance(level, str) and level
        assert isinstance(references, (list, tuple))
        assert all(isinstance(reference, str) and reference for reference in references)
        assert isinstance(reason, str) and reason.strip()


def test_simple_one_character_one_object_push_pull_sequence_is_producible() -> None:
    evidence = general_producibility_evidence(simple_sequential_ir())

    assert _status(evidence) == "PRODUCIBLE"


def test_fine_motor_precision_is_high_and_can_block_or_warn() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "thread_needle",
                    start=0.0,
                    end=3.0,
                    action="Mimi pinches a tiny thread and threads it through a needle eye.",
                    objects=("thread", "needle"),
                    fineMotorRequirement={
                        "required": True,
                        "precision": "TINY_PINCHING_THREADING",
                    },
                )
            ],
            setting={"mainProps": ["thread", "needle"], "objectCount": 2},
        )
    )

    assert _status(evidence) in {"RISKY", "NOT_PRODUCIBLE"}
    assert _level(evidence, "FINE_MOTOR_PRECISION") == "HIGH"


def test_fully_occluded_object_that_must_return_represents_occlusion_risk() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "hide_key",
                    start=0.0,
                    end=2.0,
                    action="Mimi slides the key behind the sofa until it is fully hidden.",
                    objects=("key", "sofa"),
                    visibility={
                        "object": "key",
                        "state": "FULLY_OCCLUDED",
                        "occluder": "sofa",
                    },
                ),
                beat(
                    "return_key",
                    start=2.0,
                    end=4.0,
                    action="Mimi retrieves the hidden key from behind the sofa.",
                    objects=("key", "sofa"),
                    requiredReappearance={"object": "key", "mustReturnVisible": True},
                ),
            ],
            setting={"mainProps": ["key", "sofa"], "objectCount": 2},
            objectContinuity={"required": True, "trackedObject": "key"},
        )
    )

    _assert_risk_dimension(evidence, "OCCLUSION_HIDDEN_STATE")


def test_independent_simultaneous_actor_and_object_motion_is_concurrency_risk() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "simultaneous_motion",
                    start=0.0,
                    end=2.0,
                    action="Mimi moves the ball while Cat moves the box at the same time.",
                    actors=("Mimi", "Cat"),
                    objects=("ball", "box"),
                    simultaneous=True,
                    independentMotion=True,
                    movingEntities=("Mimi", "Cat", "ball", "box"),
                )
            ],
            characters={"primary": "Mimi", "others": ["Cat"], "count": 2},
            setting={"mainProps": ["ball", "box"], "objectCount": 2},
        )
    )

    _assert_risk_dimension(evidence, "MULTI_ENTITY_CONCURRENCY")


def test_exact_quantity_required_across_stages_is_count_dependency_risk() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "count_start",
                    start=0.0,
                    end=2.0,
                    action="Mimi places exactly three marbles in the tray.",
                    objects=("marble_1", "marble_2", "marble_3", "tray"),
                    quantityAtStage={"object": "marble", "count": 3, "exact": True},
                ),
                beat(
                    "count_end",
                    start=2.0,
                    end=4.0,
                    action="The same three marbles remain in the tray.",
                    objects=("marble_1", "marble_2", "marble_3", "tray"),
                    quantityAtStage={"object": "marble", "count": 3, "exact": True},
                ),
            ],
            setting={"mainProps": ["marbles", "tray"], "objectCount": 4},
            exactCountDependency={
                "required": True,
                "trackedObject": "marble",
                "requiredCount": 3,
                "acrossStages": True,
            },
        )
    )

    _assert_risk_dimension(evidence, "EXACT_COUNT_DEPENDENCY")


def test_absurd_sticky_ball_physics_is_not_an_automatic_not_producible_result() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "throw_ball",
                    start=0.0,
                    end=2.0,
                    action="Mimi throws the sticky ball toward the wall.",
                    objects=("sticky_ball", "wall"),
                    physics={"impossible": True, "rule": "sticky_ball_sticks_to_wall"},
                ),
                beat(
                    "ball_sticks",
                    start=2.0,
                    end=4.0,
                    action="The sticky ball sticks to the wall and stays there.",
                    objects=("sticky_ball", "wall"),
                    physics={"impossible": True, "rule": "sticky_ball_sticks_to_wall"},
                ),
            ],
            coreMechanic={"physicalRule": "A sticky ball sticks to a wall."},
            setting={"mainProps": ["sticky_ball", "wall"], "objectCount": 2},
        )
    )

    assert _status(evidence) in {"PRODUCIBLE", "RISKY"}
    assert _status(evidence) != "NOT_PRODUCIBLE"


def test_optional_dialogue_or_text_does_not_create_text_lipsync_failure() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "optional_dialogue",
                    start=0.0,
                    end=2.0,
                    action="Mimi pushes the box while optionally saying hello.",
                    optionalDialogue={
                        "text": "Hello!",
                        "required": False,
                        "lipSyncRequired": False,
                    },
                )
            ],
            dialogueRequirement={"required": False},
        )
    )

    assert _status(evidence) != "NOT_PRODUCIBLE"
    assert _level(evidence, "TEXT_LIP_SYNC_SYMBOL") != "HIGH"


def test_exact_readable_letters_required_are_text_lipsync_symbol_risk() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "read_letters",
                    start=0.0,
                    end=2.0,
                    action="Mimi holds a card whose exact readable letters must be ABC.",
                    objects=("card",),
                    textRequirement={
                        "required": True,
                        "exactText": "ABC",
                        "readable": True,
                        "lettersMustMatch": True,
                    },
                )
            ],
            setting={"mainProps": ["card"], "objectCount": 1},
        )
    )

    _assert_risk_dimension(evidence, "TEXT_LIP_SYNC_SYMBOL")


def test_complex_camera_motion_coupled_to_object_interaction_is_camera_risk() -> None:
    evidence = general_producibility_evidence(
        structured_ir(
            beats=[
                beat(
                    "coupled_camera_action",
                    start=0.0,
                    end=3.0,
                    action="The camera orbits and pushes in while Mimi spins and catches the box.",
                    objects=("box",),
                    camera={
                        "movement": "ORBIT_PUSH_IN_RACK_FOCUS",
                        "complexity": "HIGH",
                        "coupledToInteraction": True,
                    },
                    objectInteraction={
                        "complexity": "HIGH",
                        "requiresSynchronizedCamera": True,
                    },
                )
            ]
        )
    )

    _assert_risk_dimension(evidence, "CAMERA_ACTION_COUPLING")


@pytest.mark.parametrize("missing_ir", [None, {}], ids=["null", "missing-structure"])
def test_missing_structured_evidence_is_explicitly_unknown(missing_ir: dict[str, Any] | None) -> None:
    evidence = general_producibility_evidence(missing_ir)

    assert _status(evidence) == "UNKNOWN"
    assert _status(evidence) not in {"FAIL", "NOT_PRODUCIBLE"}
    for key in REQUIRED_DIMENSIONS:
        assert _level(evidence, key) == "UNKNOWN"


def test_unrelated_creative_grade_does_not_change_producibility_projection() -> None:
    plain = general_producibility_evidence(simple_sequential_ir())
    with_creative_grade = simple_sequential_ir()
    with_creative_grade["creativeGrade"] = "A"
    graded = general_producibility_evidence(with_creative_grade)

    assert _status(plain) == "PRODUCIBLE"
    assert _status(graded) == _status(plain)
    assert not _contains_key(_payload(graded), "creativeGrade")


@pytest.mark.parametrize("duration", [6.0, 28.0])
def test_same_simple_sequence_is_not_rejected_merely_for_duration(duration: float) -> None:
    evidence = general_producibility_evidence(simple_sequential_ir(duration=duration))

    assert _status(evidence) == "PRODUCIBLE"


def test_explicit_multi_segment_state_handoff_represents_segment_continuity_risk() -> None:
    handoff_state = {
        "character": "Mimi",
        "characterPose": "standing",
        "heldObjects": ["box"],
        "objectStates": {"box": "open"},
        "unresolvedAction": "return box to shelf",
    }
    evidence = general_producibility_evidence(
        structured_ir(
            duration=28.0,
            generation_mode="SPLIT_2X15S",
            beats=[
                beat(
                    "part1_end",
                    start=0.0,
                    end=14.0,
                    action="Mimi opens the box and pauses before returning it.",
                ),
                beat(
                    "part2_start",
                    start=14.0,
                    end=28.0,
                    action="Mimi continues the return action with the box.",
                ),
            ],
            splitPlan={
                "required": True,
                "part1": {"endState": handoff_state},
                "part2": {"startState": dict(handoff_state)},
            },
            segmentContinuityRequirement={
                "required": True,
                "handoff": "part1.endState -> part2.startState",
                "fields": ["character", "heldObjects", "objectStates", "unresolvedAction"],
            },
        )
    )

    _assert_risk_dimension(evidence, "SEGMENT_CONTINUITY")
    assert _references(evidence, "SEGMENT_CONTINUITY")
