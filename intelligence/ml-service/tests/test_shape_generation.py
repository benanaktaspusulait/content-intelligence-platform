import importlib.util
import json
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workflow import concept_ranking as ranking
from app.workflow import premise_generation as prior
from app.workflow import shape_generation as gen
from app.workflow.shape_benchmark import compare_runs
from app.workflow.short_concept_generation import ranking_input

ROOT = Path(__file__).parents[2]
CONFIG = dict(
    generatorVersion="v2",
    beatGrammarVersion="v2",
    premiseNaturalnessGateVersion="v1",
    creativeShapeVersion="v1",
    seed=42,
    count=20,
)


@lru_cache
def run():
    return gen.generate_and_rank(CONFIG)


@pytest.mark.parametrize(
    "config",
    [
        dict(generatorVersion="v1"),
        dict(generatorVersion="v2"),
        dict(generatorVersion="v2", beatGrammarVersion="v2"),
        dict(generatorVersion="v2", beatGrammarVersion="v2", premiseNaturalnessGateVersion="v1"),
    ],
)
def test_disabled_dispatch_exactly_preserves_each_prior_stack(config):
    assert json.dumps(gen.generate_and_rank(config), sort_keys=True) == json.dumps(
        prior.generate_and_rank(config), sort_keys=True
    )


def test_seed_golden_and_repeat():
    r = run()
    assert r == gen.generate_and_rank(CONFIG)
    golden = json.loads((Path(__file__).parent / "fixtures/creative_shape_v1_golden.json").read_text())
    assert [c["candidateId"] for c in r["candidates"]] == golden["candidateIds"]
    assert r["generationSummary"] == golden["generationSummary"]
    assert [c["candidateId"] for c in r["top3ProductionCandidates"]] == golden["productionSlate"]


def test_capacity_quality_shape_and_historical_constraints():
    r = run()
    assert 0 < len(r["candidates"]) < 20
    assert r["generationEvidence"]["capacityStatus"] == "DIVERSITY_CAPACITY_REACHED"
    assert (
        len(r["candidates"]) + len(r["suppressedCandidates"]) == r["generationEvidence"]["internalPoolSize"]
    )
    for c in r["candidates"]:
        assert c["validation"]["shortFormScore"] >= 85 and c["disposition"] == "ELIGIBLE"
        assert c["historicalCreativeTerritory"]["historicalCreativeTerritoryRisk"] != "HIGH"
        assert c["closestBatchShape"]["distance"] >= 0.22
    assert any(
        "HIGH_HISTORICAL_CREATIVE_TERRITORY" in c["suppressionReasons"] for c in r["suppressedCandidates"]
    )
    assert any("STORY_SHAPE_DISTANCE_CAPACITY" in c["suppressionReasons"] for c in r["suppressedCandidates"])


def test_reuses_canonical_ranker_exactly_and_returns_frontier():
    r = run()
    assert r["rankingResult"] == ranking.rank_concepts(
        [ranking_input(c["candidate"]) for c in r["candidates"]]
    )
    assert r["qualityDiversityFrontier"]["nondominatedCandidateIds"]
    assert r["poolValidationEvidence"]["finalRankingScoresUsedForRewrites"] is False
    assert r["providerCalls"] == 0 and not r["renderAuthorized"]


def test_full_human_review_reports():
    for report in run()["humanReadableConcepts"]:
        for label in [
            "ONE-LINE PREMISE:",
            "FRAME ZERO:",
            "BEAT 1:",
            "BEAT 5 / PAYOFF:",
            "GOAL-STATE ARC:",
            "CONTROL-STATE ARC:",
            "CLOSEST BATCH SHAPE:",
            "CLOSEST HISTORICAL CREATIVE TERRITORY:",
            "TEMPLATE SHAPE RISK:",
            "rawRank:",
            "productionSlateRank:",
        ]:
            assert label in report


@pytest.mark.parametrize(
    "config",
    [
        {"creativeShapeVersion": "v1"},
        {"generatorVersion": "v2", "creativeShapeVersion": "v1"},
        {**CONFIG, "premiseNaturalnessGateVersion": None},
        {**CONFIG, "generatorVersion": "v1"},
        {**CONFIG, "creativeShapeVersion": "v2"},
        {**CONFIG, "rank": False},
        {**CONFIG, "provider": "openai"},
    ],
)
def test_invalid_api_config(config):
    assert TestClient(app).post("/api/v1/workflow/concepts/generate", json=config).status_code == 422


def test_api_cli_parity(monkeypatch, capsys):
    response = TestClient(app).post("/api/v1/workflow/concepts/generate", json=CONFIG)
    assert response.status_code == 200 and response.json() == run()
    script = ROOT / "scripts/generate-short-concepts.py"
    spec = importlib.util.spec_from_file_location("shape_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(script),
            "--generator-version",
            "v2",
            "--beat-grammar-version",
            "v2",
            "--premise-naturalness-gate-version",
            "v1",
            "--creative-shape-version",
            "v1",
            "--rank",
        ],
    )
    assert module.main() == 0
    cli = capsys.readouterr().out
    assert cli == json.dumps(run(), indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def test_benchmark_annotations_are_read_only():
    paths = [
        "short-concept-generation-v2/example-run.json",
        "beat-grammar-v2/experiment-seed-42-count-20.json",
        "premise-naturalness-v1/experiment-seed-42-count-20.json",
    ]
    runs = {
        k: json.loads((ROOT / "docs" / p).read_text()) for k, p in zip(["A", "B", "C"], paths, strict=True)
    }
    before = deepcopy(runs)
    runs["D"] = run()
    comparison = compare_runs(runs)
    assert {k: runs[k] for k in before} == before
    assert comparison["stages"]["C"]["averageShortFormScore"] == 70.15
    assert comparison["stages"]["D"]["finalCandidateCount"] < 20


def test_protected_sources_and_all_prior_experiments_unchanged():
    manifest = json.loads((ROOT / "docs/creative-shape-v1/immutable-before.json").read_text())
    assert len(manifest) >= 184
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(ROOT.parent, manifest)
