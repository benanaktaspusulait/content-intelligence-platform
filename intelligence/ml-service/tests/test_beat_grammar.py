from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.workflow import beat_grammar as bg
from app.workflow.concept_fingerprint import digest


@pytest.fixture
def reference():
    return json.loads((Path(__file__).parent / "fixtures/beat_grammar_v2_reference.json").read_text())


def test_reference_shoe_is_strong_but_not_a_generator_recipe(reference):
    result = bg.assess(reference["shoeGolden"], reference["composition"])
    assert result["beatGrammarQuality"] == "STRONG"
    assert result["strategyDiversityScore"] == result["consequenceDiversityScore"] == 100
    assert result["bodyStateProgressionScore"] >= 80 and result["payoffDistance"] >= 0.5
    assert reference["shoeGolden"][-1]["payoffStateChange"] == "OPENING_PROBLEM_RETURNS"
    assert "sock" in reference["shoeGolden"][-1]["referenceText"]
    assert len({b["impossibleRule"] for b in reference["shoeGolden"]}) == 1
    assert len({b["consequenceType"] for b in reference["shoeGolden"]}) >= 3


def test_mechanical_reference_has_required_flags(reference):
    result = bg.assess(reference["mechanicalNegative"])
    codes = {f["code"] for f in result["flags"]}
    assert {
        "LOW_STRATEGY_DIVERSITY",
        "LOW_CONSEQUENCE_DIVERSITY",
        "NEAR_DUPLICATE_ATTEMPTS",
        "LOW_INFORMATION_GAIN",
        "LOW_PAYOFF_DISTANCE",
    } <= codes
    assert result["beatGrammarQuality"] == "MECHANICAL"


def test_wording_and_one_hand_to_two_hands_do_not_create_new_strategy(reference):
    a, b = deepcopy(reference["mechanicalNegative"][:2])
    a["characterStrategy"] = "DIRECT_USE"
    b["characterStrategy"] = "TWO_HAND_FORCE"
    b["objectResponse"] = "Entirely different wording for the identical state"
    assert bg.attempt_signature(a)["strategyType"] == bg.attempt_signature(b)["strategyType"]
    assert bg.compare_attempts(a, b)["classification"] == "IDENTICAL_ATTEMPT"


def test_trigger_can_stay_identical_while_body_consequence_changes(reference):
    a, b = reference["shoeGolden"][0], reference["shoeGolden"][2]
    assert a["trigger"] == b["trigger"]
    assert bg.compare_attempts(a, b)["classification"] == "DISTINCT_ATTEMPT"


def test_body_and_spatial_state_evidence_is_explicit(reference):
    result = bg.assess(reference["shoeGolden"])
    assert "DRAGGED" in result["bodyStateSequence"]
    assert result["spatialProgressionScore"] > 50
    assert result["attemptSignatures"][2]["spatialChange"]["horizontalDisplacement"] == "BACKWARD"


def test_missing_information_is_flagged(reference):
    plan = deepcopy(reference["shoeGolden"])
    plan[2]["newInformation"] = []
    result = bg.assess(plan)
    assert any(f["code"] == "NON_PROGRESSIVE_BEAT" and f["beatNumber"] == 3 for f in result["flags"])


def test_payoff_distance_ignores_magnitude_and_wording(reference):
    plan = deepcopy(reference["mechanicalNegative"])
    plan[-1]["objectStateAfter"]["applicationCount"] = 100000
    assert bg.payoff_distance(plan)["distance"] < 0.5
    assert bg.payoff_distance(reference["shoeGolden"])["distance"] >= 0.5


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("rule", "DOMINANT_RULE_CHANGED"),
        ("continuity", "STATE_CONTINUITY_BROKEN"),
        ("untriggered", "UNTRIGGERED_OBJECT_STATE_CHANGE"),
        ("schema", "INCOMPLETE_ATTEMPT_SIGNATURE"),
    ],
)
def test_invalid_state_or_rule_is_broken(reference, mutation, code):
    plan = deepcopy(reference["shoeGolden"])
    if mutation == "rule":
        plan[2]["impossibleRule"] = "Suddenly flies for unrelated reasons"
    elif mutation == "continuity":
        plan[2]["bodyStateBefore"] = "UNKNOWN"
    elif mutation == "untriggered":
        plan[1]["trigger"] = "NONE"
    else:
        del plan[2]["newInformation"]
    result = bg.assess(plan)
    assert result["beatGrammarQuality"] == "BROKEN"
    assert code in {f["code"] for f in result["flags"]}


@pytest.mark.parametrize(
    "object_id,strategy",
    [("eraser", "ANCHOR_TO_ENVIRONMENT"), ("pencil", "USE_BODY_WEIGHT"), ("shoe", "MOVE_UNDER_OBJECT")],
)
def test_strategy_compatibility_rejects_nonsense(reference, object_id, strategy):
    comp = {**reference["composition"], "objectId": object_id}
    assert bg.compatible(strategy, comp)


def test_environment_anchor_and_body_load_are_supported_on_shoe(reference):
    assert not bg.compatible("ANCHOR_TO_ENVIRONMENT", reference["composition"])
    assert not bg.compatible("USE_BODY_WEIGHT", reference["composition"])


def test_production_complexity_is_separate_from_creative_evidence(reference):
    plan = deepcopy(reference["shoeGolden"])
    plan[1]["characterStrategy"] = "PRECISION_HANDOFF"
    result = bg.assess(plan)
    assert "RAPID_HANDOFF" in result["productionFeasibility"]["flags"]
    assert result["productionFeasibility"]["score"] < 100
    assert result["scoreUse"] == "NON_CANONICAL_GENERATION_REVIEW_NOT_RETENTION"


def test_concentration_guard_tracks_under_object_and_force(reference):
    candidate = {
        "beatGrammar": bg.assess(reference["mechanicalNegative"]),
        "progressionShape": "LINEAR_MAGNITUDE",
        "composition": {"escalationTopology": "LINEAR_MAGNITUDE"},
    }
    result = bg.batch_evidence([candidate] * 10)
    assert {
        "MOVE_UNDER_OBJECT_CONCENTRATION",
        "FORCE_ESCALATION_CONCENTRATION",
        "LINEAR_MAGNITUDE_CONCENTRATION",
    } <= {f["code"] for f in result["concentrationWarnings"]}


def test_attempt_similarity_symmetric_and_no_input_mutation(reference):
    a, b = reference["shoeGolden"][:2]
    before = digest(reference)
    assert bg.compare_attempts(a, b) == bg.compare_attempts(b, a)
    bg.assess(reference["shoeGolden"])
    assert digest(reference) == before


def test_shape_compatibility_excludes_shrinking_space_collapse(reference):
    composition = {
        **reference["composition"],
        "stateTransition": "SCALE_DOWN",
        "engineFamily": "PROGRESSIVE_SHRINK",
    }
    with pytest.raises(ValueError, match="PROGRESSION_SHAPE_ENGINE_MISMATCH"):
        bg.build_plan(composition, "SPACE_COLLAPSE")
