import importlib.util
import json
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workflow import beat_generation as old
from app.workflow import concept_ranking as ranking
from app.workflow import premise_generation as new
from app.workflow.premise_benchmark import compare_runs
from app.workflow.short_concept_generation import ranking_input

ROOT = Path(__file__).parents[1]
CONFIG = dict(
    generatorVersion="v2", beatGrammarVersion="v2", premiseNaturalnessGateVersion="v1", seed=42, count=20
)


@lru_cache
def run():
    return new.generate_and_rank(CONFIG)


@pytest.mark.parametrize(
    "config",
    [
        {"generatorVersion": "v1"},
        {"generatorVersion": "v2"},
        {"generatorVersion": "v2", "beatGrammarVersion": "v2"},
    ],
)
def test_disabled_is_exact_legacy_dispatch(config):
    assert new.generate_and_rank(config) == old.generate_and_rank(config)


def test_seed_repeat_and_golden():
    result = run()
    assert result == new.generate_and_rank(CONFIG)
    golden = json.loads((Path(__file__).parent / "fixtures/premise_generation_v1_golden.json").read_text())
    assert [r["candidateId"] for r in result["candidates"]] == golden["candidateIds"]
    assert result["generationSummary"] == golden["generationSummary"]
    assert [r["candidateId"] for r in result["top3ProductionCandidates"]] == golden["productionSlate"]


def test_gate_precedes_beat_construction_and_ranker_called_only_once(monkeypatch):
    original = new.legacy.make_candidate
    calls = []
    original_assess = new.gate.assess
    screened = set()

    def assess(candidate, model=None):
        r = original_assess(candidate, model)
        if "frameZeroDescription" not in candidate and r["admitted"]:
            screened.add(
                (
                    candidate["primaryObject"],
                    candidate["everydayGoal"],
                    candidate["composition"]["stateTransition"],
                )
            )
        return r

    def make(composition, shape, cast, config, grammar, data):
        obj = next(o for o in grammar["objects"] if o["id"] == composition["objectId"])
        goal = next(g for g in grammar["goals"] if g["id"] == composition["goalId"])
        assert (obj["name"], goal["visibleAction"], composition["stateTransition"]) in screened
        return original(composition, shape, cast, config, grammar, data)

    rank = ranking.rank_concepts

    def rank_once(candidates):
        calls.append(len(candidates))
        return rank(candidates)

    monkeypatch.setattr(new.gate, "assess", assess)
    monkeypatch.setattr(new.legacy, "make_candidate", make)
    monkeypatch.setattr(new.ranking, "rank_concepts", rank_once)
    r = new.generate_and_rank(CONFIG)
    assert calls == [20]
    assert r["generationEvidence"]["rejectedPremiseCount"] > 0
    assert all(c["premiseNaturalness"]["admitted"] for c in r["candidates"])
    assert any(x["stage"] == "PREMISE_NATURALNESS" for x in r["generationRejections"])


def test_accepted_scores_reused_and_no_row_mutation():
    r = run()
    assert r["rankingResult"] == ranking.rank_concepts(
        [ranking_input(c["candidate"]) for c in r["candidates"]]
    )
    snapshot = deepcopy(r["rankingResult"])
    new.select_production(
        r["rankingResult"]["rankedEligibleCandidates"], [c["candidate"] for c in r["candidates"]]
    )
    assert r["rankingResult"] == snapshot
    assert r["productionSelection"]["policy"]["qualityBand"] == 3
    assert r["productionSelection"]["policy"]["diversityMargin"] == 5
    slate = r["top3ProductionCandidates"]
    assert all(
        old.behaviorally_distinct(a["candidate"], b["candidate"])
        for i, a in enumerate(slate)
        for b in slate[i + 1 :]
    )


def test_naturalness_precedes_id_only_in_close_quality_band():
    r = run()
    c = deepcopy(r["candidates"][0]["candidate"])
    weak = deepcopy(c)
    c["candidateId"], weak["candidateId"] = "z-direct", "a-arbitrary"
    weak["premiseNaturalness"]["goalInterferenceType"] = "CONTRIVED"
    rows = [
        dict(candidateId="a-arbitrary", rankingScore=90, rank=1),
        dict(candidateId="z-direct", rankingScore=89, rank=2),
    ]
    assert new.select_production(rows, [c, weak])["productionOrder"] == ["z-direct", "a-arbitrary"]
    rows[0]["rankingScore"] = 94
    assert new.select_production(rows, [c, weak])["productionOrder"][0] == "a-arbitrary"


def test_all_full_human_reports_and_explicit_configuration():
    r = run()
    assert len(r["humanReadableConcepts"]) == 20
    for report in r["humanReadableConcepts"]:
        for label in [
            "EXPECTED OBJECT BEHAVIOR",
            "WHY THIS OBJECT?",
            "FRAME ZERO",
            "BEAT 1:",
            "BEAT 5 / PAYOFF:",
            "premiseNaturalness:",
            "productionSlateRank:",
        ]:
            assert label in report
    assert r["premiseNaturalnessGateVersion"] == "premise-naturalness-v1"
    assert r["providerCalls"] == 0 and not r["renderAuthorized"]


@pytest.mark.parametrize(
    "config",
    [
        {"premiseNaturalnessGateVersion": "v1"},
        {"generatorVersion": "v2", "premiseNaturalnessGateVersion": "v1"},
        {**CONFIG, "premiseNaturalnessGateVersion": "v9"},
        {**CONFIG, "provider": "openai"},
    ],
)
def test_invalid_api_configs(config):
    assert TestClient(app).post("/api/v1/workflow/concepts/generate", json=config).status_code == 422


def test_api_and_cli_share_pipeline(monkeypatch, capsys):
    response = TestClient(app).post("/api/v1/workflow/concepts/generate", json=CONFIG)
    assert response.status_code == 200 and response.json() == run()
    script = ROOT.parent / "scripts/generate-short-concepts.py"
    spec = importlib.util.spec_from_file_location("premise_cli", script)
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
            "--rank",
        ],
    )
    assert module.main() == 0
    assert json.loads(capsys.readouterr().out) == run()


def test_benchmark_is_read_only_and_retains_historical_scores():
    a = json.loads((ROOT.parent / "docs/short-concept-generation-v2/example-run.json").read_text())
    b = json.loads((ROOT.parent / "docs/beat-grammar-v2/experiment-seed-42-count-20.json").read_text())
    before = deepcopy([a, b])
    comparison = compare_runs(a, b, run())
    assert [a, b] == before
    assert comparison["runs"]["A_originalV2"]["averageShortFormScore"] == 73.7
    assert comparison["runs"]["B_beatGrammarV2"]["averageShortFormScore"] == 65.7


def test_all_protected_files_and_historical_evidence_unchanged():
    manifest = json.loads((ROOT.parent / "docs/premise-naturalness-v1/immutable-before.json").read_text())
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(ROOT.parents[1], manifest)
