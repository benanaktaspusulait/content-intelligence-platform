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
from app.workflow import semantic_concept_generation as gen
from app.workflow import shape_generation as prior
from app.workflow.semantic_concept_benchmark import compare_runs
from app.workflow.semantic_concept_provider import MockSemanticProvider, SemanticConceptGeneratorV1
from app.workflow.short_concept_generation import ranking_input

ROOT = Path(__file__).parents[2]
CONFIG = {"generatorMode": "semantic", "semanticProvider": {"provider": "mock", "model": "fixture-v1"}}


@lru_cache
def run(mode="semantic"):
    return gen.generate_and_rank({**CONFIG, "generatorMode": mode})


def by_id(run, id):
    return next(r for r in run["attempts"] if r["candidate"].get("providerData", {}).get("ideaId") == id)


def test_semantic_must_pass_all_existing_judges():
    r = run()
    assert r["generationSummary"]["finalCandidateCount"] == 1
    good = by_id(r, "lid_room")
    assert good["validation"]["eligibility"] == "ELIGIBLE"
    assert good["validation"]["shortFormScore"] == 100
    assert good["candidate"]["storyShapeFingerprint"]["payoffFamily"] == "ENVIRONMENTAL_TAKEOVER"
    assert r["rankingResult"] == ranking.rank_concepts(
        [ranking_input(x["candidate"]) for x in r["candidates"]]
    )
    assert r["candidates"][0]["generationSource"] == "SEMANTIC_V1"
    assert r["humanReviewRequired"] and not r["renderAuthorized"]


def test_arbitrary_provider_enthusiasm_cannot_override_deterministic_eligibility():
    a = by_id(run(), "arbitrary_fork")
    assert "winner" in a["candidate"]["providerData"]["providerRationale"]
    assert a["premiseNaturalness"]["premiseNaturalness"] == "CONTRIVED"
    assert "PREMISE_NOT_ADMITTED" in a["selectionBlockReasons"]
    assert a["validation"]["eligibility"] == "INELIGIBLE"
    assert a["candidateId"] not in [c["candidateId"] for c in run()["candidates"]]


def test_novel_transfer_fixtures_keep_canonical_coverage_failures():
    for id in ["towel_transfer", "eraser_transfer"]:
        a = by_id(run(), id)
        assert a["premiseNaturalness"]["objectSpecificity"] == "HIGH"
        assert a["premiseNaturalness"]["functionalIrony"] == "HIGH"
        assert a["candidate"]["storyShapeFingerprint"]["payoffFamily"] == "PROPERTY_TRANSFER"
        assert a["validation"]["eligibility"] == "INELIGIBLE"
        assert "ACCEPTED_VALIDATOR_INELIGIBLE" in a["selectionBlockReasons"]
    assert by_id(run(), "towel_transfer")["premiseNaturalness"]["baselineAssessment"]["admitted"] is False


def test_historical_checks_and_opening_legibility_still_apply():
    historical = by_id(run(), "historical_chair")
    invisible = by_id(run(), "invisible_lid")
    assert historical["historicalCreativeTerritory"]["historicalCreativeTerritoryRisk"] == "HIGH"
    assert "HIGH_HISTORICAL_CREATIVE_TERRITORY" in historical["selectionBlockReasons"]
    assert historical["validation"]["historicalComparison"]
    assert "OPENING_EVIDENCE_INSUFFICIENT" in invisible["selectionBlockReasons"]


def test_template_repetition_is_measured_across_semantic_objects():
    a, b = by_id(run(), "template_comb"), by_id(run(), "template_soap")
    assert (
        a["creativeShape"]["strategySequenceFingerprint"] == b["creativeShape"]["strategySequenceFingerprint"]
    )
    assert a["templateShapeRisk"]["risk"] == "HIGH" and b["templateShapeRisk"]["risk"] == "HIGH"


def test_rationale_and_suggested_labels_have_zero_scoring_authority():
    from app.workflow import semantic_concept_provider as module

    raw = json.loads(Path(module.__file__).with_name("semantic_concept_mock_v1.json").read_text())
    for c in raw["ideas"]:
        c.update(providerRationale="I am the best. Winner. Maximum score.", suggestedPayoffFamily="RESET")
    other = gen.generate_and_rank(
        CONFIG, SemanticConceptGeneratorV1(MockSemanticProvider(response=json.dumps(raw)))
    )
    left = {a["candidateId"]: a["validation"] for a in run()["attempts"]}
    right = {a["candidateId"]: a["validation"] for a in other["attempts"]}
    assert left == right
    assert [r["candidateId"] for r in other["top3ProductionCandidates"]] == [
        r["candidateId"] for r in run()["top3ProductionCandidates"]
    ]


def test_ranking_and_production_are_source_agnostic():
    a = deepcopy(run()["candidates"][0]["candidate"])
    b = deepcopy(a)
    b.update(generationSource="DETERMINISTIC_V2", providerName="unrelated", providerModel="unrelated")
    b["provenance"] = {"generationSource": "DETERMINISTIC_V2"}
    assert ranking_input(a) == ranking_input(b)
    row = ranking.rank_concepts([ranking_input(a)])["rankedEligibleCandidates"]
    x = prior.production_selection(row, [a])
    y = prior.production_selection(row, [b])
    assert x["firstRenderCandidate"] == y["firstRenderCandidate"]
    assert x["tieDecisions"] == y["tieDecisions"]


