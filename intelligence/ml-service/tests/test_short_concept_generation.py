from copy import deepcopy
import re
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.workflow import concept_ranking as ranking
from app.workflow import short_form_engine
from app.workflow.concept_fingerprint import digest
from app.workflow.short_concept_generation import (
    VERSION,
    DeterministicConceptGenerator,
    GeneratedConcept,
    GenerationRequest,
    generate_and_rank,
    resolve_cast,
    project_generation_report,
)

ROOT = Path(__file__).parents[2]
GOLDEN = json.loads((Path(__file__).parent / "fixtures/short_concept_generation_golden.json").read_text())


def test_seed_42_matches_the_new_versioned_generation_golden():
    result = generate_and_rank(GOLDEN["config"])
    assert result["generatorVersion"] == GOLDEN["generatorVersion"]
    assert {row["candidateId"]: digest(row["candidate"]) for row in result["candidates"]} == GOLDEN[
        "candidateDigests"
    ]
    assert result["generationSummary"] == GOLDEN["summary"]
    assert [row["candidateId"] for row in result["top3ProductionCandidates"]] == GOLDEN["top3"]
    assert result["firstRenderCandidate"] == GOLDEN["first"]


def test_same_seed_config_is_byte_stable_for_the_complete_run():
    first = generate_and_rank({"count": 20, "seed": 42})
    second = generate_and_rank({"count": 20, "seed": 42})
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_different_seeds_change_structural_recipe_selection_not_only_names():
    first = generate_and_rank({"count": 20, "seed": 42, "rank": False})
    second = generate_and_rank({"count": 20, "seed": 43, "rank": False})
    a = {row["structuralFingerprint"]["coreHash"] for row in first["candidates"]}
    b = {row["structuralFingerprint"]["coreHash"] for row in second["candidates"]}
    assert len(a.symmetric_difference(b)) >= 2


def test_catalog_cast_and_constraint_input_order_do_not_change_output():
    config = GenerationRequest(count=10, seed=9)
    cast, _ = resolve_cast(config)
    one = {**config.model_dump(), "canonicalCast": cast, "excludeObjects": ["shoe", "spoon"]}
    two = {**one, "canonicalCast": list(reversed(cast)), "excludeObjects": ["SPOON", "shoe", "spoon"]}
    first = generate_and_rank(one)
    assert generate_and_rank(two) == first
    catalog = deepcopy(DeterministicConceptGenerator().catalog)
    catalog["recipes"].reverse()
    assert generate_and_rank(one, DeterministicConceptGenerator(catalog)) == first


def test_character_is_assigned_after_engine_and_comes_from_repository_data():
    config = GenerationRequest(count=10)
    cast, source = resolve_cast(config)
    assert source == "REPOSITORY_CANONICAL_SEED_SNAPSHOT_NOT_LIVE_REGISTRY"
    generated = DeterministicConceptGenerator().generate(config, cast)
    known = {row["id"]: row["name"] for row in cast}
    for row in generated:
        assert known[row["protagonistCharacterId"]] == row["protagonist"]
        assert row["provenance"]["characterAssignedAfterEngine"]
        assert row["provenance"]["recipeId"]
        assert row["dialogueRequirement"] == "NONE"


def test_changing_cast_changes_identity_but_not_causal_engine_content():
    config = GenerationRequest(count=10)
    cast, _ = resolve_cast(config)
    generator = DeterministicConceptGenerator()
    first = generator.generate(config, [cast[0]])
    second = generator.generate(config, [cast[1]])
    for a, b in zip(first, second):
        assert a["provenance"]["recipeId"] == b["provenance"]["recipeId"]
        assert a["everydayGoal"] == b["everydayGoal"]
        assert a["structuralPlan"] == b["structuralPlan"]
        assert a["impossibleRule"] == b["impossibleRule"]
        assert a["protagonist"] != b["protagonist"]


def test_every_authored_engine_has_visible_goal_immediate_trouble_and_one_rule():
    generator = DeterministicConceptGenerator()
    config = GenerationRequest(count=25, rank=False)
    cast, _ = resolve_cast(config)
    for row in generator.generate(config, cast):
        GeneratedConcept.model_validate(row)
        assert row["everydayGoal"] and row["primaryObject"] and row["impossibleRule"]
        assert row["goalRuleRelationship"]
        assert row["frameZeroDescription"] == row["beats"][0]["description"]
        assert "tries to" in row["frameZeroDescription"]
        assert row["beats"][0]["startSeconds"] == 0
        assert row["beats"][-1]["endSeconds"] == 15
        assert 4 <= len(row["beats"]) <= 5
        assert len({beat["description"] for beat in row["beats"]}) == len(row["beats"])
        assert all(stage["sourceRule"] == row["impossibleRule"] for stage in row["escalationCurve"])
        assert row["finalPayoff"] == row["beats"][-1]["description"]
        assert "smiles" not in row["finalPayoff"].casefold()
        assert not any(
            word in row["finalPayoff"].casefold()
            for word in ["genie", "explosion", "bird suddenly", "new character"]
        )
        assert "viral" not in row["title"].casefold()


