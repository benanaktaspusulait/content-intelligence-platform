"""Actor/source provenance and camera separation under Ruleset 1.9."""

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from app.parser.prompt_parser import ParserConfig, parse_prompt
from app.quality.canonical_evidence import attempt_evidence
from app.workflow.review import _run_canonical_evaluation

CONFIG = ParserConfig(attempt_evidence_policy="ACTOR_SOURCE_BOUND_V2")
CONFIG_V3 = ParserConfig(attempt_evidence_policy="ACTOR_SOURCE_BOUND_V3")


def parse(body):
    text = "CHARACTER\nZed\nDuration: 6s\nCORE RULE\nThe card is stuck to Zed.\n" + body
    return text, parse_prompt(text, CONFIG).video_plan_ir


@pytest.mark.parametrize(
    "clause,expected,verb",
    [
        ("Keep the cabinet visible.", False, ""),
        ("Keep Zed's finger in frame.", False, ""),
        ("Zed keeps pulling.", True, "PULL"),
        ("Zed tries to peel the note.", True, "PEEL"),
        ("Zed pulls again.", True, "PULL"),
        ("[static close-up; keep the cabinet visible] Zed tries to peel the note.", True, "PEEL"),
        ("Camera keeps pulling away from Zed; keep the cabinet visible.", False, ""),
        ("[close-up: Zed tries to peel the note; keep the cabinet visible]", True, "PEEL"),
        ("[wide shot containing Zed and the cabinet]", False, ""),
        ("The note splits into two.", False, ""),
        ("[static close-up; keep the finger visible] Zed tries to THE note.", False, ""),
    ],
)
def test_actor_directive_and_verb_contract(clause, expected, verb):
    text, ir = parse("0-3s: " + clause + "\n3-6s: Zed sneezes.")
    b = ir["beats"][0]
    assert b["isAttempt"] is expected and b["primaryVerb"] == verb
    if expected:
        ev = b["attemptEvidence"]
        assert ev["actor"] == "Zed" and ev["relationship"] and ev["confidence"] > 0
        assert text[slice(*ev["sourceSpan"])] == ev["sourceQuote"] == ev["action"]
        assert text[slice(*ev["actorReference"]["sourceSpan"])] == ev["actorReference"]["sourceQuote"]
        for a in ev["actions"]:
            assert text[slice(*a["sourceSpan"])] == a["action"]
            assert text[slice(*a["verbSourceSpan"])] == a["verbQuote"]
            assert a["primaryVerb"] not in {"THE", "A", "AN"}
        assert b["actor"] == "Zed"


def test_distinct_attempts_and_duplicate_same_event():
    text, ir = parse(
        "0-2s: Zed tries to peel the card. [close-up: Zed tries to peel the card.]\n"
        "2-4s: Zed pushes the stuck card away.\n4-6s: Zed tries to twist the card free."
    )
    assert attempt_evidence(ir).count == 3
    assert [b["primaryVerb"] for b in ir["beats"]] == ["PEEL", "PUSH", "TWIST"]
    from app.parser.actor_attempts import bind_beats

    repeated = deepcopy(ir["beats"])
    repeated.append(deepcopy(repeated[0]))
    bind_beats(text, repeated, "Zed")
    assert sum(b["isAttempt"] for b in repeated) == 3
    assert repeated[-1]["attemptEvidence"]["classification"] == "DUPLICATE_SOURCE_EVENT"


def test_attached_participle_attempts_in_echoing_puddle_story_are_source_bound():
    text = (
        "CHARACTER\nKiko\nDuration: 22s\nGoal: Water a wilting seedling.\n"
        "Rule: The puddle returns any object dipped into it.\n"
        "0.0-3.5 SEC: Kiko kneels at a round puddle, holding a small watering can toward the water to fill it for the drooping seedling beside her. The spout echo knocks it away.\n"
        "3.5-7.5 SEC: Kiko tries a new strategy: she cups her hands and dips them in to scoop water. The echo slaps her palms.\n"
        "7.5-11.5 SEC: Kiko changes approach again, lowering the can sideways so only its rim touches. The echo tips it over.\n"
        "11.5-15.5 SEC: Kiko lifts the seedling's drooping leaf and dips its tip into the water. The echo rises.\n"
        "15.5-19.0 SEC: Kiko gently lowers the root ball toward the puddle edge, letting the roots touch the water. The seedling straightens.\n"
        "19.0-22.0 SEC: The seedling stands upright. Kiko pulls her hands back."
    )
    ir = parse_prompt(text, CONFIG_V3).video_plan_ir
    attempts = [beat for beat in ir['beats'] if beat['isAttempt']]
    assert [beat['primaryVerb'] for beat in attempts] == ['HOLD', 'CUP', 'LOWER', 'LIFT', 'LOWER']
    for beat in attempts:
        evidence = beat['attemptEvidence']
        assert evidence['sourceBound'] is True
        assert evidence['contractVersion'] == 'actor-source-bound-v3'
        assert text[slice(*evidence['sourceSpan'])] == evidence['sourceQuote']


