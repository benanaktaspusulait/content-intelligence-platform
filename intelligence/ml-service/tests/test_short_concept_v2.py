from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from app.workflow import short_concept_generation as v1
from app.workflow import short_concept_generation_v2 as v2
from app.workflow import concept_ranking as ranking
from app.workflow.concept_fingerprint import compare, fingerprint, digest
from app.workflow.creative_distance import (
    creative_distance,
    distributions,
    novelty,
    pairwise_summary,
    silhouette_similarity,
)
from app.workflow.concept_production_selection import materially_distinct

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def run():
    return v2.generate_and_rank({"generatorVersion": "v2", "count": 20, "seed": 42})


def test_v1_direct_and_dispatch_output_remain_exactly_equal():
    expected = v1.generate_and_rank({"count": 20, "seed": 42})
    assert v2.generate_and_rank({"generatorVersion": "v1"}) == expected
    assert v2.generate_and_rank({}) == expected
    golden = json.loads((ROOT / "ml-service/tests/fixtures/short_concept_generation_golden.json").read_text())
    assert expected["generationSummary"] == golden["summary"]


def test_v2_same_seed_complete_result_is_byte_stable(run):
    assert digest(run) == digest(v2.generate_and_rank({"generatorVersion": "v2"}))


def test_different_seeds_change_compositions_not_just_characters(run):
    other = v2.generate_and_rank({"generatorVersion": "v2", "seed": 43, "rank": False})
    assert {r["candidateId"] for r in run["candidates"]} != {r["candidateId"] for r in other["candidates"]}


def test_new_golden_is_versioned_and_all_twenty_candidates_are_retained(run):
    golden = json.loads((ROOT / "ml-service/tests/fixtures/short_concept_v2_golden.json").read_text())
    assert len(run["candidates"]) == 20
    assert digest([r["candidate"] for r in run["candidates"]]) == golden["candidateHash"]
    assert run["generationSummary"] == golden["generationSummary"]
    assert run["firstRenderCandidate"] == golden["firstRenderCandidate"]


def test_grammar_contains_primitives_not_complete_stories():
    g = v2.load_grammar()
    assert len(g["goals"]) >= 15 and len(g["engines"]) >= 8
    assert len(g["objects"]) >= 20
    for e in g["engines"]:
        assert {
            "validTriggerTypes",
            "validInteractionTypes",
            "stateTransition",
            "allowedEscalations",
            "compatiblePayoffFamilies",
            "productionRiskHints",
        } <= e.keys()
        assert not {"beats", "title", "frameZeroDescription", "finalPayoff"} & e.keys()
    assert len({e["stateTransition"] for e in g["engines"]}) == len(g["engines"])


def test_compatibility_and_sanity_are_enforced_for_every_selected_plan(run):
    g = v2.load_grammar()
    for r in run["candidates"]:
        c = r["candidate"]
        p = c["composition"]
        assert not v2.sanity_errors(p, g)
        assert c["everydayGoal"] in c["frameZeroDescription"]
        assert c["primaryObject"] in c["frameZeroDescription"]
        assert c["impossibleRule"] and c["goalRuleRelationship"]
        assert len(c["beats"]) == 5 and len({b["description"] for b in c["beats"]}) == 5
        assert c["dialogueRequirement"] == "NONE"
        assert c["provenance"]["characterAssignedAfterEngine"]
        assert all(e["sourceRule"] == c["impossibleRule"] for e in c["escalationCurve"])
        assert [e["transitionApplication"] for e in c["escalationCurve"]] == [1, 2, 3, 3, 4]
        assert c["finalPayoff"] == c["beats"][-1]["description"]
        assert g["triggers"][p["trigger"]]["visible"]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("objectId", "chair", "GOAL_OBJECT_MISMATCH"),
        ("trigger", "INVISIBLE_TIMER", "TRIGGER_NOT_VISIBLE"),
        ("payoffTopology", "MAGIC_EXPLOSION", "UNEXPLAINED_PAYOFF_RULE"),
        ("stateTransition", "UNRELATED_MAGIC", "FINAL_STATE_VIOLATES_ENGINE"),
        ("escalationTopology", "RANDOM_BIRD", "ENGINE_ESCALATION_MISMATCH"),
        ("environment", "space station", "ENVIRONMENT_GOAL_MISMATCH"),
        ("goalId", "unknown", "UNKNOWN_PRIMITIVE"),
    ],
)
def test_invalid_compositions_have_explicit_reasons(run, field, value, reason):
    plan = deepcopy(
        next(
            r["candidate"]["composition"]
            for r in run["candidates"]
            if r["candidate"]["primaryObject"] == "brush"
        )
    )
    plan[field] = value
    assert reason in v2.sanity_errors(plan, v2.load_grammar())
    with pytest.raises(ValueError):
        v2.compose(plan, v2.load_grammar(), [{"id": "a", "name": "Kiko"}], 42, 15)