def test_catalog_does_not_support_random_character_object_effect_combinations():
    catalog = DeterministicConceptGenerator().catalog
    for row in catalog["recipes"]:
        assert set(part for beat in row["beats"] for part in re.findall(r"\{(.*?)\}", beat)) <= {"character"}
    bad = deepcopy(catalog)
    bad["recipes"][0]["beats"][0] = "{object} is random."
    with pytest.raises(ValueError, match="Only character"):
        DeterministicConceptGenerator(bad)
    bad = deepcopy(catalog)
    bad["recipes"][0]["beats"][1] = bad["recipes"][0]["beats"][0]
    with pytest.raises(ValueError, match="distinct authored"):
        DeterministicConceptGenerator(bad)


def test_generation_and_structural_dedup_precede_accepted_short_form_and_ranking():
    actual = ranking.rank_concepts
    actual_short = short_form_engine.assess
    with (
        patch("app.workflow.concept_ranking.rank_concepts", wraps=actual) as rank_spy,
        patch("app.workflow.short_form_engine.assess", wraps=actual_short) as short_spy,
    ):
        result = generate_and_rank({"count": 100, "seed": 42})
    assert rank_spy.call_count == 1
    assert short_spy.call_count == result["generationSummary"]["rankingAdmissionCount"] <= 30
    assert result["structuralDuplicateCount"] >= 75
    admitted = rank_spy.call_args.args[0]
    assert result["rankingResult"] == actual(admitted)
    assert result["rankedCandidates"] == result["rankingResult"]["rankedEligibleCandidates"]
    assert [row["candidateId"] for row in result["top3ProductionCandidates"]] == [
        row["candidateId"] for row in result["rankingResult"]["productionSlate"]
    ]
    assert result["firstRenderCandidate"] == result["rankingResult"]["firstRenderCandidate"]


@pytest.mark.parametrize("count", [10, 20, 30, 50, 100])
def test_supported_count_retains_every_attempt_with_an_accounted_disposition(count):
    result = generate_and_rank({"count": count, "seed": 42})
    summary = result["generationSummary"]
    assert summary["rawCandidateCount"] == len(result["candidates"]) == count
    assert count == sum(
        summary[key]
        for key in ["eligibleCount", "revisionCount", "rejectedCount", "deferredCount", "notEvaluatedCount"]
    )
    assert summary["structuralDuplicateCount"] <= summary["rejectedCount"]
    if count > 25:
        assert summary["catalogExhausted"] and summary["structuralDuplicateCount"]


def test_default_twenty_have_structurally_diverse_engines_without_equal_quotas():
    result = generate_and_rank({"count": 20, "seed": 42})
    assert len(result["engineDistribution"]) >= 10
    assert max(result["engineDistribution"].values()) <= 5
    assert result["dominantEngineWarning"] is None
    assert result["diversityScore"] > 90


def test_concentration_is_guarded_when_catalog_is_skewed():
    catalog = deepcopy(DeterministicConceptGenerator().catalog)
    growth = next(row for row in catalog["recipes"] if row["engineFamily"] == "progressive_growth")
    others = [row for row in catalog["recipes"] if row["engineFamily"] != "progressive_growth"][:5]
    variants = []
    for index in range(20):
        clone = deepcopy(growth)
        clone["id"] = f"growth-variant-{index:02d}"
        variants.append(clone)
    catalog["recipes"] = variants + others
    result = generate_and_rank(
        {"count": 20, "seed": 42, "rank": False}, DeterministicConceptGenerator(catalog)
    )
    assert result["engineDistribution"]["progressive_growth"] <= 5
    assert result["structuralDuplicateCount"] > 0


def test_constrained_single_family_warns_and_does_not_invent_other_engines():
    catalog = DeterministicConceptGenerator().catalog
    excluded = [r["engineFamily"] for r in catalog["recipes"] if r["engineFamily"] != "progressive_growth"]
    result = generate_and_rank({"count": 20, "excludeEngineFamilies": excluded})
    assert set(result["engineDistribution"]) == {"progressive_growth"}
    assert result["dominantEngineWarning"]["count"] == 20
    assert result["structuralDuplicateCount"] == 19
    assert len(result["top3ProductionCandidates"]) <= 1


