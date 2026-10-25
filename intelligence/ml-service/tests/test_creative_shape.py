import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.workflow import creative_shape as shape
from app.workflow import shape_generation as gen

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def cases():
    run = json.loads((ROOT / "docs/premise-naturalness-v1/experiment-seed-42-count-20.json").read_text())
    return [r["candidate"] for r in run["candidates"]]


def test_within_concept_diversity_does_not_imply_cross_concept_originality(cases):
    a = cases[4]
    b = deepcopy(a)
    b.update(
        candidateId="another",
        primaryObject="drawer",
        protagonist="Someone Else",
        engineFamily="DIFFERENT_ENGINE",
        title="Renamed",
    )
    assert a["beatGrammar"]["strategyDiversityScore"] == 100
    assert shape.annotate(a) == shape.annotate(b)
    result = shape.review_batch([a, b])
    assert result[0]["closestBatchShape"]["distance"] == 0
    assert result[0]["templateShapeRisk"]["risk"] == "HIGH"
    assert shape.batch_metrics([a, b])["strategySequenceWarning"] == "STRATEGY_SEQUENCE_CONCENTRATION"


def test_false_success_and_reset_are_measurable(cases):
    a = cases[4]
    metrics = shape.batch_metrics([a, deepcopy(a)])
    assert metrics["falseSuccessBeat4Rate"] == 1
    assert metrics["temporaryStopTriggerRate"] == 1
    assert metrics["resetPayoffRate"] == 1
    assert metrics["payoffFamilyDistribution"] == {"FALSE_SUCCESS_COLLAPSE": 2}


def test_payoff_and_final_relationship_diversity(cases):
    result = shape.batch_metrics([cases[4], cases[2], cases[19]])
    assert len(result["payoffFamilyDistribution"]) == 3
    assert len(result["finalRelationshipDistribution"]) == 3
    assert shape.annotate(cases[2])["payoffFamily"] == "CONTACT_ENTANGLEMENT"
    assert "PROPERTY_TRANSFER" not in result["payoffFamilyDistribution"]


@pytest.mark.parametrize("i,j", [(0, 1), (4, 19), (2, 6), (11, 14)])
def test_distance_symmetric_and_bounded(cases, i, j):
    assert shape.distance(cases[i], cases[j]) == shape.distance(cases[j], cases[i])
    assert 0 <= shape.distance(cases[i], cases[j])["distance"] <= 1


def test_order_and_duration_do_not_change_pairwise_shape(cases):
    a, b = deepcopy(cases[4]), deepcopy(cases[1])
    expected = shape.distance(a, b)
    for beat in a["beats"]:
        beat["startSeconds"] *= 1.2
        beat["endSeconds"] *= 1.2
    assert shape.distance(a, b) == expected
    assert shape.batch_metrics([a, b]) == shape.batch_metrics([b, a])


def test_chair_inversion_territory_from_structure_not_title_or_engine(cases):
    chair = deepcopy(cases[9])
    chair["title"] = "Entirely unrelated label"
    chair["engineFamily"] = "NOT_HISTORICAL_ENGINE"
    r = shape.territory(chair)
    assert r["historicalCreativeTerritoryRisk"] == "HIGH"
    assert r["closestHistoricalCreativeTerritory"]["referenceId"] == "upside-chair-01"
    assert {"objectCategory", "goal", "dominantTransformation", "silhouetteTopology"} <= set(
        r["closestHistoricalCreativeTerritory"]["matchingAxes"]
    )
    assert r["canonicalHistoricalMetricsChanged"] is False
    chair.update(primaryObject="spoon", everydayGoal="eat soup")
    assert shape.territory(chair)["historicalCreativeTerritoryRisk"] != "HIGH"


def test_two_reset_engines_can_have_distinct_full_shapes(cases):
    shoe, drawer = cases[4], cases[1]
    assert shoe["engineFamily"] == drawer["engineFamily"] == "RESET_TO_START"
    assert shape.distance(shoe, drawer)["distance"] >= 0.22


def test_goal_and_control_arcs_are_supported_by_plan(cases):
    f = shape.annotate(cases[4])["dimensions"]
    assert f["goalStateSequence"] == ["BLOCKED", "PARTIAL_PROGRESS", "FARTHER", "APPARENT_SUCCESS", "RESET"]
    assert f["controlStateSequence"] == [
        "OBJECT_RESISTS",
        "OBJECT_RESISTS",
        "OBJECT_DOMINATES",
        "FALSE_CONTROL",
        "OBJECT_RESISTS",
    ]
    assert f["falseSuccessPosition"] == [4]
    assert shape.annotate(cases[1])["dimensions"]["falseSuccessPosition"] == []


