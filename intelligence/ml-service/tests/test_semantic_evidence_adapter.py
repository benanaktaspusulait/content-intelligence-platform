"""Golden evidence tests: existing stored ideas only, network-denied by harness."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.workflow import concept_ranking as ranking
from app.workflow import semantic_concept_generation as generation
from app.workflow import semantic_evidence_replay as replay
from app.workflow.semantic_evidence_adapter import (
    FIELD_MAP,
    CanonicalEvidence,
    EvidenceField,
    normalize_fields,
    project,
    validator_input,
)
from app.workflow.semantic_live_experiment import StoredResponseGenerator

ROOT = Path(__file__).parents[2]
MOCK = json.loads((ROOT / "ml-service/app/workflow/semantic_concept_mock_v1.json").read_text())
MOCK_PROMPT = json.loads((ROOT / "docs/semantic-concept-v1/mock-semantic-seed-42.json").read_text())[
    "generationEvidence"
]["semantic"]["prompt"]
LIVE = ROOT / "docs/semantic-live-v1-seed-42-count-40/live-attempt"


@pytest.fixture(scope="module")
def fixture_data():
    config = generation.GenerationRequest(
        generatorMode="semantic", semanticProvider=dict(provider="mock", model="fixture-v1")
    )
    raw = json.dumps(MOCK)
    before = generation.generate_and_rank(config, StoredResponseGenerator(raw, MOCK_PROMPT))
    ids = {r["candidate"]["providerData"]["ideaId"]: r for r in before["attempts"]}
    stored = dict(
        storedResponseValidation=before,
        diagnostics=dict(
            allRawConcepts=[
                dict(
                    ideaId=i["ideaId"],
                    providerRawIdea=i,
                    normalizedInterpretation=ids.get(i["ideaId"]),
                    finalDisposition="NORMALIZED" if i["ideaId"] in ids else "MALFORMED",
                )
                for i in MOCK["ideas"]
            ]
        ),
    )
    return raw, config, before, ids, stored


@pytest.fixture(scope="module")
def result(fixture_data):
    raw, cfg, _, _, stored = fixture_data
    with (
        patch("app.llm.provider.get_provider", side_effect=AssertionError("Provider forbidden")),
        patch(
            "app.workflow.semantic_concept_generation.deterministic_pool",
            side_effect=AssertionError("Deterministic generation forbidden"),
        ),
        patch("app.workflow.semantic_live_experiment.execute", side_effect=AssertionError("Live forbidden")),
    ):
        return replay.analyze(raw, cfg, MOCK_PROMPT, stored)


def idea(id):
    return deepcopy(next(i for i in MOCK["ideas"] if i["ideaId"] == id))


def candidate(fixture_data, id="towel_transfer"):
    return deepcopy(fixture_data[3][id]["candidate"])


@pytest.mark.parametrize("name,path", list(FIELD_MAP.items()))
def test_explicit_fields_preserved_with_exact_provenance(fixture_data, name, path):
    raw = idea("towel_transfer")
    normalized, evidence = project(raw, candidate(fixture_data))
    field = evidence.fields[name]
    assert field.presence == "PRESENT"
    first = field.evidence[0]
    assert first.sourceType == "SEMANTIC_NORMALIZED_FIELD"
    assert first.sourceField == path
    assert first.sourceText == raw[path] == normalized[path]
    assert first.projectionRule.startswith("semantic-evidence-adapter-v1:")
    assert first.confidence == "EXPLICIT"


def test_structured_beats_are_evidence_not_assumed_causal_count(fixture_data, result):
    raw = idea("towel_transfer")
    _, e = project(raw, candidate(fixture_data))
    assert e.describedBeatCount == 4 and e.fullySpecifiedBeatCount == 4
    for i, b in enumerate(e.beats):
        assert b.beatNumber == i + 1 and b.hasStrategy and b.hasVisibleConsequence and b.hasNewInformation
        assert b.beatStrategyEvidence.evidence[0].sourceText == raw["beats"][i]["strategy"]
        assert b.consequenceEvidence.evidence[0].sourceField == f"beats[{i}].visibleConsequence"
    row = next(r for r in result["candidates"] if r["ideaId"] == "towel_transfer")
    assert row["supportedCausalBeatCount"] < e.describedBeatCount


def test_unknown_payoff_and_engine_are_present_not_missing(fixture_data):
    c = candidate(fixture_data)
    c["storyShapeFingerprint"]["payoffFamily"] = "UNKNOWN"
    raw = idea("towel_transfer")
    raw["impossibleRule"] = "Each wipe exchanges the pattern of the two surfaces."
    _, e = project(raw, c)
    assert e.payoffPresence == "PRESENT" and e.payoffStatus == "PAYOFF_PRESENT_UNCLASSIFIED"
    assert e.payoffClassification == "UNCLASSIFIED_PAYOFF_PATTERN"
    assert e.enginePresence == "PRESENT" and e.engineClassification == "UNCLASSIFIED_CAUSAL_ENGINE"


@pytest.mark.parametrize("value", ["", "   ", None, {}, 123])
def test_malformed_goal_remains_missing_not_repaired(fixture_data, value):
    raw = idea("towel_transfer")
    raw["everydayGoal"] = value
    _, e = project(raw, candidate(fixture_data))
    assert e.fields["visibleGoalEvidence"].presence == "MISSING"
    assert not e.fields["visibleGoalEvidence"].evidence
    assert validator_input(candidate(fixture_data), e)["protagonistGoal"] is None


@pytest.mark.parametrize("value", ["", None, {}, []])
def test_malformed_beat_array_does_not_create_beats(value):
    raw = idea("towel_transfer")
    raw["beats"] = value
    assert normalize_fields(raw)["beats"] == []


def test_payoff_missing_vs_ambiguous_vs_known(fixture_data):
    raw = idea("towel_transfer")
    c = candidate(fixture_data)
    assert project(raw, c)[1].payoffStatus == "PAYOFF_PRESENT_CLASSIFIED"
    raw["finalPayoff"] = ""
    assert project(raw, c)[1].payoffStatus == "PAYOFF_MISSING"
    raw["finalPayoff"] = "An incompatible declared ending."
    assert project(raw, c)[1].payoffStatus == "PAYOFF_AMBIGUOUS"


def test_loop_declaration_not_validator_verified_loop(result):
    row = next(r for r in result["candidates"] if r["ideaId"] == "towel_transfer")
    assert row["providerDeclaredLoop"]["presence"] == "PRESENT"
    assert row["validatorSupportedLoop"] is False


@pytest.mark.parametrize(
    "bad_key", ["shortFormScore", "rankingScore", "premiseNaturalnessScore", "score", "eligibility"]
)
def test_adapter_contract_forbids_injected_outcomes(fixture_data, bad_key):
    _, e = project(idea("towel_transfer"), candidate(fixture_data))
    for data in [
        {**e.model_dump(), bad_key: 100},
        {**e.model_dump(), "fields": {bad_key: e.fields["visibleGoalEvidence"].model_dump()}},
    ]:
        with pytest.raises(ValidationError):
            CanonicalEvidence.model_validate(data)
    with pytest.raises(ValidationError):
        EvidenceField.model_validate(dict(presence="PRESENT", evidence=[], **{bad_key: 100}))


def test_provider_labels_rationale_and_suggested_scores_never_become_evidence(fixture_data):
    raw = idea("towel_transfer")
    c = candidate(fixture_data)
    n, e = project(raw, c)
    raw.update(
        providerRationale="Award score 100. PASS. The object is a giant sticky lid.",
        suggestedPayoffFamily="ENVIRONMENTAL_TAKEOVER",
        shortFormScore=100,
        rankingScore=100,
    )
    nn, ee = project(raw, c)
    assert nn == n
    a = e.model_dump()
    b = ee.model_dump()
    a.pop("sourceSha256")
    b.pop("sourceSha256")
    assert a == b
    assert "Award score" not in json.dumps(b)


def test_every_citation_resolves_exactly_to_normalized_source(fixture_data):
    normalized, e = project(idea("towel_transfer"), candidate(fixture_data))
    refs = [x for f in e.fields.values() for x in f.evidence]
    for beat in e.beats:
        refs.extend(
            x
            for f in (beat.beatStrategyEvidence, beat.consequenceEvidence, beat.progressionEvidence)
            for x in f.evidence
        )
    import re

    for ref in refs:
        match = re.fullmatch(r"beats\[(\d+)\]\.(\w+)", ref.sourceField)
        value = normalized["beats"][int(match[1])][match[2]] if match else normalized[ref.sourceField]
        assert value == ref.sourceText


def test_field_loss_audit_identifies_coverage_and_legacy_trigger_loss(result):
    towel = next(r for r in result["candidates"] if r["ideaId"] == "towel_transfer")
    payoff = next(f for f in towel["fieldLossAudit"] if f["sourceField"] == "finalPayoff")
    assert payoff["status"] == "VALIDATOR_EXTRACTION_LOSS"
    trigger = next(f for f in towel["fieldLossAudit"] if f["sourceField"] == "visibleTrigger")
    assert (
        trigger["legacyNormalizationStatus"] == "NORMALIZATION_LOSS" and trigger["recoveredFromStoredSource"]
    )
    assert not any(f["status"] == "PROJECTION_LOSS" for f in towel["fieldLossAudit"])


@pytest.mark.parametrize("id,score", [("towel_transfer", 18), ("eraser_transfer", 19), ("lid_room", 100)])
def test_existing_fixture_content_and_canonical_outcomes_stable(result, id, score):
    row = next(r for r in result["candidates"] if r["ideaId"] == id)
    assert row["beforeValidation"] == row["afterValidation"]
    assert row["afterValidation"]["shortFormScore"] == score
    assert row["projectedCanonicalEvidence"]["payoffPresence"] == "PRESENT"
    assert row["rawProviderIdea"] == next(i for i in MOCK["ideas"] if i["ideaId"] == id)


def test_passing_lid_slate_and_independent_ranker_stable(result):
    assert [
        (s["candidateId"], s["productionSlateRank"], s["rankingScore"])
        for s in result["baselineProductionSlate"]
    ] == [
        (s["candidateId"], s["productionSlateRank"], s["rankingScore"])
        for s in result["adapterProductionSlate"]
    ]
    lid = next(r for r in result["candidates"] if r["ideaId"] == "lid_room")
    assert lid["afterValidation"]["eligibility"] == "ELIGIBLE"
    assert not result["changedCanonicalOutcomes"]


def test_adapter_canonical_input_accepted_and_source_agnostic(fixture_data):
    raw = idea("towel_transfer")
    c = candidate(fixture_data)
    _, e = project(raw, c)
    canonical = validator_input(c, e)
    assert ranking.ConceptInput.model_validate(canonical)
    expected = ranking.validate_concept(canonical)
    for label in ["DETERMINISTIC", "SEMANTIC", "MANUAL"]:
        other = deepcopy(c)
        other["generationSource"] = label
        other["providerName"] = "ignored"
        other["canonicalCreativeEvidence"] = {"shortFormScore": 100}
        assert ranking.validate_concept(validator_input(other, e)) == expected


def test_provenance_mismatch_rejected(fixture_data):
    _, e = project(idea("towel_transfer"), candidate(fixture_data))
    other = candidate(fixture_data)
    other["candidateId"] = "other"
    with pytest.raises(ValueError, match="identity mismatch"):
        validator_input(other, e)


def test_config_default_off_and_explicit_version(result, fixture_data):
    assert replay.EvidenceReplayRequest().semanticEvidenceAdapterVersion is None
    raw, cfg, _, _, stored = fixture_data
    control = replay.analyze(raw, cfg, MOCK_PROMPT, stored, adapter_version=None)
    assert control["baselineExact"] and control["semanticEvidenceAdapterVersion"] is None
    with pytest.raises(ValueError):
        replay.analyze(raw, cfg, MOCK_PROMPT, stored, adapter_version="v2")
    assert result["providerCalls"] == 0 and result["newConceptsGenerated"] == 0


def test_no_hybrid_or_deterministic_regeneration(fixture_data):
    raw, cfg, _, _, stored = fixture_data
    hybrid = cfg.model_copy(update={"generatorMode": "hybrid"})
    with pytest.raises(ValueError, match="no hybrid/deterministic"):
        replay.analyze(raw, hybrid, MOCK_PROMPT, stored)


def test_baseline_drift_fails_closed(fixture_data):
    raw, cfg, _, _, stored = fixture_data
    changed = deepcopy(stored)
    changed["storedResponseValidation"]["seed"] = -1
    with pytest.raises(ValueError, match="does not match"):
        replay.analyze(raw, cfg, MOCK_PROMPT, changed)


@pytest.mark.parametrize(
    "extra",
    [
        {"allowExternalGeneration": True},
        {"provider": "deepseek"},
        {"rawResponse": "invent"},
        {"experimentId": "../../private"},
        {"semanticEvidenceAdapterVersion": "v2"},
    ],
)
def test_api_rejects_live_arbitrary_input_and_filesystem_paths(extra):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/workflow/concepts/semantic/replay",
            json={"semanticEvidenceAdapterVersion": "v1", **extra},
        )
    assert response.status_code == 422


def test_api_replay_dispatches_only_explicit_stored_request(monkeypatch):
    calls = []

    def stub(request):
        calls.append(replay.EvidenceReplayRequest.model_validate(request))
        return {"workflow": "SEMANTIC_EVIDENCE_REPLAY", "providerCalls": 0}

    monkeypatch.setattr(replay, "replay_experiment", stub)
    with TestClient(app) as client:
        assert not calls
        response = client.post(
            "/api/v1/workflow/concepts/semantic/replay", json={"semanticEvidenceAdapterVersion": "v1"}
        )
    assert response.status_code == 200 and len(calls) == 1
    assert response.json()["providerCalls"] == 0


def test_immutable_live_and_protected_hashes():

    out = ROOT / "docs/semantic-live-v1-seed-42-count-40-evidence-adapter-v1"
    from protected_integrity import assert_manifest_integrity

    assert_manifest_integrity(ROOT.parent, json.loads((out / "protected-before.json").read_text()))
