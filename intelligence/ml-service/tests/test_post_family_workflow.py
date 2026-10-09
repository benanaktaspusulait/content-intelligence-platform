from copy import deepcopy

import pytest

from app.workflow.review import binding_fingerprint, enrich_production_evidence, review_prompt


def request(prompt="0-6 SEC\nLuca lifts the box. The box opens and a cat waves. CUT.", **extra):
    return dict(
        prompt=prompt,
        sourceId="local/prompt.txt",
        sourceVersion="1",
        profile="post-family-v1",
        references=[],
        desiredDuration=6,
        generator="AUTO",
        settings={"aspectRatio": "9:16"},
        segments=[],
        protectedIntent=["Luca lifts the box"],
        **extra,
    )


def test_missing_evidence_remains_unknown_and_never_confirms_omitted_requirements():
    evidence = enrich_production_evidence(request("An unspecified visual idea."))
    assert evidence["generalProducibility"]["status"] == "UNKNOWN"
    assert any(c["state"] == "MISSING" for c in evidence["claims"])


def test_source_grounded_precision_enrichment_supplies_actual_family10_inputs():
    value = request("0-6 SEC\nLuca must thread a tiny needle with exact finger placement.")
    result = enrich_production_evidence(value)
    assert result["generalProducibility"]["status"] == "RISKY"
    claim = next(c for c in result["claims"] if c["field"] == "fineMotorRequirement")
    assert value["prompt"][claim["span"][0] : claim["span"][1]] == claim["quote"]
    assert claim["sourceHash"] == result["source"]["sha256"]
    assert claim["methodVersion"] and claim["state"] in {"OBSERVED", "INFERRED"}


@pytest.mark.parametrize("key", ["winner", "views", "performanceClass", "corpusRole"])
def test_enrichment_is_independent_of_historical_outcomes(key):
    plain = request()
    assert enrich_production_evidence(plain) == enrich_production_evidence({**plain, key: 1000000})


def test_non_comedic_unresolved_discovery_is_not_forced_to_attempts_or_fake_resolution():
    value = request(
        "0-8 SEC\nLuca and Zipo discover a glowing seed. Its light reveals a hidden path. "
        "They leave together to explore. The mystery remains open.",
        contentProfile="CURIOSITY_ADVENTURE",
    )
    result = review_prompt(value)
    assert result["routing"]["contentProfile"] == "CURIOSITY_ADVENTURE"
    assert result["engagement"]["status"] != "FAIL"
    assert not any(
        f["category"] in {"NOT_FUNNY", "TOO_FEW_ATTEMPTS", "UNRESOLVED_ENDING", "TWO_CHARACTERS"}
        for f in result["executionReview"]["findings"]
    )
    assert result["applicability"]["THREE_ATTEMPTS"]["status"] == "NOT_APPLICABLE"


def test_opening_strategy_does_not_replace_content_family():
    result = review_prompt(request(contentProfile="EDUCATIONAL", openingStrategy="CURIOSITY_DISCOVERY"))
    assert result["routing"]["contentProfile"] == "EDUCATIONAL"
    assert result["opening"]["strategy"] == "CURIOSITY_DISCOVERY"


@pytest.mark.parametrize(
    ("seconds", "quality", "expected"),
    [(5, False, "SEEDANCE_2_0_MINI"), (12, True, "SEEDANCE_2_0"), (27, False, "SEEDANCE_2_5")],
)
def test_all_three_duration_model_preferences_remain_distinct(seconds, quality, expected):
    value = request()
    value.update(
        desiredDuration=seconds, qualityJustification="Required reference fidelity" if quality else ""
    )
    result = review_prompt(value)
    assert result["generation"]["recommendedGenerator"] == expected
    assert result["generation"]["desiredDuration"] == seconds
    assert result["generation"]["supportedRenderDuration"] is None
    assert result["generation"]["capabilityStatus"] == "UNKNOWN"
    assert result["family8"]["renderAuthorization"]["status"] != "AUTHORIZED"


def test_fingerprint_invalidates_prompt_reference_model_duration_settings_segments():
    value = request()
    fingerprint = binding_fingerprint(value)
    for key, changed in [
        ("prompt", "Changed prompt"),
        ("references", [{"sha256": "a" * 64}]),
        ("generator", "SEEDANCE_2_0"),
        ("desiredDuration", 8),
        ("settings", {"aspectRatio": "16:9"}),
        ("segments", [{"end": 5}]),
        ("structuredPlan", {"beats": []}),
        ("viewerQuestion", "New question"),
        ("plannedEditedDuration", 4),
    ]:
        assert binding_fingerprint({**value, key: changed}) != fingerprint


def test_review_is_pure_and_keeps_prompt_and_unknown_visual_evidence_separate():
    value = request()
    before = deepcopy(value)
    result = review_prompt(value)
    assert value == before
    assert result["finalPrompt"] == value["prompt"]
    assert result["opening"]["actualFirstFrame"]["status"] == "UNKNOWN"
    assert result["opening"]["actualOpeningVideo"]["status"] == "UNKNOWN"
    assert result["executionReview"]["visualInspected"] is False
    assert result["family8"]["creativeQuality"]["creativeScore"] is None


def test_explicit_no_lipsync_is_not_a_required_text_dependency():
    from app.workflow.review import enrich_production_evidence

    evidence = enrich_production_evidence(
        {"prompt": "0-6 SEC\nLuca watches the ball. No lip-sync.", "sourceId": "local", "sourceVersion": "1"}
    )
    assert evidence["videoPlanIR"].get("textRequirement", {}).get("required") is not True


def test_lessons_match_resolved_target_capability_and_binding_excludes_mismatches():
    value = {**request(), "generator":"SEEDANCE_2_0_MINI", "contentProfile":"EDUCATIONAL"}
    lesson = {"recordId":"approved-fixture", "targetModelVersion":"fixture-cap-v1", "contentProfile":"EDUCATIONAL", "settings":{"aspectRatio":"9:16"}}
    caps = {"SEEDANCE_2_0_MINI":{"version":"fixture-cap-v1", "modes":{}}}
    good = review_prompt({**value,"retrievedLessons":[lesson]},caps)
    assert good["retrievedLessons"] == [lesson]
    plain = review_prompt(value,caps)
    for invalid in ({**lesson,"targetModelVersion":"wrong"},{**lesson,"contentProfile":"ABSURD_PHYSICS"},{**lesson,"settings":{"aspectRatio":"16:9"}}):
        result = review_prompt({**value,"retrievedLessons":[invalid]},caps)
        assert result["retrievedLessons"] == []
        assert result["bindingHash"] == plain["bindingHash"]
    assert good["bindingHash"] != plain["bindingHash"]
    assert review_prompt({**value,"retrievedLessons":[lesson]})["retrievedLessons"] == []
