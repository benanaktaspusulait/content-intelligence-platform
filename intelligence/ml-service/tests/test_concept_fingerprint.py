from copy import deepcopy
import json
from pathlib import Path

from app.workflow.concept_fingerprint import compare, fingerprint

CASES = json.loads((Path(__file__).parent / "fixtures/concept_fingerprint_cases.json").read_text())


def test_user_spoon_and_brush_share_a_causal_core_despite_different_goals():
    a, b = fingerprint(CASES["growth_spoon"]), fingerprint(CASES["growth_brush"])
    assert a["fullHash"] != b["fullHash"]
    assert a["coreHash"] == b["coreHash"]
    assert a["dimensions"]["trigger"] == b["dimensions"]["trigger"] == "OBJECT_LIFT"
    assert a["dimensions"]["engineFamily"] == "PROGRESSIVE_GROWTH"
    result = compare(a, b)
    assert result["nearDuplicate"] and result["goalDifferenceIsCosmeticForEngine"]
    assert not result["materialDifferences"]


def test_user_shrinking_strategy_variant_is_materially_distinct():
    growth = fingerprint(CASES["growth_spoon"])
    shrinking = fingerprint(CASES["shrinking_strategy"])
    result = compare(growth, shrinking)
    assert not result["nearDuplicate"]
    assert {"trigger", "transformationDirection", "escalationTopology", "resolutionTopology"}.issubset(
        result["materialDifferences"]
    )
    assert shrinking["dimensions"]["trigger"] == "STRATEGY_CHANGE"
    assert shrinking["dimensions"]["resolutionTopology"] == "GOAL_REVERSAL"


def test_character_title_and_object_cosmetics_do_not_change_core():
    first = fingerprint(CASES["growth_spoon"])
    renamed = {
        **CASES["growth_spoon"],
        "title": "Different title",
        "protagonist": "Different character",
        "primaryObject": "hairbrush",
        "impossibleRule": CASES["growth_spoon"]["impossibleRule"].replace("spoon", "hairbrush"),
    }
    assert fingerprint(renamed)["coreHash"] == first["coreHash"]


def test_materially_different_authored_payoff_is_allowed():
    source = deepcopy(CASES["growth_spoon"])
    source["structuralPlan"] = {
        "resolutionTopology": "LOGICAL_EXTREME",
        "finalSilhouetteTopology": "TOOL_DOMINATES_USER",
    }
    other = deepcopy(source)
    other["structuralPlan"] = {
        "resolutionTopology": "GOAL_REVERSAL",
        "finalSilhouetteTopology": "USER_GROOMS_TOOL",
    }
    assert not compare(fingerprint(source), fingerprint(other))["nearDuplicate"]


def test_unknown_descriptions_do_not_become_positive_duplicate_evidence():
    assert not compare(fingerprint({}), fingerprint({}))["nearDuplicate"]


def test_descriptors_are_deterministic_and_do_not_mutate_source():
    original = deepcopy(CASES["growth_spoon"])
    assert fingerprint(original) == fingerprint(dict(reversed(list(original.items()))))
    assert original == CASES["growth_spoon"]
