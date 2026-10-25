import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.workflow.semantic_concept_generation import GenerationRequest, generate_and_rank
from app.workflow.semantic_concept_provider import (
    MockSemanticProvider,
    SemanticConceptGeneratorV1,
    SemanticIdea,
    SemanticProviderConfig,
    build_prompt,
    parse_response,
)
from app.workflow.short_concept_generation import ConceptCandidateGenerator, resolve_cast

CONFIG = {"generatorMode": "semantic", "semanticProvider": {"provider": "mock", "model": "fixture-v1"}}


@pytest.fixture
def raw():
    from app.workflow import semantic_concept_provider as module

    return json.loads(Path(module.__file__).with_name("semantic_concept_mock_v1.json").read_text())


def test_generator_conforms_to_existing_provider_boundary_and_makes_one_mock_call(raw):
    config = GenerationRequest.model_validate(CONFIG)
    cast, _ = resolve_cast(config)
    transport = MockSemanticProvider(response=json.dumps(raw))
    generator: ConceptCandidateGenerator = SemanticConceptGeneratorV1(transport)
    values = generator.generate(config, cast)
    assert len(values) == 8 and len(transport.calls) == 1
    assert generator.evidence["externalProviderCalls"] == 0 and generator.evidence["automaticRetries"] == 0
    assert all(c["generationSource"] == "SEMANTIC_V1" for c in values)
    assert all(c["providerName"] == "mock" and c["providerModel"] == "fixture-v1" for c in values)
    assert len(generator.schema_rejections) == 7


def test_prompt_is_versioned_without_finished_recipes():
    config = GenerationRequest.model_validate(CONFIG)
    cast, _ = resolve_cast(config)
    p = build_prompt(config, cast, 40)
    assert p["version"] == "semantic-concept-prompt-v1"
    assert "Do not select winners" in p["system"] and "Strange but intuitive" in p["system"]
    payload = json.loads(p["prompt"])
    assert payload["requestedRawCount"] == 40 and len(payload["historicalCautionZones"]) == 2
    assert all(set(r) == {"referenceId", "signature"} for r in payload["historicalCautionZones"])
    assert "towel" not in p["system"].lower() and "eraser" not in p["system"].lower()
    assert "rankingScore" not in payload["candidateSchema"]["properties"]


def test_schema_partial_rejections_and_duplicate_ids(raw):
    values, rejected = parse_response(json.dumps(raw), 60)
    assert len(values) == 8 and len(rejected) == 7
    assert sum(r["ideaId"] == "duplicate_id" for r in rejected) == 2
    assert all(r["stage"] == "SCHEMA" for r in rejected)


@pytest.mark.parametrize(
    "edit",
    [
        {"rankingScore": 100},
        {"confidence": 1.0},
        {"beats": []},
        {"title": " "},
        {"durationSeconds": float("inf")},
        {"impossibleRule": "A knife appears with blood."},
        {"title": "Invisible\x00control"},
        {"title": "Invisible\u202eformat"},
    ],
)
def test_untrusted_fields_and_unsafe_or_malformed_candidates_rejected(raw, edit):
    item = deepcopy(raw["ideas"][0])
    item.update(edit)
    with pytest.raises(ValueError):
        SemanticIdea.model_validate(item)


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "```json\n{}\n```",
        '{"ideas":NaN}',
        '{"ideas":[],"winner":1}',
        '{"ideas":[],"ideas":[]}',
        "[]",
    ],
)
def test_invalid_response_envelope_fails_closed(text):
    with pytest.raises(ValueError):
        parse_response(text, 60)


def test_size_count_and_final_event_bounds(raw):
    with pytest.raises(ValueError):
        parse_response(" " * 2_000_001, 60)
    with pytest.raises(ValueError):
        parse_response(json.dumps(raw), 1)
    item = deepcopy(raw["ideas"][0])
    item["finalPayoff"] = "A new unrelated ending appears."
    with pytest.raises(ValueError):
        SemanticIdea.model_validate(item)


@pytest.mark.parametrize(
    "provider,allow,message",
    [
        ("openai", False, "EXTERNAL_GENERATION_DISABLED"),
        ("deepseek", False, "EXTERNAL_GENERATION_DISABLED"),
        ("anthropic", True, "LIVE_SEMANTIC_TRANSPORT_NOT_ENABLED"),
    ],
)
def test_live_execution_never_constructs_provider(monkeypatch, provider, allow, message):
    from app.llm import provider as llm

    monkeypatch.setattr(llm, "get_provider", lambda *a, **k: pytest.fail("Live factory must never be called"))
    with pytest.raises(ValueError, match=message):
        generate_and_rank(
            {
                "generatorMode": "semantic",
                "allowExternalGeneration": allow,
                "semanticProvider": {"provider": provider, "model": "explicit-model"},
            }
        )


def test_missing_provider_clear_error():
    with pytest.raises(ValueError, match="SEMANTIC_PROVIDER_NOT_CONFIGURED"):
        generate_and_rank({"generatorMode": "semantic"})


def test_mock_subclass_cannot_smuggle_live_transport():
    class PretendMock(MockSemanticProvider):
        def complete(self, *a, **k):
            pytest.fail("Must be rejected before execution")

    config = GenerationRequest.model_validate(CONFIG)
    cast, _ = resolve_cast(config)
    with pytest.raises(ValueError, match="controlled mock"):
        SemanticConceptGeneratorV1(PretendMock()).generate(config, cast)


def test_provider_configuration_bounds():
    for change in [
        {"maxCandidates": 61},
        {"maxOutputTokens": 0},
        {"timeoutSeconds": 0},
        {"temperature": 3},
        {"baseUrl": "https://example.invalid"},
    ]:
        with pytest.raises(ValueError):
            SemanticProviderConfig.model_validate({"provider": "mock", "model": "fixture-v1", **change})


def test_normal_mock_run_never_uses_provider_factory(monkeypatch):
    from app.llm import provider as llm

    monkeypatch.setattr(llm, "get_provider", lambda *a, **k: pytest.fail("No live factory in mock execution"))
    result = generate_and_rank(CONFIG)
    assert result["externalProviderCalls"] == 0


def test_noncanonical_or_conflicting_characters_rejected_during_normalization(raw):
    config = GenerationRequest.model_validate(CONFIG)
    cast, _ = resolve_cast(config)
    for edit in [
        dict(protagonistSuggestion="Unknown Person"),
        dict(frameZeroDescription="Luca and Kiko both push the growing lid."),
    ]:
        idea = deepcopy(raw["ideas"][0])
        idea.update(edit)
        generator = SemanticConceptGeneratorV1(MockSemanticProvider(response=json.dumps({"ideas": [idea]})))
        assert generator.generate(config, cast) == []
        assert generator.schema_rejections[0]["stage"] == "NORMALIZATION"
        assert generator.evidence["normalizationRejectedCount"] == 1