def test_bracket_action_camera_and_consequence_spans():
    text, ir = parse(
        "0-3s: [tracking shot: Zed tries to peel the card; keep Zed in frame] -> the card splits.\n"
        "3-6s: Zed tries to pull the card off."
    )
    b = ir["beats"][0]
    assert b["isAttempt"] and b["productionInstructions"] and b["physicalConsequences"]
    assert b["sourceAction"].startswith("Zed tries to peel")
    for obj in b["productionInstructions"] + b["physicalConsequences"]:
        assert text[slice(*obj["sourceSpan"])] == obj["quote"]


def test_saved_original_and_candidates_with_historical_reproduction():
    root = Path(__file__).resolve().parents[3] / "output/verification/ruleset-1.8-creative-review"
    original = json.loads((root / "analysis.json").read_text())
    comparison = json.loads((root / "comparison.json").read_text())
    for _name, saved in [("Original", original)] + [
        (c["candidateId"], c["review"]) for c in comparison["candidates"]
    ]:
        for version in ["1.7", "1.8", "1.9"]:
            request = {
                **saved["boundRequest"],
                "prompt": saved["originalPrompt"],
                "canonicalRulesetVersion": version,
            }
            with patch(
                "app.llm.semantic_checks.get_provider", side_effect=AssertionError("No provider calls")
            ):
                result = _run_canonical_evaluation(request)
            assert result["status"] == "EVALUATED"
            if version == "1.7":
                assert result["score"] == 85
            if version == "1.8":
                assert result["score"] == saved["canonicalRuleEvaluation"]["score"]
            if version == "1.9":
                assert (
                    result["videoPlanIR"]["beats"][0]["isAttempt"] is False
                    and result["videoPlanIR"]["beats"][0]["primaryVerb"] == ""
                )
                assert any(r["ruleId"] == "ATTEMPT_001" for r in result["failedRules"])
                assert [
                    (b["actor"], b["primaryVerb"]) for b in result["videoPlanIR"]["beats"] if b["isAttempt"]
                ] == [("Mimi", "PEEL"), ("Mimi", "PULL")]
                assert result["score"] == original["canonicalRuleEvaluation"]["score"]


def test_frozen_source_multi_attempts_are_not_lost_to_reference_heading():
    root = Path(__file__).resolve().parents[2] / "data/golden/pompom-golden-v1/prompts"
    text = (root / "sticky-ball-01.txt").read_text()
    ir = parse_prompt(text, CONFIG).video_plan_ir
    assert ir["characters"]["primary"] == "Luca"
    assert attempt_evidence(ir).count >= 2
    for b in ir["beats"]:
        if b.get("beatRole") == "ATTEMPT":
            assert b["isAttempt"] and b["attemptEvidence"]["actor"] == "Luca"
            assert text[slice(*b["attemptEvidence"]["sourceSpan"])] == b["attemptEvidence"]["sourceQuote"]
    assert all(b.get("primaryVerb") not in {"THE", "REFERENCE", "REDESIGN"} for b in ir["beats"])


def test_unbracketed_camera_and_object_consequences_are_separate():
    text, ir = parse("0-3s: Keep the cabinet visible.\n3-6s: The note splits into two.")
    assert ir["beats"][0]["productionInstructions"] and not ir["beats"][0]["characterActions"]
    assert ir["beats"][1]["physicalConsequences"] and not ir["beats"][1]["isAttempt"]
    for b in ir["beats"]:
        for obj in b["productionInstructions"] + b["physicalConsequences"]:
            assert text[slice(*obj["sourceSpan"])] == obj["quote"]


@pytest.mark.parametrize(
    "clause", ["[ATTEMPT: PULL] Zed pulls the card.", "Zed tries to peel the card. [ATTEMPT: PEEL]"]
)
def test_actor_action_with_explicit_attempt_marker_remains_supported(clause):
    text, ir = parse("0-3s: " + clause + "\n3-6s: Zed smiles.")
    assert ir["beats"][0]["isAttempt"] and ir["beats"][0]["attemptEvidence"]["sourceBound"]


def test_unicode_offsets_and_pronoun_actor_context():
    text, ir = parse("0-3s: 🎬 Zed tries to peel the stuck card.\n3-6s: She keeps pulling the card away.")
    for b in ir["beats"]:
        ev = b["attemptEvidence"]
        assert b["isAttempt"] and ev["actor"] == "Zed"
        assert text[slice(*ev["sourceSpan"])] == ev["sourceQuote"]
    assert ir["beats"][1]["fieldEvidence"]["actor"]["state"] == "INFERRED"