def test_filters_apply_before_engine_selection_and_cast_assignment():
    cast, _ = resolve_cast(GenerationRequest())
    result = generate_and_rank(
        {
            "count": 10,
            "characterIds": [cast[1]["id"]],
            "excludeEngineFamilies": ["progressive_growth"],
            "excludeObjects": ["chair"],
            "excludeObjectCategories": ["grooming_tool"],
        }
    )
    for record in result["candidates"]:
        candidate = record["candidate"]
        assert candidate["protagonistCharacterId"] == cast[1]["id"]
        assert candidate["engineFamily"] != "progressive_growth"
        assert candidate["primaryObject"] not in {"chair", "brush"}


def test_generation_only_mode_does_not_assign_quality_or_call_ranking():
    with patch(
        "app.workflow.concept_ranking.rank_concepts", side_effect=AssertionError("No ranking requested")
    ):
        result = generate_and_rank({"count": 20, "rank": False})
    assert result["rankingResult"] is None and not result["rankedCandidates"]
    assert result["generatorMetrics"]["eligibilityYield"] is None
    assert result["generatorMetrics"]["averageShortFormScore"] is None
    assert result["generationSummary"]["notEvaluatedCount"] == 20


class LocalFixtureGenerator:
    version = VERSION

    def __init__(self, rows):
        self.rows = rows

    def generate(self, config, cast):
        return self.rows


def fixture_rows():
    config = GenerationRequest(count=10)
    cast, _ = resolve_cast(config)
    return DeterministicConceptGenerator().generate(config, cast)


def test_incomplete_and_rejected_candidates_are_preserved_with_reasons():
    rows = fixture_rows()
    rows[0] = {"candidateId": "incomplete", "title": "Incomplete local adapter result"}
    result = generate_and_rank({"count": 10}, LocalFixtureGenerator(rows))
    incomplete = next(row for row in result["candidates"] if row["candidateId"] == "incomplete")
    assert incomplete["candidate"] == rows[0]
    assert incomplete["disposition"] == "REVISION_REQUIRED"
    assert incomplete["failureReasons"][0]["code"] == "GENERATED_SCHEMA_INCOMPLETE"
    failures = [r for r in result["candidates"] if r["disposition"] in {"REVISION_REQUIRED", "REJECTED"}]
    assert failures and all(row["failureReasons"] for row in failures)


def test_provider_result_order_and_metadata_are_not_mutated_by_orchestration():
    rows = fixture_rows()
    before = deepcopy(rows)
    first = generate_and_rank({"count": 10}, LocalFixtureGenerator(rows))
    second = generate_and_rank({"count": 10}, LocalFixtureGenerator(list(reversed(rows))))
    assert first == second
    assert rows == before


def test_exact_repeated_beats_do_not_pass_the_local_provider_contract():
    rows = fixture_rows()
    rows[0]["beats"][1]["description"] = rows[0]["beats"][0]["description"]
    result = generate_and_rank({"count": 10}, LocalFixtureGenerator(rows))
    row = next(r for r in result["candidates"] if r["candidateId"] == rows[0]["candidateId"])
    assert row["disposition"] == "REVISION_REQUIRED"
    assert "Identical repeated attempts" in row["failureReasons"][0]["reason"]


def test_future_catalog_extensions_remain_data_driven_and_capacity_is_explicit():
    rows = fixture_rows()
    expanded = []
    for index in range(40):
        row = deepcopy(rows[index % len(rows)])
        row["candidateId"] = f"capacity-{index:02d}"
        row["structuralPlan"]["escalationTopology"] = f"CAPACITY_TEST_ONLY_{index}"
        expanded.append(row)
    result = generate_and_rank({"count": 40}, LocalFixtureGenerator(expanded))
    assert result["generationSummary"]["rankingAdmissionCount"] == 30
    assert result["generationSummary"]["deferredCount"] == 10
    assert result["rankingScope"] == "FIRST_30_CANONICAL_ID_ADMISSIONS_ONLY"
    assert len(result["candidates"]) == 40
    assert all(
        row["failureReasons"]
        for row in result["candidates"]
        if row["disposition"] == "DEFERRED_RANKING_CAPACITY"
    )


