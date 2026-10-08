"""Family 10 RED contracts for independent risks and conservative aggregation."""

from copy import deepcopy

import pytest
from test_family10_general_producibility import beat, simple_sequential_ir, structured_ir

from app.quality.general_producibility import general_producibility_evidence


@pytest.mark.parametrize(
    ("field", "dimension"),
    [
        ("objectContinuity", "OBJECT_IDENTITY_CONTINUITY"),
        ("characterContinuity", "CHARACTER_IDENTITY_CONTINUITY"),
        ("contactPhysicsRequirement", "CONTACT_PHYSICS_COMPLEXITY"),
        ("transformationRequirement", "TRANSFORMATION_COMPLEXITY"),
        ("simulationRequirement", "LIQUID_CLOTH_PARTICLE"),
        ("spatialRequirement", "SPATIAL_RELATIONSHIP_COMPLEXITY"),
        ("sceneContinuityRequirement", "MULTI_SCENE_CONTINUITY"),
    ],
)
def test_required_precision_dependencies_are_independent(field, dimension):
    ir = simple_sequential_ir()
    ir[field] = {"required": True, "precision": "HIGH", "essential": True}
    result = general_producibility_evidence(ir)
    assert result["dimensions"][dimension]["level"] == "HIGH"
    assert result["status"] == "RISKY"
    ir[field]["requiresRedesign"] = True
    assert general_producibility_evidence(ir)["status"] == "NOT_PRODUCIBLE"


def test_non_video_artifact_is_not_applicable_only_when_explicit():
    result = general_producibility_evidence({"metadata": {"requiresGenerativeVideo": False}})
    assert result["status"] == "NOT_APPLICABLE"
    assert all(d["level"] == "NOT_APPLICABLE" for d in result["dimensions"].values())


def test_risky_a_grade_plan_is_pure_and_preserves_all_protected_fields():
    ir = simple_sequential_ir()
    ir.update(
        creativeGrade="A",
        creativeScore=98,
        evidenceCompleteness={"status": "COMPLETE"},
        renderAuthorization={"status": "AUTHORIZED"},
        fineMotorRequirement={"required": True, "precision": "HIGH"},
    )
    original = deepcopy(ir)
    result = general_producibility_evidence(ir)
    assert result["status"] == "RISKY"
    assert ir == original
    assert not set(result).intersection(
        {"creativeGrade", "creativeScore", "renderAuthorization", "evidenceCompleteness"}
    )


def test_missing_duration_is_unknown_and_not_defaulted_to_fifteen():
    ir = simple_sequential_ir()
    ir["metadata"].pop("duration")
    assert general_producibility_evidence(ir)["durationSeconds"] == 4
    for row in ir["beats"]:
        row.pop("startTime")
        row.pop("endTime")
        row.pop("duration")
    result = general_producibility_evidence(ir)
    assert result["durationSeconds"] is None
    assert result["status"] == "UNKNOWN"


def test_duration_aware_dependent_load_does_not_redefine_family6():
    ir = structured_ir(
        duration=6,
        beats=[
            beat(
                str(i),
                start=i * 0.5,
                end=(i + 1) * 0.5,
                action="Mimi moves box.",
                stateChangeRequired=True,
                dependsOnPreviousState=True,
            )
            for i in range(10)
        ],
    )
    short = general_producibility_evidence(ir)
    assert short["durationLoad"]["level"] == "HIGH"
    assert short["status"] == "RISKY"
    ir["metadata"]["duration"] = 30
    for i, row in enumerate(ir["beats"]):
        row.update(startTime=i * 3, endTime=(i + 1) * 3)
    long = general_producibility_evidence(ir)
    assert long["durationLoad"]["level"] == "LOW"
    assert long["status"] == "PRODUCIBLE"


def test_fine_precision_is_risky_despite_manageable_duration_load():
    ir = simple_sequential_ir(duration=30)
    ir["fineMotorRequirement"] = {"required": True, "precision": "HIGH"}
    result = general_producibility_evidence(ir)
    assert result["status"] == "RISKY"
    assert result["durationLoad"]["level"] == "LOW"


def test_legacy_keyword_risk_factors_and_performance_do_not_control_status():
    ir = simple_sequential_ir()
    ir.update(
        producibility={"overallComplexity": "very_high", "riskFactors": ["liquid physics"]},
        performanceClass="WINNER",
        virality=100,
        creativeGrade="C",
    )
    assert general_producibility_evidence(ir)["status"] == "PRODUCIBLE"


def test_optional_high_precision_is_not_a_required_risk():
    ir = simple_sequential_ir()
    ir["textRequirement"] = {"required": False, "exactText": "ABC", "readable": True}
    assert general_producibility_evidence(ir)["dimensions"]["TEXT_LIP_SYNC_SYMBOL"]["level"] == "LOW"


