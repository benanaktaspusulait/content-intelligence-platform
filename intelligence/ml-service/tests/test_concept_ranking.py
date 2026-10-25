"""Ranking policy tests over supplied, accepted repository concept fixtures."""

from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path

import pytest

from app.workflow.concept_ranking import (
    DIMENSIONS,
    ConceptInput,
    normalize,
    project_report,
    rank_concepts,
    validate_concept,
)
from app.workflow.short_form_engine import assess

ROOT = Path(__file__).parents[2]
FIXTURE = json.loads((Path(__file__).parent / "fixtures/concept_ranking_batches.json").read_text())
CANDIDATES = FIXTURE["candidates"]


def batch(name):
    return [deepcopy(CANDIDATES[key]) for key in FIXTURE["batches"][name]]


def test_obvious_winner_and_incomplete_records_do_not_compete():
    result = rank_concepts(batch("obvious"))
    assert result["firstRenderCandidate"] == "lid-a"
    assert [r["candidateId"] for r in result["rankedEligibleCandidates"]] == ["lid-a"]
    for row in result["revisionCandidates"]:
        assert "rank" not in row and row["rankingScore"] is None
        assert row["eligibility"] == "INELIGIBLE"
        assert row["eligibilityReasons"]
    incomplete = next(r for r in result["revisionCandidates"] if r["candidateId"] == "incomplete")
    assert "protagonistGoal" in incomplete["missingFields"]
    assert incomplete["shortFormEngine"] is None


def test_short_form_scores_are_not_replaced_and_cpq_is_not_invented():
    row = validate_concept(CANDIDATES["simple"])
    before = assess(CANDIDATES["simple"]["text"], {"shortFormEvaluation": True, "desiredDuration": 15})
    assert row["shortFormEngine"] == before
    assert row["shortFormScore"] == 100
    assert row["rankingScore"] == 97.6
    assert row["cpqPreview"]["absoluteQuality"]["aggregateScore"] is None
    assert not row["cpqPreview"]["renderAuthorized"]


def test_formula_is_named_unequal_and_exactly_reproducible():
    row = validate_concept(CANDIDATES["adhesion"])
    assert sum(weight for _, _, weight in DIMENSIONS) == 100
    assert len({weight for _, _, weight in DIMENSIONS}) > 1
    weighted = sum(d["score"] * d["weightPercent"] for d in row["rankingDimensions"]) / 100
    assert row["baseCompositeScore"] == weighted
    assert row["rankingScore"] == weighted - row["rankingPenaltyPoints"]
    assert all(d["source"].startswith("SHORT_FORM_ENGINE.") for d in row["rankingDimensions"])


def test_duplicate_penalty_changes_order_despite_equal_short_form_scores():
    result = rank_concepts(batch("duplicate_penalty"))
    simple, duplicate = result["rankedEligibleCandidates"]
    assert simple["candidateId"] == "simple" and duplicate["candidateId"] == "a-adhesion"
    assert simple["shortFormScore"] == duplicate["shortFormScore"] == 100
    assert simple["baseCompositeScore"] == duplicate["baseCompositeScore"]
    assert duplicate["duplicateRisk"] == "MODERATE"
    assert duplicate["rankingPenaltyPoints"] == 8
    assert duplicate["rankingScore"] < simple["rankingScore"]
    assert duplicate["historicalComparison"]["closestHistoricalEngine"] == "sticky-ball-01"
    assert duplicate["historicalComparison"]["similarities"] == ["opening", "ending"]
    assert duplicate["historicalComparison"]["differences"][0]["axis"] == "progression"


def test_cost_breaks_close_scores_without_rewriting_creative_value():
    result = rank_concepts(batch("cost_tie"))
    simple, heavy = result["rankedEligibleCandidates"]
    assert simple["candidateId"] == "simple"
    assert simple["rankingScore"] < heavy["rankingScore"]
    assert simple["productionEfficiency"]["score"] > heavy["productionEfficiency"]["score"]
    assert simple["rawRank"] == 2 and heavy["rawRank"] == 1
    assert simple["whyRankedHere"]["basis"] == "PRODUCTION_EFFICIENCY_TIE_BREAK"
    penalty = next(p for p in heavy["penalties"] if p["code"] == "PRODUCTION_COMPLEXITY")
    assert penalty["points"] == 0 and penalty["secondaryPoints"] == 72


