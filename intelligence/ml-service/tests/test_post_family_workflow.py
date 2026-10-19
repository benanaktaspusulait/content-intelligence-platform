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


def test_juice_story_gates_fail_closed_for_unmotivated_and_unverified_openings():
    flawed = """11-second video
0.0-2.0 SEC: At frame zero Kiko holds a tilted cup and watches orange juice curve upward back into it. Kiko tilts the cup farther.
2.0-4.0 SEC: Kiko rotates the cup toward horizontal; the juice climbs into a taller arc.
4.0-6.0 SEC: Kiko puts an open palm under the cup, expecting the juice to fall, but it returns to the cup.
6.0-8.5 SEC: Kiko turns the cup upside down; the juice still curls into it.
8.5-11.0 SEC: The stream retracts, leaving the inverted cup full. Kiko looks at his dry palm."""
    positive = """11-second video
Kiko is thirsty and wants to drink his juice.
0.0-2.0 SEC: Already trying to drink at frame zero, Kiko holds the cup to his mouth, but the orange juice ribbon curves away and returns to the cup before it can reach his lips.
2.0-4.0 SEC: Still trying to drink, Kiko tips the cup farther over his mouth; the same ribbon climbs higher and returns inside instead of reaching him.
4.0-6.0 SEC: Kiko takes a careful sip from the rim, but the juice again flows upward into the cup, leaving his mouth dry.
6.0-8.5 SEC: Kiko turns the cup upside down over his mouth to empty it; the juice still curls back into the cup.
8.5-11.0 SEC: Kiko turns the cup upright and drinks normally as the ribbon finally settles inside; his thirst is relieved."""

    for prompt, expected_goal in ((flawed, "FAIL"), (positive, "UNKNOWN")):
        result = review_prompt(request(prompt, contentProfile="CURIOSITY_ADVENTURE"))
        rows = result["canonicalRuleEvaluation"]
        gate_rows = {
            row["ruleId"]: row
            for group in ("passedRules", "failedRules", "unknownRules", "notApplicableRules")
            for row in rows[group]
        }
        assert gate_rows["GOAL_001"]["outcome"] == expected_goal
        assert result["family8"]["renderAuthorization"]["status"] != "AUTHORIZED"
        reasons = result["family8"]["renderAuthorization"]["reasons"]
        assert any(row["source"] == "FIRST_FRAME_VISUAL_LEGIBILITY" for row in reasons)
        assert any(row["source"] == "GOAL_001" for row in reasons)


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


def test_step4_candidate_envelope_is_not_misclassified_as_a_contradictory_tracked_plan():
    value = request("0-2s: Mimi pulls a note.\n2-5s: The note splits into two.", structuredPlan={
        "evidenceStatus": "DETERMINISTIC_SOURCE_EVENTS_ONLY", "sourceVersion": "1",
        "events": [{"sourceQuote": "0-2s: Mimi pulls a note.", "action": "Mimi pulls a note."}],
    })
    result = review_prompt(value)
    assert not any(c["state"] in {"CONTRADICTORY", "INVALID"} for c in result["productionEvidence"]["claims"])
    assert not any(r["code"] == "ASSESSMENT_TECHNICAL_FAILURE" for r in result["family8"]["renderAuthorization"]["reasons"])
    assert result["family8"]["renderAuthorization"]["status"] != "AUTHORIZED"
    assert next(c for c in result["productionEvidence"]["claims"] if c["field"] == "sourceEventCandidates")["state"] == "INFERRED"


def test_invalid_tracked_plan_keeps_technical_blocker_with_diagnostic_instead_of_story_contradiction():
    value = request(structuredPlan={"beats": []})
    result = review_prompt(value)
    diagnostic = next(c for c in result["productionEvidence"]["claims"] if c["field"] == "trackedPlan")
    assert diagnostic["state"] == "INVALID"
    assert diagnostic["diagnosticCode"] == "EMPTY_TRACKED_BEATS"
    authorization = result["family8"]["renderAuthorization"]
    assert authorization["status"] == "BLOCKED_TECHNICAL_FAILURE"
    reason = next(r for r in authorization["reasons"] if r["code"] == "ASSESSMENT_TECHNICAL_FAILURE")
    assert "EMPTY_TRACKED_BEATS" in reason["message"]
    assert "Contradictory source evidence" not in reason["message"]
    assert reason["references"] == []