def test_engine_and_escalation_are_independent_and_environment_follows_goal(run):
    pool = run["candidates"]
    engines = {}
    escalations = {}
    for r in pool:
        p = r["candidate"]["composition"]
        engines.setdefault(p["engineFamily"], set()).add(p["escalationTopology"])
        escalations.setdefault(p["escalationTopology"], set()).add(p["engineFamily"])
    assert any(len(v) > 1 for v in engines.values()) and any(len(v) > 1 for v in escalations.values())
    assert len(run["environmentDistribution"]) >= 6


def test_pool_and_suppression_accounting_and_failure_preservation(run):
    e = run["generationEvidence"]
    assert e["internalPoolSize"] == 240 and e["validCompositionCount"] > 240
    assert e["internalPoolSize"] == sum(
        e[k]
        for k in [
            "dedupeCount",
            "silhouetteSuppressionCount",
            "diversitySuppressionCount",
            "finalCandidateCount",
        ]
    )
    assert e["sanityRejectionCount"] == len(run["generationRejections"])
    assert all(r["failureReasons"] for r in run["suppressedCandidates"])
    assert all(r["failureReasons"] for r in run["candidates"] if r["disposition"] != "ELIGIBLE")


def test_catalog_and_cast_order_cannot_change_search_result():
    config = v2.GenerationRequest(generatorVersion="v2", rank=False)
    cast, _ = v1.resolve_cast(config)
    g = v2.load_grammar()
    expected = v2.search(config, cast, g)
    for key in ["goals", "objects", "engines"]:
        g[key].reverse()
    # Resolve_cast canonicalizes externally supplied cast snapshots too.
    reverse_config = v2.GenerationRequest(
        generatorVersion="v2", rank=False, canonicalCast=list(reversed(cast))
    )
    sorted_cast, _ = v1.resolve_cast(reverse_config)
    assert expected == v2.search(reverse_config, sorted_cast, g)


def test_object_swapped_growth_is_engine_close_and_shrink_strategy_is_distinct():
    cases = json.loads((ROOT / "ml-service/tests/fixtures/concept_fingerprint_cases.json").read_text())
    a, b, c = (cases[k] for k in ["growth_spoon", "growth_brush", "shrinking_strategy"])
    assert compare(fingerprint(a), fingerprint(b))["nearDuplicate"]
    assert creative_distance(a, b)["engineSimilarity"] == 1
    assert creative_distance(a, c)["creativeDistance"] > creative_distance(a, b)["creativeDistance"]


def test_distance_symmetry_and_order_independent_pairwise_results(run):
    candidates = [r["candidate"] for r in run["candidates"]]
    for a, b in zip(candidates, candidates[1:]):
        assert creative_distance(a, b) == creative_distance(b, a)
    assert pairwise_summary(candidates) == pairwise_summary(list(reversed(candidates)))
    assert all(novelty(c, candidates) == novelty(c, list(reversed(candidates))) for c in candidates)


def test_silhouette_detects_horizontal_stretch_across_different_engines(run):
    a = deepcopy(run["candidates"][0]["candidate"])
    b = deepcopy(a)
    b["candidateId"] = "another"
    b["title"] = "Different title"
    b["composition"]["engineFamily"] = "UNRELATED_ENGINE"
    assert silhouette_similarity(a, b)["similarity"] == 1
    assert creative_distance(a, b)["engineSimilarity"] < 1
    assert not materially_distinct(a, b)


def test_unknown_visual_axes_do_not_claim_pixel_similarity():
    assert silhouette_similarity({}, {}) == {
        "similarity": 0,
        "supportedAxes": 0,
        "evidenceKind": "PLANNED_STAGING_METADATA_NOT_PIXELS",
    }


def test_concentration_warns_without_banning_a_category(run):
    c = run["candidates"][0]["candidate"]
    summary = distributions([c] * 10)
    assert any(
        r["dimension"] == "objectCategory" and r["share"] == 1 for r in summary["concentrationWarnings"]
    )
    assert any(r["dimension"] == "character" for r in summary["concentrationWarnings"])
    assert not run["concentrationWarnings"]
    assert run["objectCategoryDistribution"]["FURNITURE"] > 0


def test_excessive_constrained_request_returns_fewer_without_cosmetic_repeats():
    g = v2.load_grammar()
    excluded = [o["name"] for o in g["objects"] if o["name"] != "chair"]
    r = v2.generate_and_rank(
        {
            "generatorVersion": "v2",
            "count": 100,
            "excludeObjects": excluded,
            "excludeEngineFamilies": [e["id"] for e in g["engines"] if e["id"] != "REVERSAL"],
            "rank": False,
        }
    )
    assert 0 < len(r["candidates"]) < 100
    assert r["generationEvidence"]["capacityStatus"] == "DIVERSITY_CAPACITY_REACHED"
    assert len({c["candidateId"] for c in r["candidates"]}) == len(r["candidates"])