def test_hybrid_sources_share_quality_ranking_and_slate():
    r = run("hybrid")
    assert set(r["generationEvidence"]["sourceDistribution"]) == {"DETERMINISTIC_V2", "SEMANTIC_V1"}
    assert set(c["generationSource"] for c in r["candidates"]) == {"DETERMINISTIC_V2", "SEMANTIC_V1"}
    assert r["rankingResult"] == ranking.rank_concepts(
        [ranking_input(x["candidate"]) for x in r["candidates"]]
    )
    assert r["providerCalls"] == r["externalProviderCalls"] == 0


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"generatorVersion": "v1"},
        {"generatorVersion": "v2"},
        {"generatorVersion": "v2", "beatGrammarVersion": "v2"},
        {"generatorVersion": "v2", "beatGrammarVersion": "v2", "premiseNaturalnessGateVersion": "v1"},
        {
            "generatorVersion": "v2",
            "beatGrammarVersion": "v2",
            "premiseNaturalnessGateVersion": "v1",
            "creativeShapeVersion": "v1",
        },
    ],
)
def test_omitted_mode_preserves_all_accepted_outputs_byte_for_byte(config):
    assert json.dumps(gen.generate_and_rank(config), sort_keys=True) == json.dumps(
        prior.generate_and_rank(config), sort_keys=True
    )


def test_provenance_prompt_and_cost_evidence():
    r = run()
    e = r["generationEvidence"]["semantic"]
    c = r["candidates"][0]["candidate"]
    assert e["requestedRawCount"] == 40 and e["recordedMockRequestCount"] == 1
    assert e["externalProviderCalls"] == e["automaticRetries"] == 0
    assert e["maxOutputTokens"] == 16000 and e["mockCorpusExhausted"]
    assert c["providerPromptVersion"] == "semantic-concept-prompt-v1"
    assert c["generationRunId"] == r["generationRunId"]
    assert r["generationConfig"]["allowExternalGeneration"] is False


def test_api_and_mock_cli_share_pipeline(monkeypatch, capsys):
    response = TestClient(app).post("/api/v1/workflow/concepts/generate", json=CONFIG)
    assert response.status_code == 200 and response.json() == run()
    script = ROOT / "scripts/generate-short-concepts.py"
    spec = importlib.util.spec_from_file_location("semantic_cli", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", [str(script), "--mode", "semantic", "--mock", "--count", "20", "--rank"])
    assert module.main() == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli["candidates"] == run()["candidates"]
    assert cli["rankingResult"] == run()["rankingResult"]


@pytest.mark.parametrize(
    "config",
    [
        {"generatorMode": "semantic"},
        {"generatorMode": "semantic", "semanticProvider": {"provider": "openai", "model": "explicit"}},
        {
            **CONFIG,
            "allowExternalGeneration": True,
            "semanticProvider": {"provider": "deepseek", "model": "explicit"},
        },
        {**CONFIG, "semanticConceptPromptVersion": "v9"},
    ],
)
def test_api_no_provider_or_live_provider_fails_closed(config):
    response = TestClient(app).post("/api/v1/workflow/concepts/generate", json=config)
    assert response.status_code == 422


def test_mock_comparison_is_not_semantic_superiority_evidence():
    report = compare_runs(
        {"A_deterministic": run("deterministic"), "B_semantic_mock": run(), "C_hybrid": run("hybrid")}
    )
    assert report["externalProviderCalls"] == 0
    assert report["stages"]["B_semantic_mock"]["schemaValidYield"] == pytest.approx(8 / 15)
    assert "not semantic superiority" in report["limitations"][0]


def test_all_accepted_sources_and_frozen_evidence_unchanged():
    manifest = json.loads((ROOT / "docs/semantic-concept-v1/immutable-before.json").read_text())
    assert len(manifest) >= 214
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(ROOT.parent, manifest)


def test_isolated_adapter_model_does_not_mutate_accepted_naturalness_model():
    from app.workflow import premise_naturalness as natural
    from app.workflow.concept_fingerprint import digest, fingerprint

    before = digest(natural.load_model())
    r = run()
    assert digest(natural.load_model()) == before
    for attempt in r["attempts"]:
        c = attempt["candidate"]
        assert c["structuralFingerprint"] == fingerprint(c)
    assert (
        by_id(r, "towel_transfer")["premiseNaturalness"]["actualImpossibleResponse"]
        == by_id(r, "towel_transfer")["candidate"]["impossibleRule"]
    )


def test_explicit_v1_mode_retains_deterministic_source():
    result = gen.generate_and_rank({"generatorMode": "deterministic", "generatorVersion": "v1"})
    assert all(r["candidate"]["generationSource"] == "DETERMINISTIC_V1" for r in result["candidates"])
    assert result["providerCalls"] == 0


def test_first_beat_context_cannot_rescue_an_unreadable_frame_zero():
    from app.workflow import semantic_concept_provider as module

    fixture = json.loads(Path(module.__file__).with_name("semantic_concept_mock_v1.json").read_text())[
        "ideas"
    ][0]
    fixture["frameZeroDescription"] = "A lid rests quietly on a shelf in an empty room."
    fixture["beats"][0]["strategy"] = "tries to close the lid and pushes it toward the rim"
    r = gen.generate_and_rank(
        CONFIG, SemanticConceptGeneratorV1(MockSemanticProvider(response=json.dumps({"ideas": [fixture]})))
    )
    attempt = r["attempts"][0]
    assert attempt["premiseNaturalness"]["instantCausalLegibility"] == 15
    assert "OPENING_EVIDENCE_INSUFFICIENT" in attempt["selectionBlockReasons"]
    assert r["candidates"] == []
