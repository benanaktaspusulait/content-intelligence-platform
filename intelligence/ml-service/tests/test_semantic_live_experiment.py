"""All transports here are mocks. Live requests are forbidden by offline harness."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.workflow import semantic_live_diagnostics as diagnostics
from app.workflow import semantic_live_experiment as live
from app.workflow.semantic_concept_generation import GenerationRequest, generate_and_rank
from app.workflow.semantic_concept_provider import MockSemanticProvider, build_prompt
from app.workflow.short_concept_generation import resolve_cast

ROOT = Path(__file__).parents[2]
BASELINE = json.loads((ROOT / "docs/creative-shape-v1/experiment-seed-42-count-20.json").read_text())
PROFILE = dict(
    provider="deepseek",
    model="configured-mock-model",
    baseUrl="https://example.invalid",
    maxOutputTokens=64000,
    contextTokens=1000000,
    inputUsdPerMillion=1.32,
    outputUsdPerMillion=3.96,
    responseMode="json_object",
    tokenParameter="max_tokens",
    temperatureSupported=False,
    reasoningEffort="high",
)
RAW = MockSemanticProvider().response


@pytest.fixture(scope="module")
def result():
    cfg = live.configuration_for(PROFILE)
    cast, _ = resolve_cast(cfg)
    return live.replay(RAW, cfg, live.live_prompt(cfg, cast), BASELINE)


class MockTransport:
    calls = []

    def __init__(self, *args):
        pass

    def complete(self, prompt, system="", temperature=0.7):
        self.calls.append((prompt, system))
        self.last_usage = {"prompt_tokens": 100, "completion_tokens": 200}
        self.last_response_metadata = {"finishReason": "stop", "model": PROFILE["model"]}
        return RAW


def test_default_external_disabled(tmp_path):
    with pytest.raises(ValueError, match="EXTERNAL_GENERATION_DISABLED"):
        live.execute(tmp_path, PROFILE, BASELINE, provider_factory=MockTransport)
    assert not list(tmp_path.iterdir())


def test_budget_and_credentials_before_any_call(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="credential unavailable"):
        live.execute(
            tmp_path, PROFILE, BASELINE, allow_external_generation=True, provider_factory=MockTransport
        )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    for profile in [
        {**PROFILE, "maxOutputTokens": 1000},
        {**PROFILE, "outputUsdPerMillion": 1000},
        {**PROFILE, "contextTokens": 1000},
    ]:
        with pytest.raises(ValueError):
            live.execute(
                tmp_path, profile, BASELINE, allow_external_generation=True, provider_factory=MockTransport
            )
    assert not list(tmp_path.iterdir())


def test_exact_one_request_no_reexecution_and_full_preservation(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    MockTransport.calls = []
    metadata = live.execute(
        tmp_path, PROFILE, BASELINE, allow_external_generation=True, provider_factory=MockTransport
    )
    assert metadata["requestCount"] == 1 and metadata["status"] == "COMPLETED"
    assert len(MockTransport.calls) == 1
    assert (tmp_path / "live-attempt/response.txt").read_text() == RAW
    assert json.loads((tmp_path / "live-attempt/analysis-status.json").read_text())["status"] == "COMPLETED"
    request = json.loads((tmp_path / "live-attempt/request.json").read_text())
    assert request["arguments"]["messages"][0]["content"] == MockTransport.calls[0][
        1
    ] + "\nReturn JSON matching this schema; use catalog IDs exactly:\n" + json.dumps(
        live.response_format()["json_schema"]["schema"], separators=(",", ":")
    )
    assert "test-only" not in "".join(p.read_text() for p in (tmp_path / "live-attempt").iterdir())
    with pytest.raises(FileExistsError):
        live.execute(
            tmp_path, PROFILE, BASELINE, allow_external_generation=True, provider_factory=MockTransport
        )
    assert len(MockTransport.calls) == 1


@pytest.mark.parametrize("failure", ["network", "truncated", "bad_json"])
def test_failure_is_saved_never_retried(tmp_path, monkeypatch, failure):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    calls = []

    class Failure(MockTransport):
        def complete(self, *args, **kwargs):
            calls.append(1)
            self.last_raw_response = '{"ideas": ['
            if failure != "bad_json":
                raise RuntimeError("secret test-only must never be saved")
            return self.last_raw_response

    meta = live.execute(tmp_path, PROFILE, BASELINE, allow_external_generation=True, provider_factory=Failure)
    assert len(calls) == 1
    assert (tmp_path / "live-attempt/response.txt").read_text() == '{"ideas": ['
    if failure != "bad_json":
        assert meta["status"] == "FAILED"
    else:
        assert json.loads((tmp_path / "live-attempt/analysis-status.json").read_text())["status"] == "FAILED"
    assert "test-only" not in (tmp_path / "live-attempt/provider-metadata.json").read_text()
    with pytest.raises(FileExistsError):
        live.execute(tmp_path, PROFILE, BASELINE, allow_external_generation=True, provider_factory=Failure)
    assert len(calls) == 1


def test_wrapper_preserves_v1_and_adds_broad_search():
    cfg = live.configuration_for(PROFILE)
    cast, _ = resolve_cast(cfg)
    original = build_prompt(cfg, cast, 40)
    wrapped = live.live_prompt(cfg, cast)
    assert wrapped["system"] == original["system"]
    assert wrapped["basePromptSha256"] == original["sha256"]
    assert original["version"] == "semantic-concept-prompt-v1"
    assert wrapped["version"] == "semantic-concept-prompt-v1.1"
    payload = json.loads(wrapped["prompt"])
    assert len(payload["historicalCautionZones"]) == 3
    for text in ["delayed consequence", "conservation", "40 raw ideas", "No model scores"]:
        assert text in wrapped["prompt"]


def test_replay_deterministic_actual_provider_provenance_and_no_transport(result):
    cfg = live.configuration_for(PROFILE)
    cast, _ = resolve_cast(cfg)
    again = live.replay(RAW, cfg, live.live_prompt(cfg, cast), BASELINE)
    assert result == again
    for r in result["storedResponseValidation"]["attempts"]:
        c = r["candidate"]
        assert c["providerName"] == PROFILE["provider"] and c["providerModel"] == PROFILE["model"]
        assert c["providerPromptVersion"] == live.PROMPT_VERSION
        assert c["provenance"]["rationaleScored"] is False


def test_all_raw_invalid_and_duplicate_entries_retained(result):
    items = result["diagnostics"]["allRawConcepts"]
    assert len(items) == 15
    assert sum(i["finalDisposition"] == "MALFORMED" for i in items) == 7
    assert len([i for i in items if i["ideaId"] == "duplicate_id"]) == 2
    assert all(i["failureReasons"] for i in items if i["finalDisposition"] == "MALFORMED")


def test_downstream_scores_ranking_and_slate_unchanged(result):
    mock = generate_and_rank(
        dict(generatorMode="semantic", semanticProvider=dict(provider="mock", model="fixture-v1"))
    )
    actual = result["storedResponseValidation"]
    assert {r["candidateId"]: r["validation"]["shortFormScore"] for r in mock["attempts"]} == {
        r["candidateId"]: r["validation"]["shortFormScore"] for r in actual["attempts"]
    }
    assert mock["rankingResult"] == actual["rankingResult"]
    assert [
        (r["candidateId"], r["productionSlateRank"], r["rankingScore"])
        for r in mock["top3ProductionCandidates"]
    ] == [
        (r["candidateId"], r["productionSlateRank"], r["rankingScore"])
        for r in actual["top3ProductionCandidates"]
    ]


def test_low_score_diagnosis_does_not_override(result):
    for i in result["diagnostics"]["allRawConcepts"]:
        if i.get("shortFormScore", 100) < 60:
            d = i["lowScoreDiagnosis"]
            assert d["code"] == "LOW_SCORE_DIAGNOSIS"
            assert not d["scoreOverride"] and d["failedDimensions"]
            assert all(
                x["classification"]
                in ("CONTENT_FAILURE", "STRUCTURE_FAILURE", "EVIDENCE_EXTRACTION_FAILURE", "UNKNOWN")
                for x in d["failedDimensions"]
            )
    towel = next(i for i in result["diagnostics"]["allRawConcepts"] if i["ideaId"] == "towel_transfer")
    assert towel["shortFormScore"] == 18 and towel["humanReview"]
    assert any(
        f["classification"] == "EVIDENCE_EXTRACTION_FAILURE"
        for f in towel["lowScoreDiagnosis"]["failedDimensions"]
    )


def test_audit_raw_opening_separate_from_combined_beat_one(result):
    towel = next(i for i in result["diagnostics"]["allRawConcepts"] if i["ideaId"] == "towel_transfer")
    a = towel["extractionAudit"]
    assert set(a) == {
        "everydayGoal",
        "frameZeroAnomaly",
        "coreRule",
        "trigger",
        "beatCount",
        "causalProgression",
        "payoff",
        "loop",
    }
    assert a["frameZeroAnomaly"]["rawEvidence"] == towel["providerRawIdea"]["frameZeroDescription"]
    assert a["loop"]["status"] == "ambiguous"
    assert a["coreRule"]["status"] == "not recognized"


def test_unclassified_engine_preserved_and_not_promoted():
    raw = next(i for i in json.loads(RAW)["ideas"] if i["ideaId"] == "towel_transfer")
    raw["impossibleRule"] = "Every wipe exchanges the table pattern with the pattern on the cloth."
    cfg = live.configuration_for(PROFILE)
    cast, _ = resolve_cast(cfg)
    run = live.replay(json.dumps({"ideas": [raw]}), cfg, live.live_prompt(cfg, cast), BASELINE)
    item = run["diagnostics"]["allRawConcepts"][0]
    assert item["engineDiscovery"] == "UNCLASSIFIED_CAUSAL_ENGINE"
    assert item["normalizedInterpretation"] and item["canonicalStatus"]
    assert len(run["storedResponseValidation"]["attempts"]) == 1


def test_shape_discovery_against_all_480_not_finalists(result):
    assert len(diagnostics.pool_records(BASELINE)) == 480
    assert result["diagnostics"]["comparison"]["deterministic"]["rawCandidateCount"] == 480
    for i in result["diagnostics"]["allRawConcepts"]:
        if i.get("shapeDiscovery"):
            assert i["shapeDiscovery"]["closestDeterministicCandidateId"]
            assert not i["shapeDiscovery"]["noveltyVerified"]


def test_human_review_set_complete_and_no_ranking_override(result):
    d = result["diagnostics"]
    assert set(d["HUMAN_REVIEW_SET"]) == {
        r["candidateId"] for r in d["allRawConcepts"] if r.get("humanReview")
    }
    assert d["comparison"]["semantic"]["normalizedCount"] == 8
    assert sum(d["bucketCounts"].values()) == 15
    assert "not establish semantic superiority" in " ".join(d["limitations"])


def test_two_view_report_includes_every_raw_field_and_story(result):
    text = diagnostics.markdown(result["diagnostics"])
    for i in result["diagnostics"]["allRawConcepts"]:
        assert str(i["ideaId"]) in text
        if i["providerRawIdea"].get("finalPayoff"):
            assert i["providerRawIdea"]["finalPayoff"] in text
    assert "Provider raw idea" in text and "Normalized / deterministic interpretation" in text


def test_cli_import_no_live_and_optin_required(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "semantic_live_cli", ROOT / "scripts/run-semantic-live-experiment.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(SystemExit):
        module.main(["--replay", "/not-read", "--execute-live"])


def test_existing_api_config_default_still_false():
    cfg = GenerationRequest(
        generatorMode="semantic", semanticProvider=dict(provider="deepseek", model="configured")
    )
    assert not cfg.allowExternalGeneration
    with pytest.raises(ValueError, match="EXTERNAL_GENERATION_DISABLED"):
        generate_and_rank(cfg)


@pytest.mark.parametrize("kind", ["STRUCTURE_FAILURE", "CONTENT_FAILURE", "UNKNOWN"])
def test_diagnostic_classification_explicit_evidence_only(result, kind):
    item = next(i for i in result["diagnostics"]["allRawConcepts"] if i["ideaId"] == "towel_transfer")
    record = deepcopy(item["normalizedInterpretation"])
    raw = deepcopy(item["providerRawIdea"])
    extraction = deepcopy(item["extractionAudit"])
    record["validation"]["rankingDimensions"] = [dict(dimension="progressDensity", score=10, source="test")]
    if kind == "STRUCTURE_FAILURE":
        extraction["causalProgression"]["rawEvidence"] = None
    elif kind == "CONTENT_FAILURE":
        for beat in raw["beats"]:
            beat["visibleConsequence"] = "The identical unchanged outcome."
    d = diagnostics.diagnose(raw, record, extraction)
    assert d["failedDimensions"][0]["classification"] == kind
    assert not d["scoreOverride"]