def test_materially_stronger_creative_value_beats_low_production_cost():
    result = rank_concepts(batch("material_quality"))
    heavy, easy = result["rankedEligibleCandidates"]
    assert heavy["candidateId"] == "heavy"
    assert heavy["rankingScore"] - easy["rankingScore"] > 3
    assert heavy["productionEfficiency"]["score"] < easy["productionEfficiency"]["score"]
    assert heavy["whyRankedHere"]["basis"] == "QUALITY_SCORE"


def test_close_score_bands_are_anchored_and_do_not_chain_cost_preference(monkeypatch):
    # Sorting-policy simulation, using copies of an accepted supplied fixture;
    # these injected numbers are not new engine outputs or production concepts.
    template = validate_concept(CANDIDATES["simple"])
    rows = {}
    for key, score, efficiency in [("a", 100, 100), ("b", 97.5, 10), ("c", 96.5, 50)]:
        row = deepcopy(template)
        row["candidateId"] = row["normalizedConcept"]["id"] = key
        row["rankingScore"] = score
        row["productionEfficiency"]["score"] = efficiency
        rows[key] = row
    monkeypatch.setattr("app.workflow.concept_ranking.validate_concept", lambda key: deepcopy(rows[key]))
    result = rank_concepts(["c", "b", "a"])
    assert [row["candidateId"] for row in result["rankedEligibleCandidates"]] == ["a", "b", "c"]
    assert result["rankedEligibleCandidates"][2]["whyRankedHere"]["basis"] == "QUALITY_SCORE"
    assert result["tieBands"][0]["candidateIds"] == ["a", "b"]


def test_diversity_promotes_different_engines_within_small_quality_gap():
    result = rank_concepts(batch("diversity"))
    assert [r["candidateId"] for r in result["rankedEligibleCandidates"][:3]] == ["lid-a", "lid-b", "lid-c"]
    assert [r["candidateId"] for r in result["productionSlate"]] == ["lid-a", "z-garden", "growth"]
    assert result["productionSlate"][2]["rank"] == 5
    assert [a["code"] for a in result["diversityAdjustments"]] == [
        "DIVERSITY_PROMOTION",
        "DIVERSITY_PROMOTION",
    ]
    assert result["diversityAdjustments"][1]["qualityGap"] == 2.4
    assert result["firstRenderCandidate"] == "lid-a"


def test_diversity_does_not_promote_distant_weak_value_or_fill_with_duplicates():
    result = rank_concepts([CANDIDATES[key] for key in ["lid", "lid_b", "lid_c", "adhesion"]])
    assert len(result["productionSlate"]) == 1
    assert result["diversityAdjustments"][0]["code"] == "SLATE_UNDERFILLED_QUALITY_GAP"


def test_entire_output_is_identical_for_every_input_permutation():
    supplied = batch("diversity")
    expected = rank_concepts(supplied)
    for ordering in permutations(supplied):
        assert rank_concepts(list(ordering)) == expected


@pytest.mark.parametrize("name", list(FIXTURE["batches"]))
def test_ranker_is_deterministic_and_does_not_mutate_supplied_records(name):
    supplied = batch(name)
    original = deepcopy(supplied)
    assert rank_concepts(supplied) == rank_concepts(list(reversed(supplied)))
    assert supplied == original


def test_high_duplicate_is_ineligible_before_ranking():
    row = validate_concept(CANDIDATES["duplicate"])
    assert row["eligibility"] == "INELIGIBLE"
    assert row["rankingScore"] is None
    assert row["duplicateRisk"] == "HIGH"
    assert any(r["code"] == "ENGINE_DUPLICATE_RISK" for r in row["eligibilityReasons"])
    assert next(p["points"] for p in row["penalties"] if p["code"] == "DUPLICATE_ENGINE") == 25