def test_entity_tracking_excludes_unimportant_decoration():
    ir = simple_sequential_ir()
    ir["setting"]["backgroundDecoration"] = ["flower"] * 100
    assert general_producibility_evidence(ir)["dimensions"]["ENTITY_LOAD"]["level"] == "LOW"
    ir["beats"][0].update(
        movingEntities=["Mimi", "box", "ball", "chair", "cat", "cup"],
        simultaneous=True,
        independentMotion=True,
    )
    assert general_producibility_evidence(ir)["dimensions"]["ENTITY_LOAD"]["level"] == "HIGH"


def test_partial_ir_has_unknown_axes_without_fabricated_failure():
    result = general_producibility_evidence({"metadata": {"duration": 12}, "beats": []})
    assert result["status"] == "UNKNOWN"
    assert result["durationLoad"]["level"] == "UNKNOWN"
    assert all(d["level"] == "UNKNOWN" for d in result["dimensions"].values())


def test_family6_severe_concurrency_is_consumed_without_blanket_high_mapping():
    ir = structured_ir(
        duration=12,
        beats=[
            {
                "id": "coupled",
                "startTime": 0,
                "endTime": 2,
                "actor": "Mimi and Cat",
                "heldObjects": ["ball", "box"],
                "action": "Mimi catches while Cat pushes.",
                "unresolvedAction": "catch and push simultaneously",
            }
        ],
    )
    result = general_producibility_evidence(ir)
    assert result["dimensions"]["MULTI_ENTITY_CONCURRENCY"]["level"] == "HIGH"
    assert (
        "family6.action_concurrency" in result["dimensions"]["MULTI_ENTITY_CONCURRENCY"]["evidenceReferences"]
    )
    assert result["status"] == "RISKY"


def test_explicit_dimension_not_applicable_is_preserved():
    ir = simple_sequential_ir()
    ir["textRequirement"] = {"applicable": False}
    assert (
        general_producibility_evidence(ir)["dimensions"]["TEXT_LIP_SYNC_SYMBOL"]["level"] == "NOT_APPLICABLE"
    )


def test_one_character_without_props_is_still_a_video_plan():
    ir = simple_sequential_ir()
    for row in ir["beats"]:
        row.update(action="Mimi walks.", objects=[])
    assert general_producibility_evidence(ir)["status"] == "PRODUCIBLE"


@pytest.mark.parametrize("duration", [5, 8, 12, 18, 25, 30, 65])
def test_no_universal_duration_or_generation_segment_limit(duration):
    assert general_producibility_evidence(simple_sequential_ir(duration=duration))["status"] == "PRODUCIBLE"


def test_moderate_nonmaterial_risks_do_not_aggressively_block_a_simple_plan():
    ir = simple_sequential_ir()
    for field in ("simulationRequirement", "spatialRequirement", "contactPhysicsRequirement"):
        ir[field] = {"required": True, "precision": "MODERATE", "material": False}
    assert general_producibility_evidence(ir)["status"] == "PRODUCIBLE"


def test_occlusion_of_one_entity_is_not_continuity_of_a_different_entity():
    ir = simple_sequential_ir()
    ir["beats"][0]["visibility"] = {"object": "box", "state": "FULLY_OCCLUDED"}
    ir["beats"][1]["requiredReappearance"] = {"object": "ball", "mustReturnVisible": True}
    assert general_producibility_evidence(ir)["dimensions"]["OBJECT_IDENTITY_CONTINUITY"]["level"] == "LOW"


def test_character_occlusion_is_separate_from_object_identity():
    ir = simple_sequential_ir()
    ir["beats"][0]["visibility"] = {"character": "Mimi", "state": "FULLY_OCCLUDED"}
    ir["beats"][1]["requiredReappearance"] = {"character": "Mimi", "mustReturnVisible": True}
    result = general_producibility_evidence(ir)
    assert result["dimensions"]["CHARACTER_IDENTITY_CONTINUITY"]["level"] == "MODERATE"
    assert result["dimensions"]["OBJECT_IDENTITY_CONTINUITY"]["level"] == "LOW"


def test_multiple_independent_segments_do_not_require_a_state_handoff():
    ir = simple_sequential_ir()
    ir["splitPlan"] = {"required": True, "continuityRequired": False, "segments": [{}, {}]}
    result = general_producibility_evidence(ir)
    assert result["status"] == "PRODUCIBLE"
    assert result["dimensions"]["SEGMENT_CONTINUITY"]["level"] == "NOT_APPLICABLE"
