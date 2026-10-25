import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.workflow import premise_naturalness as gate
from app.workflow.concept_fingerprint import digest


@pytest.fixture
def cases():
    return json.loads((Path(__file__).parent / "fixtures/premise_naturalness_v1_cases.json").read_text())[
        "cases"
    ]


@pytest.mark.parametrize(
    "name", ["shoe_reset", "brush_growth", "eraser_transfer", "wet_towel", "drawer_reversal"]
)
def test_strong_functional_contradictions(cases, name):
    r = gate.assess(cases[name])
    assert r["admitted"] and r["goalInterferenceType"] == "DIRECT"
    assert r["premiseNaturalness"] == "STRONG" and r["expectationDistance"] == "CLEAR_CONTRADICTION"
    assert r["objectSpecificityScore"] >= 75 and r["functionalIrony"] == "HIGH"
    assert r["physicalPayoffPotential"] >= 80


@pytest.mark.parametrize("name", ["fork_float", "can_adhesion", "pencil_adhesion", "generic_escape"])
def test_arbitrary_obstruction_rejected_even_with_natural_trigger(cases, name):
    r = gate.assess(cases[name])
    assert not r["admitted"]
    assert r["premiseNaturalness"] == "CONTRIVED"
    assert {"ARBITRARY_MAGIC_RELATIONSHIP", "GENERIC_ENGINE_APPLICATION"} <= {f["code"] for f in r["flags"]}
    assert r["objectSpecificityScore"] < 50


def test_trigger_naturalness_alone_is_insufficient(cases):
    good, bad = gate.assess(cases["brush_growth"]), gate.assess(cases["fork_float"])
    assert good["triggerNaturalness"] == bad["triggerNaturalness"] == 100
    assert good["physicalPayoffPotential"] > bad["physicalPayoffPotential"]
    assert good["goalInterferenceType"] == "DIRECT" and bad["goalInterferenceType"] == "CONTRIVED"


def test_functional_irony_and_material_connections(cases):
    eraser, towel, soap = [gate.assess(cases[k]) for k in ["eraser_transfer", "wet_towel", "soap_slip"]]
    assert [eraser["contradictionType"], towel["contradictionType"], soap["contradictionType"]] == [
        "TRANSFER",
        "FUNCTION_REVERSAL",
        "PROPERTY_EXAGGERATION",
    ]
    assert all(r["materialPropertyConnection"]["supportedInObjectData"] for r in [eraser, towel, soap])


def test_surreal_but_intuitive_is_retained(cases):
    r = gate.assess(cases["ball_weight"])
    assert r["admitted"] and r["premiseReviewStatus"] == "STRANGE_BUT_LEGIBLE"
    assert r["contradictionType"] == "PROPERTY_EXAGGERATION"


def test_object_swap_keeps_functional_dependency_fixed(cases):
    strong, weak = gate.assess(cases["eraser_transfer"]), gate.assess(cases["generic_escape"])
    assert strong["objectSwapTest"]["classification"] == "OBJECT_SPECIFIC_PREMISE"
    assert weak["objectSwapTest"]["classification"] == "GENERIC_ENGINE_APPLICATION"
    assert (
        strong["objectSwapTest"]["portableArchetypeFraction"]
        < weak["objectSwapTest"]["portableArchetypeFraction"]
    )
    assert all(s["functionalLogicPreserved"] for s in weak["objectSwapTest"]["comparisons"])


def test_frame_zero_cause_and_static_legibility_are_separate(cases):
    clear = gate.assess(cases["shoe_reset"])
    missing = deepcopy(cases["shoe_reset"])
    missing["frameZeroDescription"] = "Kiko holds a shoe."
    unclear = gate.assess(missing)
    assert clear["premiseNaturalness"] == unclear["premiseNaturalness"] == "STRONG"
    assert clear["instantCausalLegibility"] > unclear["instantCausalLegibility"]
    assert clear["staticFrameLegibility"] != clear["instantCausalLegibility"]
    assert any(f["code"] == "CAUSE_NOT_VISIBLE_AT_FRAME_ZERO" for f in unclear["flags"])


def test_ordinary_response_is_not_contradiction(cases):
    r = gate.assess(cases["ordinary_fork"])
    assert r["expectationDistance"] == "TOO_SMALL" and not r["admitted"]


def test_beat_scores_cannot_rescue_arbitrary_premise(cases):
    c = deepcopy(cases["fork_float"])
    before = gate.assess(c)
    c["beatGrammar"] = {
        "beatGrammarQuality": "STRONG",
        "strategyDiversityScore": 100,
        "consequenceDiversityScore": 100,
    }
    assert gate.assess(c) == before and not before["admitted"]


def test_unknown_response_is_unverified_broken_not_a_score(cases):
    c = {**cases["brush_growth"], "impossibleRule": "A mysterious indescribable event occurs."}
    r = gate.assess(c)
    assert r["premiseNaturalness"] == "BROKEN" and not r["admitted"]
    assert "NON_CANONICAL" in r["scoreUse"]


def test_expected_behavior_model_is_data_driven(cases):
    model = gate.load_model()
    before = digest(model)
    r = gate.assess(cases["shoe_reset"], model)
    assert r["primaryExpectedBehaviors"] == model["archetypes"]["FOOTWEAR"]["primaryExpectedBehaviors"]
    assert digest(model) == before
    candidate = deepcopy(cases["shoe_reset"])
    snapshot = digest(candidate)
    gate.assess(candidate)
    assert digest(candidate) == snapshot


def test_conflicting_declared_object_goal_is_preserved_and_flagged(cases):
    c = dict(
        primaryObject="towel",
        everydayGoal="fold a shirt",
        impossibleRule="The towel grows whenever pressed.",
        trigger="PRESSURE",
    )
    r = gate.assess(c)
    assert not r["admitted"]
    assert any(f["code"] == "DECLARED_GOAL_OBJECT_MISMATCH" for f in r["flags"])