def test_exact_historical_resubmission_is_flagged_without_changing_accepted_validator():
    source = (ROOT / "data/golden/pompom-golden-v1/prompts/upside-chair-01.md").read_text()
    row = validate_concept({"id": "historical-copy", "title": "Historical resubmission", "text": source})
    assert row["shortFormEngine"]["status"] == "PASS_WITH_WARNINGS"
    assert row["shortFormEngine"]["duplicateEngineRisk"]["status"] == "NO_MATCH_IN_LIMITED_CORPUS"
    assert row["duplicateRisk"] == "HIGH" and row["eligibility"] == "INELIGIBLE"
    assert row["shortFormEngine"] == assess(source, {"shortFormEvaluation": True, "desiredDuration": 17})


def test_no_eligible_concept_produces_no_production_or_render_recommendation():
    result = rank_concepts([CANDIDATES["busy"], CANDIDATES["incomplete"]])
    assert not result["rankedEligibleCandidates"] and not result["productionSlate"]
    assert result["firstRenderCandidate"] is None
    assert not result["renderAuthorized"] and result["conceptsGenerated"] == result["providerCalls"] == 0


def test_every_ranking_rationale_names_actual_compared_dimensions_and_penalties():
    result = rank_concepts(batch("duplicate_penalty"))
    first = result["rankedEligibleCandidates"][0]
    explanation = result["whyThisBeatsTheOthers"][0]
    assert explanation["dimensions"][0] == {
        "dimension": "instantCausalLegibility",
        "candidateScore": 100,
        "otherScore": 100,
        "difference": 0,
    }
    assert explanation["rankingPenaltyPoints"] == [0, 8]
    assert first["whyRankedHere"]["comparison"] == explanation
    assert "ranking penalties 0 vs 8" in first["whyRankedHere"]["text"]


def test_report_answers_first_production_choice_and_excluded_reasons():
    result = rank_concepts(batch("obvious"))
    original = deepcopy(result)
    report = "\n".join(project_report(result))
    assert "Produce first: lid-a" in report
    assert "hook 100; progress 100; payoff 100" in report
    assert "INELIGIBLE incomplete" in report
    assert result == original


def test_labeled_plain_text_is_normalized_without_generation():
    plan = CANDIDATES["lid"]["text"]
    candidate = (
        "ID: labeled\nTitle: Existing labeled fixture\nDuration: 15 seconds\nEscalation Plan:\n" + plan
    )
    result = validate_concept(candidate)
    normalized = result["normalizedConcept"]
    assert result["eligibility"] == "ELIGIBLE"
    assert normalized["protagonist"] == "Mimi"
    assert normalized["protagonistGoal"] == "close the lid"
    assert normalized["frameZeroDescription"].startswith("Mimi tries")
    assert normalized["evaluationText"] == plan
    assert normalized["normalizationEvidence"]["protagonistGoal"] == "EXACT_SOURCE_EXCERPT"


def test_unlabeled_unknown_fields_stay_missing_and_identity_is_stable():
    first = normalize("Someone looks at something. Nothing else is supplied.")
    assert first["id"] == normalize("Someone looks at something. Nothing else is supplied.")["id"]
    assert first["protagonistGoal"] is first["frameZeroDescription"] is first["escalationPlan"] is None
    assert validate_concept("Someone looks at something.")["eligibility"] == "INELIGIBLE"


