from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from app.workflow import beat_generation as feature
from app.workflow import beat_grammar as bg
from app.workflow import short_concept_generation_v2 as old
from app.workflow import concept_ranking as ranking
from app.workflow.short_concept_generation import ranking_input
from app.workflow.concept_fingerprint import digest


@pytest.fixture(scope="module")
def run():
    return feature.generate_and_rank(
        {"generatorVersion": "v2", "beatGrammarVersion": "v2", "seed": 42, "count": 20}
    )


def test_feature_disabled_is_exact_old_v2_and_v1():
    for version in ["v1", "v2"]:
        assert feature.generate_and_rank({"generatorVersion": version}) == old.generate_and_rank(
            {"generatorVersion": version}
        )


def test_same_seed_new_run_is_stable(run):
    assert digest(run) == digest(
        feature.generate_and_rank({"generatorVersion": "v2", "beatGrammarVersion": "v2"})
    )


def test_structured_plan_precedes_rendering_and_rules_are_stable(run):
    assert len(run["candidates"]) == 20
    for r in run["candidates"]:
        c = r["candidate"]
        assert c["provenance"]["structuredBeforeProse"]
        assert len(c["structuredBeatPlan"]) == 5
        assert len({b["impossibleRule"] for b in c["structuredBeatPlan"]}) == 1
        assert c["beatGrammar"]["uniqueStrategyCount"] >= 3
        assert c["beatGrammar"]["uniqueConsequenceCount"] >= 3
        assert not any(
            bg.compatible(b["characterStrategy"], c["composition"]) for b in c["structuredBeatPlan"]
        )
        assert c["beatGrammar"] == bg.assess(c["structuredBeatPlan"], c["composition"])


def test_batch_uses_several_shapes_and_no_default_force_under_object(run):
    e = run["beatGrammarMetrics"]
    assert len(e["progressionShapeDistribution"]) >= 4
    assert e["moveUnderObjectRate"] == e["twoHandForceRate"] == 0
    assert len({tuple(r["candidate"]["beatGrammar"]["consequenceSequence"]) for r in run["candidates"]}) > 5
    assert len({r["structuredBeatPlan"][3]["consequenceType"] for r in run["candidates"]}) >= 2


def test_shared_ranker_called_once_and_canonical_result_exact(run):
    with (
        patch.object(ranking, "rank_concepts", wraps=ranking.rank_concepts) as rank,
        patch.object(ranking.short, "assess", wraps=ranking.short.assess) as short,
    ):
        feature.generate_and_rank({"generatorVersion": "v2", "beatGrammarVersion": "v2"})
    assert rank.call_count == 1 and short.call_count == 20
    direct = ranking.rank_concepts([ranking_input(r["candidate"]) for r in run["candidates"]])
    assert direct == run["rankingResult"]
    assert all(not r["existingProgressFindingSupport"]["acceptedFindingsModified"] for r in run["candidates"])


def test_beat_tie_signals_precede_cosmetic_id_without_score_mutation(run):
    a, b = deepcopy(run["candidates"][0]["candidate"]), deepcopy(run["candidates"][0]["candidate"])
    a["candidateId"] = "a-low"
    b["candidateId"] = "z-high"
    a["beatGrammar"]["strategyDiversityScore"] = 25
    b["beatGrammar"]["strategyDiversityScore"] = 100
    fixture = json.loads((Path(__file__).parent / "fixtures/chair_concentration_v2.json").read_text())
    rows = [deepcopy(fixture["rankedRows"][0]) for _ in range(2)]
    for i, r in enumerate(rows):
        r["candidateId"] = [a, b][i]["candidateId"]
        r["rank"] = i + 1
    before = deepcopy(rows)
    selection = feature.select_production(rows, [a, b])
    assert selection["productionOrder"][0] == "z-high" and rows == before


def test_reports_contain_actual_beats_and_all_failures(run):
    assert len(run["humanReadableConcepts"]) == 20
    for text in run["humanReadableConcepts"]:
        for label in [
            "FRAME ZERO:",
            "BEAT 1:",
            "BEAT 5 / PAYOFF:",
            "Strategy:",
            "Consequence:",
            "New information:",
            "strategyDiversityScore=",
            "payoffDistance=",
            "eligibility=",
        ]:
            assert label in text
    assert all(r["failureReasons"] for r in run["candidates"] if r["disposition"] != "ELIGIBLE")


def test_legacy_diagnostics_read_saved_evidence_without_mutating_it(run):
    from app.workflow.beat_grammar_benchmark import compare_runs

    previous = json.loads(
        (Path(__file__).parents[2] / "docs/short-concept-generation-v2/example-run.json").read_text()
    )
    before = digest(previous)
    report = compare_runs(previous, run)
    assert digest(previous) == before
    assert report["oldV2"]["moveUnderObjectRate"] == 1
    assert report["newV2WithBeatGrammar"]["moveUnderObjectRate"] == 0
    assert report["limitations"]


def test_new_golden_and_old_protected_hashes(run):
    fixture = json.loads((Path(__file__).parent / "fixtures/beat_generation_v2_golden.json").read_text())
    assert digest([r["candidate"] for r in run["candidates"]]) == fixture["candidateHash"]
    root = Path(__file__).parents[3]
    manifest = json.loads((root / "intelligence/docs/beat-grammar-v2/immutable-before.json").read_text())
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(root, manifest)


def test_generation_only_does_not_call_quality_or_providers():
    with (
        patch.object(ranking, "rank_concepts", side_effect=AssertionError("No rank")),
        patch("app.llm.provider.get_provider", side_effect=AssertionError("No provider")),
    ):
        r = feature.generate_and_rank({"generatorVersion": "v2", "beatGrammarVersion": "v2", "rank": False})
    assert r["rankingResult"] is None and r["firstRenderCandidate"] is None
    assert r["providerCalls"] == 0 and not r["renderAuthorized"]


def test_top3_cannot_use_cosmetic_payoff_labels_for_identical_behavior(run):
    a = deepcopy(run["candidates"][0]["candidate"])
    b = deepcopy(a)
    b["composition"]["engineFamily"] = "DIFFERENT_ENGINE"
    b["composition"]["payoffTopology"] = "DIFFERENT_LABEL"
    assert not feature.behaviorally_distinct(a, b)