def test_lower_raw_rank_promoted_for_shape_without_score_mutation(cases):
    a, b, c = deepcopy(cases[4]), deepcopy(cases[4]), deepcopy(cases[1])
    a["candidateId"] = "a-first"
    b["candidateId"] = "b-copy"
    c["candidateId"] = "z-distinct"
    a["premiseNaturalness"]["instantCausalLegibility"] = 100
    candidates = shape.review_batch([a, b, c])
    rows = [
        dict(
            candidateId=x["candidateId"],
            rank=i + 1,
            rankingScore=97 - i * 0.5,
            eligibility="ELIGIBLE",
            shortFormScore=99,
            shortFormEngine={"payoffScore": 100},
        )
        for i, x in enumerate(candidates)
    ]
    before = deepcopy(rows)
    result = gen.production_selection(rows, candidates)
    assert [s["candidateId"] for s in result["productionSlate"]] == ["a-first", "z-distinct"]
    assert rows == before and result["policy"]["canonicalScoreMutation"] is False


def test_unique_low_quality_cannot_displace_quality(cases):
    a, b = deepcopy(cases[4]), deepcopy(cases[2])
    a["candidateId"] = "strong"
    b["candidateId"] = "novel-but-weak"
    candidates = shape.review_batch([a, b])
    rows = [
        dict(
            candidateId="strong",
            rank=1,
            rankingScore=97,
            shortFormScore=99,
            eligibility="ELIGIBLE",
            shortFormEngine={"payoffScore": 100},
        ),
        dict(
            candidateId="novel-but-weak",
            rank=2,
            rankingScore=30,
            shortFormScore=31,
            eligibility="ELIGIBLE",
            shortFormEngine={"payoffScore": 100},
        ),
    ]
    assert [s["candidateId"] for s in gen.production_selection(rows, candidates)["productionSlate"]] == [
        "strong"
    ]


def test_id_is_final_fallback_only(cases):
    a, b = deepcopy(cases[4]), deepcopy(cases[4])
    a["candidateId"] = "a-low"
    b["candidateId"] = "z-high"
    candidates = shape.review_batch([a, b])
    rows = [
        dict(
            candidateId=c["candidateId"],
            rank=i + 1,
            rankingScore=97,
            shortFormScore=99,
            eligibility="ELIGIBLE",
            shortFormEngine={"payoffScore": 100},
        )
        for i, c in enumerate(candidates)
    ]
    assert gen.production_selection(rows, candidates)["firstRenderCandidate"] == "a-low"
    candidates[1]["premiseNaturalness"]["instantCausalLegibility"] = 100
    assert gen.production_selection(rows, candidates)["firstRenderCandidate"] == "z-high"


def test_historical_annotations_have_frozen_source_hashes():
    refs = json.loads((ROOT / "ml-service/app/workflow/creative_territories_v1.json").read_text())[
        "references"
    ]
    for ref in refs:
        assert (
            hashlib.sha256((ROOT.parent / ref["sourcePath"]).read_bytes()).hexdigest() == ref["sourceSha256"]
        )


def test_no_mutation_or_engine_labels_in_fingerprint(cases):
    before = deepcopy(cases)
    shape.review_batch(cases)
    assert cases == before
    assert "engineFamily" not in shape.annotate(cases[4])["dimensions"]


def test_payoff_taxonomy_documents_both_supported_and_unobserved_families():
    assert {"ABSURD_SUCCESS", "HIDDEN_CAUSE_REVEAL", "PROPERTY_TRANSFER", "CONTROL_REVERSAL"} <= set(
        shape.PAYOFF_FAMILIES
    )
    assert sum(shape.WEIGHTS.values()) == pytest.approx(1)


def test_silhouette_and_object_goal_experience_precede_id(cases):
    a, b, c = deepcopy(cases[4]), deepcopy(cases[1]), deepcopy(cases[1])
    a["candidateId"] = "a-first"
    b["candidateId"] = "z-drawer"
    c.update(candidateId="b-alias", primaryObject="shoe", everydayGoal="put the shoe on")
    c["visualFingerprint"] = deepcopy(a["visualFingerprint"])
    a["premiseNaturalness"]["instantCausalLegibility"] = 100
    candidates = shape.review_batch([a, b, c])
    rows = [
        dict(
            candidateId=x["candidateId"],
            rank=i + 1,
            rankingScore=97,
            shortFormScore=99,
            eligibility="ELIGIBLE",
            shortFormEngine={"payoffScore": 100},
        )
        for i, x in enumerate(candidates)
    ]
    result = gen.production_selection(rows, candidates)
    assert [s["candidateId"] for s in result["productionSlate"]] == ["a-first", "z-drawer"]
    assert result["tieDecisions"][1]["signals"]["objectGoalExperienceNovelty"] == 1