def test_structured_full_and_middle_beats_reuse_same_business_logic():
    from app.workflow.short_form_engine import _timeline

    source = CANDIDATES["lid"]["text"]
    beats = _timeline(source)
    normalized = normalize(CANDIDATES["lid"])
    structured = {
        key: normalized[key]
        for key in (
            "title",
            "protagonist",
            "protagonistGoal",
            "objectOrPrimaryInteraction",
            "impossibleRuleOrCoreContradiction",
            "frameZeroDescription",
            "finalPayoff",
            "intendedDurationSeconds",
        )
    }
    structured["id"] = "structured"
    structured["escalationPlan"] = [
        {"startSeconds": b["start"], "endSeconds": b["end"], "description": b["quote"]} for b in beats
    ]
    full = validate_concept(structured)
    structured["escalationPlan"] = structured["escalationPlan"][1:-1]
    middle = validate_concept(structured)
    assert full == middle or full["shortFormEngine"] == middle["shortFormEngine"]
    assert full["rankingScore"] == middle["rankingScore"] == 100
    assert middle["eligibility"] == "ELIGIBLE"


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("frameZeroDescription", "A normal pretty room.", "PLAN_FIELD_CONFLICT"),
        ("finalPayoff", "Everyone smiles.", "PLAN_FIELD_CONFLICT"),
        ("protagonistGoal", "have fun", "DECLARED_GOAL_UNSUPPORTED"),
        ("protagonistGoal", "eat a snack", "DECLARED_GOAL_CONFLICT"),
        ("protagonist", "Moro", "DECLARED_PROTAGONIST_CONFLICT"),
        ("impossibleRuleOrCoreContradiction", "The chair flips upside down.", "DECLARED_RULE_CONFLICT"),
        ("optionalDialogue", "A long explanation not placed in the plan.", "UNTIMED_DIALOGUE"),
    ],
)
def test_metadata_cannot_supply_evidence_for_a_conflicting_plan(field, value, code):
    row = validate_concept({**CANDIDATES["lid"], field: value})
    assert row["eligibility"] == "INELIGIBLE"
    assert any(r["code"] == code for r in row["eligibilityReasons"])


def test_do_not_fabricate_timing_for_an_untimed_concept():
    row = validate_concept(
        {
            "title": "Untimed source",
            "text": "Mimi tries to close the lid but it pops open. She pushes harder. It pops open again.",
            "intendedDurationSeconds": 15,
        }
    )
    assert row["eligibility"] == "INELIGIBLE"
    assert not row["shortFormEngine"]["timingVerifiedFromPlan"]
    assert any(r["code"] == "TIMING_UNVERIFIED" for r in row["eligibilityReasons"])


def test_explicit_protagonist_can_be_referred_to_by_pronoun_in_the_opening():
    supplied = {
        **CANDIDATES["lid"],
        "protagonist": "Mimi",
        "text": CANDIDATES["lid"]["text"].replace("Mimi tries", "She tries", 1),
    }
    assert validate_concept(supplied)["eligibility"] == "ELIGIBLE"


@pytest.mark.parametrize(
    "name,penalty,points",
    [
        ("busy", "HIGH_ACTIVITY_LOW_PROGRESS", 12),
        ("busy", "PASSIVE_PREMISE", 8),
        ("busy", "WEAK_PAYOFF", 15),
        ("unclear", "LATE_HOOK", 15),
        ("overload", "TEMPORAL_OVERLOAD", 6),
    ],
)
def test_named_penalty_values_are_source_triggered(name, penalty, points):
    row = validate_concept(CANDIDATES[name])
    assert next(p["points"] for p in row["penalties"] if p["code"] == penalty) == points


@pytest.mark.parametrize(
    "source,code,points",
    [("unrelated_rules", "RANDOM_ESCALATION", 20), ("boogeyman_compressed", "DIALOGUE_DEPENDENT", 20)],
)
def test_randomness_and_dialogue_penalties_use_existing_findings(source, code, points):
    cases = json.loads((Path(__file__).parent / "fixtures/short_form_cases.json").read_text())["cases"]
    row = validate_concept({"id": source, "title": source, "text": cases[source]})
    assert next(p["points"] for p in row["penalties"] if p["code"] == code) == points
    assert row["rankingScore"] is None


@pytest.mark.parametrize("values", [[], [CANDIDATES["simple"]] * 31, [CANDIDATES["simple"]] * 2])
def test_invalid_batches_are_rejected(values):
    with pytest.raises(ValueError):
        rank_concepts(values)


def test_supplied_scores_and_unbounded_or_nonfinite_inputs_are_rejected():
    for extra in (
        {"rankingScore": 100},
        {"intendedDurationSeconds": float("nan")},
        {"intendedDurationSeconds": float("inf")},
        {"text": "a" * 50001},
    ):
        with pytest.raises(ValueError):
            ConceptInput.model_validate({**CANDIDATES["simple"], **extra})


def test_frozen_accepted_implementations_fixtures_and_all_historical_artifacts_keep_hashes():
    workspace = Path(__file__).parents[3]
    before = json.loads((ROOT / "docs/concept-ranking-v1/immutable-before.json").read_text())
    assert len(before) == 68
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(workspace, before)