def test_existing_ranker_and_short_engine_reused_without_score_mutation(run):
    with (
        patch.object(ranking, "rank_concepts", wraps=ranking.rank_concepts) as rank,
        patch.object(ranking.short, "assess", wraps=ranking.short.assess) as assess,
    ):
        actual = v2.generate_and_rank({"generatorVersion": "v2"})
    assert rank.call_count == 1 and assess.call_count == len(actual["candidates"])
    direct = ranking.rank_concepts([v1.ranking_input(r["candidate"]) for r in run["candidates"]])
    assert direct == run["rankingResult"]
    for s in run["top3ProductionCandidates"]:
        raw = next(r for r in direct["rankedEligibleCandidates"] if r["candidateId"] == s["candidateId"])
        assert s["rankingScore"] == raw["rankingScore"] and s["rawRank"] == raw["rank"]


def test_top3_material_distance_and_production_readable_output(run):
    from itertools import combinations

    slate = run["top3ProductionCandidates"]
    assert len(slate) == 3
    for a, b in combinations(slate, 2):
        assert materially_distinct(a["candidate"], b["candidate"])
    assert run["firstRenderCandidate"] == slate[0]["candidateId"]
    for text in run["humanReadableTop3"]:
        for label in [
            "FRAME ZERO:",
            "GOAL:",
            "IMPOSSIBLE RULE:",
            "BEAT 1:",
            "BEAT 5 / PAYOFF:",
            "WHY IT MAY WORK:",
            "MAIN RISK:",
            "CLOSEST HISTORICAL ENGINE:",
        ]:
            assert label in text


def test_historical_unknown_axes_and_unverified_winners_remain_unknown(run):
    for r in run["candidates"]:
        h = r["noveltyVector"]["historicalConcepts"]
        assert h["visualSilhouetteSimilarity"] is None
        assert h["noveltyVector"]["objectNovelty"] is None
        assert all(v is None for v in r["noveltyVector"]["historicalWinners"]["noveltyVector"].values())
    assert run["generatorMetrics"]["historicalSilhouetteSimilarityRate"] is None


def test_no_automatic_self_optimization_and_no_external_provider(run):
    with patch("app.llm.provider.get_provider", side_effect=AssertionError("No providers")):
        again = v2.generate_and_rank({"generatorVersion": "v2"})
    assert (
        again == run
        and run["providerCalls"] == 0
        and not run["renderAuthorized"]
        and not run["selfOptimizationEnabled"]
    )


def test_generation_only_has_no_quality_or_render_side_effects():
    with patch.object(ranking, "rank_concepts", side_effect=AssertionError("Generation only")):
        result = v2.generate_and_rank({"generatorVersion": "v2", "rank": False})
    assert result["rankingResult"] is None and result["firstRenderCandidate"] is None
    assert all(r["disposition"] == "NOT_EVALUATED" for r in result["candidates"])


def test_protected_sources_and_v1_evidence_unchanged():

    repository = ROOT.parent
    before = json.loads((ROOT / "docs/short-concept-generation-v2/immutable-before.json").read_text())
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(repository, before)


def test_distance_has_zero_self_distance_and_discloses_missing_axes(run):
    c = run["candidates"][0]["candidate"]
    assert creative_distance(c, c)["creativeDistance"] == 0
    assert creative_distance(c, c)["supportedWeight"] == 1
    sparse = {"candidateId": "sparse", "engineFamily": "ADHESION"}
    assert creative_distance(sparse, sparse)["creativeDistance"] == 0
    assert creative_distance(sparse, sparse)["supportedWeight"] < 1


def test_benchmark_preserves_inputs_and_reports_honest_different_denominators(run):
    from app.workflow.short_concept_benchmark import benchmark

    report = benchmark(42, 20)
    assert report["v1"]["outputCount"] == report["v2"]["outputCount"] == 20
    assert report["v1"]["eligibleCount"] == 8
    assert report["v2"]["eligibleCount"] == run["generationSummary"]["eligibleCount"]
    assert report["v1"]["outputStructuralDuplicateRate"] == report["v2"]["outputStructuralDuplicateRate"] == 0
    assert report["v2"]["internalPoolDuplicateRate"] > 0
    assert report["v1"]["internalPoolDuplicateRate"] is None
    assert report["v2"]["meanPairwiseCreativeDistance"] > 0
    assert report["limitations"]


def test_recreated_opening_and_self_created_loop_labels_do_not_fake_payoff_distance(run):
    a = deepcopy(run["candidates"][0]["candidate"])
    b = deepcopy(a)
    b["candidateId"] = "other"
    a["composition"]["payoffTopology"] = "OPENING_RECREATED"
    b["composition"]["payoffTopology"] = "SELF_CREATED_LOOP"
    assert creative_distance(a, b)["dimensionDifferences"]["payoffTopology"] == 0
    assert not materially_distinct(a, b)


def test_reversing_a_symmetric_soap_surface_is_not_a_goal_obstruction():
    grammar = v2.load_grammar()
    plan = dict(
        goalId="wash",
        objectId="soap_bar",
        engineFamily="REVERSAL",
        trigger="PRESSURE",
        escalationTopology="FALSE_PROGRESS",
        payoffTopology="ROLE_REVERSAL",
        stateTransition="INVERT_ORIENTATION",
        environment="bathroom",
    )
    assert "ENGINE_INTERACTION_MISMATCH" in v2.sanity_errors(plan, grammar)