def test_duplicate_provider_ids_remain_visible_without_overwriting_the_ranked_candidate():
    rows = fixture_rows()
    rows[1]["candidateId"] = rows[0]["candidateId"]
    result = generate_and_rank({"count": 10}, LocalFixtureGenerator(rows))
    collisions = [row for row in result["candidates"] if row["candidateId"] == rows[0]["candidateId"]]
    assert len(collisions) == 2
    assert any(
        row["failureReasons"] and "Duplicate candidate ID" in row["failureReasons"][0]["reason"]
        for row in collisions
    )


def test_mutating_a_returned_plan_does_not_change_the_local_catalog():
    config = GenerationRequest(count=10)
    cast, _ = resolve_cast(config)
    generator = DeterministicConceptGenerator()
    first = generator.generate(config, cast)
    original = deepcopy(first)
    first[0]["productionNotes"].append("Caller mutation")
    assert generator.generate(config, cast) == original


def test_run_diagnostics_are_recomputed_from_evidence_not_new_creative_scores():
    result = generate_and_rank({"count": 20, "seed": 42})
    summary = result["generationSummary"]
    metrics = result["generatorMetrics"]
    assert metrics["eligibilityYield"] == summary["eligibleCount"] / 20
    assert metrics["duplicateRate"] == summary["structuralDuplicateCount"] / 20
    evaluated = [r["validation"] for r in result["candidates"] if r["validation"]]
    scores = [row["shortFormScore"] for row in evaluated]
    assert metrics["averageShortFormScore"] == round(sum(scores) / len(scores), 2)
    assert metrics["scoreUse"] == "GENERATOR_DIAGNOSTICS_ONLY_NOT_CANONICAL_CREATIVE_SCORES"
    assert result["selfOptimizationEnabled"] is False
    assert result["providerCalls"] == 0 and not result["renderAuthorized"]


def test_historical_novelty_guard_preserves_known_engine_and_new_execution_distinction():
    result = generate_and_rank({"count": 25})
    proven = [
        r
        for r in result["candidates"]
        if r.get("historicalNoveltyGuard", {}).get("classification") == "PROVEN_ENGINE_WITH_NEW_EXECUTION"
    ]
    assert proven
    assert all(row["historicalNoveltyGuard"]["closestHistoricalEngine"] for row in proven)


def test_first_candidate_explanation_and_text_report_use_actual_dimensions():
    result = generate_and_rank({"count": 20, "seed": 42})
    selected = next(
        r for r in result["rankedCandidates"] if r["candidateId"] == result["firstRenderCandidate"]
    )
    assert result["WHY_THIS_ONE_FIRST"]["concreteDimensions"] == selected["rankingDimensions"]
    assert result["WHY_THIS_ONE_FIRST"]["reason"] == selected["whyRankedHere"]
    before = deepcopy(result)
    report = "\n".join(project_generation_report(result))
    assert "What should we make today?" in report and result["firstRenderCandidate"] in report
    assert "closest historical engine" in report and "production" in report
    assert "Failures retained:" in report
    assert result == before


@pytest.mark.parametrize(
    "bad",
    [
        {"count": 9},
        {"count": 101},
        {"seed": -1},
        {"seed": True},
        {"duration": 60},
        {"duration": float("nan")},
        {"provider": "paid"},
        {"generatorVersion": "unversioned"},
    ],
)
def test_invalid_or_external_provider_requests_are_rejected(bad):
    with pytest.raises(ValueError):
        GenerationRequest.model_validate(bad)


def test_invalid_cast_constraints_and_exhausted_filters_are_explicit():
    with pytest.raises(ValueError, match="unregistered"):
        generate_and_rank({"characterIds": ["not-registered"]})
    with pytest.raises(ValueError, match="No configured"):
        generate_and_rank({"canonicalCast": []})
    with pytest.raises(ValueError, match="No engine recipes"):
        generate_and_rank(
            {
                "excludeEngineFamilies": [
                    r["engineFamily"] for r in DeterministicConceptGenerator().catalog["recipes"]
                ]
            }
        )


def test_no_character_descriptions_or_provider_calls_are_embedded_in_core():
    source = (ROOT / "ml-service/app/workflow/short_concept_generation.py").read_text()
    assert "get_provider(" not in source
    for member in resolve_cast(GenerationRequest())[0]:
        assert f'"{member["name"]}"' not in source


def test_accepted_sources_fixtures_history_and_projections_keep_all_hashes():
    workspace = Path(__file__).parents[3]
    manifest = json.loads((ROOT / "docs/short-concept-generation-v1/immutable-before.json").read_text())
    assert len(manifest) == 86
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(workspace, manifest)
