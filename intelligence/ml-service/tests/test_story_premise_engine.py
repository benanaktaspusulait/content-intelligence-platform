"""Offline golden/archetype and adversarial contracts; no historical assets edited."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.workflow.story_premise_engine import assess, scope

CASES = json.loads((Path(__file__).parent / "fixtures/story_premise_cases.json").read_text())
STRONG = CASES["strong"]
WEAK = CASES["weak"]


def row(result, key):
    return next(c for c in result["checks"] if c["checkId"] == key)


@pytest.mark.parametrize("name", STRONG)
def test_strong_active_arcs_have_choice_cost_reuse_and_reversal(name):
    value = assess(STRONG[name])
    assert value["status"] in {"PASS", "PASS_WITH_WARNINGS"}, value["humanReadableReport"]
    assert value["archetype"] == "ACTIVE_MORAL_ARC"
    assert value["score"] >= 80
    for key in ("MORAL_CHOICE_GATE", "SACRIFICE_OR_COST", "TRAIT_REPURPOSING", "STATUS_REVERSAL"):
        assert row(value, key)["outcome"] == "PASS", key
    assert value["meaningShiftCount"] >= 4
    assert {
        "RELATIONSHIP_CHANGE",
        "NEW_INFORMATION",
        "MORAL_CHOICE",
        "GOAL_CHANGE",
        "REINTERPRETATION",
        "STATUS_CHANGE",
    } <= {dimension for event in value["meaningShifts"] for dimension in event["dimensions"]}
    assert value["renderAuthorized"] is False
    assert value["canonicalRulesetUnchanged"] and value["providerCalls"] == 0


@pytest.mark.parametrize("name", WEAK)
def test_weak_golden_concepts_require_story_revision(name):
    value = assess(WEAK[name])
    assert value["status"] == "STORY_REVISION_REQUIRED"
    assert row(value, "MORAL_CHOICE_GATE")["outcome"] != "PASS"
    assert value["score"] < min(assess(text)["score"] for text in STRONG.values())
    assert value["humanReadableReport"].startswith("STORY_REVISION_REQUIRED:")


def test_action_density_does_not_replace_meaning_or_improve_score():
    text = WEAK["action_without_choice"]
    before = assess(text)
    after = assess(
        text.replace(
            "Pip runs, jumps and chases a cart.",
            "Pip runs, chases, jumps, spins, looks, races, pulls and pushes twenty times.",
        )
    )
    assert before["score"] == after["score"]
    assert before["meaningShiftCount"] == after["meaningShiftCount"] == 0
    assert "LOW_MEANING_SHIFT_DENSITY" in {f["code"] for f in after["findings"]}


def test_choice_and_cost_materially_improve_score_and_admission():
    text = STRONG["boogeymans_exam"]
    full = assess(text)
    no_cost = assess(text.replace("Moro officially fails the exam and loses his badge.", "Moro smiles."))
    no_choice = assess(
        text.replace(
            "Moro deliberately drops the exam badge and rejects the chance to scare Noah, choosing to shield Noah instead.",
            "Moro accidentally shields Noah.",
        )
    )
    assert full["score"] > no_cost["score"] >= no_choice["score"]
    assert no_cost["status"] == no_choice["status"] == "STORY_REVISION_REQUIRED"
    assert row(no_cost, "SACRIFICE_OR_COST")["outcome"] != "PASS"
    assert row(no_choice, "MORAL_CHOICE_GATE")["outcome"] != "PASS"


def test_early_solve_penalty_and_independent_duration_suitability():
    value = assess(WEAK["garden_guardian"])
    assert value["archetype"] == "PASSIVE_MISUNDERSTANDING"
    assert value["storyEngineSummary"]["predictabilityRisk"] == "HIGH"
    assert value["durationSuitability"]["10_20_SECONDS"]["status"] == "SUITABLE"
    assert value["durationSuitability"]["45_75_SECONDS"]["status"] == "REVISION_REQUIRED"
    assert "passive misunderstanding" in value["humanReadableReport"]


def test_unrelated_final_skill_cannot_receive_trait_repurposing_credit():
    text = STRONG["boogeymans_exam"].replace(
        "Moro uses the same scary roar to protect Noah from the storm.",
        "Moro suddenly acquires laser vision to protect Noah.",
    )
    assert row(assess(text), "TRAIT_REPURPOSING")["outcome"] != "PASS"


def test_opportunity_must_belong_to_original_actor_and_goal():
    text = STRONG["boogeymans_exam"]
    other_actor = text.replace(
        "Moro can now scare Noah and pass his exam.", "Noah can now scare Moro and pass his exam."
    )
    other_goal = text.replace("Moro can now scare Noah and pass his exam.", "Moro can now bake a cake.")
    for candidate in (other_actor, other_goal):
        assert row(assess(candidate), "MORAL_CHOICE_GATE")["outcome"] != "PASS"


def test_another_actor_cannot_make_the_protagonists_choice():
    text = STRONG["boogeymans_exam"].replace("Moro deliberately drops", "Noah deliberately drops")
    assert row(assess(text), "MORAL_CHOICE_GATE")["outcome"] != "PASS"


def test_restored_original_reward_is_not_a_meaningful_cost():
    text = STRONG["boogeymans_exam"] + "\nMoro regains his exam badge and reward."
    assert row(assess(text), "SACRIFICE_OR_COST")["outcome"] != "PASS"


def test_summary_claims_and_negated_choices_do_not_establish_a_moral_arc():
    text = (
        "Duration: 60 seconds\nArda looks scary but is nice all along.\n"
        "There is no goal, no moral choice, no sacrifice, no hidden intent and no status reversal.\n"
        "Arda never deliberately rejects an opportunity to protect Noah."
    )
    value = assess(text)
    assert value["status"] == "STORY_REVISION_REQUIRED"
    assert row(value, "MORAL_CHOICE_GATE")["outcome"] != "PASS"
    assert row(value, "ACTIVE_DECEPTION_OR_HIDDEN_INTENT")["outcome"] != "PASS"


def test_exact_evidence_offsets_and_deterministic_reproducibility():
    text = STRONG["boogeymans_exam"]
    first = assess(text)
    assert first == assess(text)
    for check in first["checks"]:
        for evidence in check["evidence"]:
            start, end = evidence["sourceSpan"]
            assert text[start:end] == evidence["quote"]
    assert first["payoffTiming"]["status"] == "SUPPORTED"


def test_prose_does_not_invent_timing_or_visual_proof():
    import re

    text = re.sub(r"\d+-\d+s: ", "", STRONG["boogeymans_exam"])
    value = assess(text)
    assert value["payoffTiming"]["status"] == "UNKNOWN"
    assert row(value, "PAYOFF_DENSITY")["outcome"] == "UNKNOWN"
    assert value["storyEngineSummary"]["earlySolveBy15Seconds"] == "UNVERIFIED_EDITORIAL_INFERENCE"
    assert value["status"] == "PASS_WITH_WARNINGS"


def test_long_payoff_gap_and_invalid_time_plan_are_visible():
    text = STRONG["boogeymans_exam"]
    value = assess(text)
    assert value["payoffTiming"]["gaps"]  # action/failure before first bond is not a payoff
    invalid = assess(text.replace("18-28s:", "17-28s:"))
    assert invalid["payoffTiming"]["status"] == "UNKNOWN"


@pytest.mark.parametrize("seconds", [10, 15, 20, 30, 35, 44])
def test_short_form_is_not_activated(seconds):
    assert assess(WEAK["garden_guardian"], {"desiredDuration": seconds}) is None


@pytest.mark.parametrize("seconds", [45, 60, 75])
def test_requested_long_form_duration_activates_even_without_duration_text(seconds):
    assert scope("A story.", {"targetConfiguration": {"duration": seconds}})["active"]


def test_explicit_story_mode_and_duration_precedence():
    assert assess("A story.", {"storyType": "Pompom Stories"}) is not None
    assert scope("Duration: 15 seconds", {"desiredDuration": 60})["active"]
    assert not scope("Duration: 60 seconds", {"desiredDuration": 15})["active"]
    assert not scope("Noah says he will return in 60 seconds.")["active"]
    assert not scope("A story.", {"desiredDuration": float("nan")})["active"]


def test_context_is_not_mutated_and_unknown_language_fails_closed():
    context = {"desiredDuration": 60, "targetConfiguration": {"duration": 60}}
    before = deepcopy(context)
    value = assess("Bir canavar ve bir çocuk arkadaş olur.", context)
    assert context == before
    assert value["status"] == "STORY_REVISION_REQUIRED"
    assert value["storyEngineSummary"]["drivingGoal"] is None


def test_a_late_unrelated_choice_or_reversal_cannot_complete_the_arc():
    text = STRONG["boogeymans_exam"]
    unrelated = text.replace(
        "Moro deliberately drops the exam badge and rejects the chance to scare Noah, choosing to shield Noah instead.",
        "Moro deliberately rejects a holiday trip and chooses to shield Noah instead.",
    )
    assert row(assess(unrelated), "MORAL_CHOICE_GATE")["outcome"] != "PASS"
    unrelated_status = text.replace(
        "Noah calls Moro Best Monster and welcomes him into the family.",
        "Noah calls Eddie Best Monster and welcomes Eddie into the family.",
    )
    assert row(assess(unrelated_status), "STATUS_REVERSAL")["outcome"] != "PASS"


def test_declared_early_resolution_is_penalized_even_when_actions_fill_a_minute():
    text = STRONG["boogeymans_exam"]
    for before, after in [
        ("0-8s:", "0-2s:"),
        ("8-18s:", "2-4s:"),
        ("18-28s:", "4-6s:"),
        ("28-38s:", "6-8s:"),
        ("38-46s:", "8-10s:"),
        ("46-52s:", "10-12s:"),
        ("52-56s:", "12-14s:"),
        ("56-60s:", "14-15s:"),
    ]:
        text = text.replace(before, after)
    text += "\n15-60s: Moro runs, jumps, looks and chases leaves repeatedly."
    value = assess(text)
    assert value["storyEngineSummary"]["earlySolveBy15Seconds"] == "EARLY_RESOLUTION_TEXT_SUPPORT"
    assert value["status"] == "STORY_REVISION_REQUIRED"
    assert row(value, "PREDICTABILITY_EARLY_SOLVE_RISK")["outcome"] == "FAIL"


def test_unmotivated_guest_and_nonvisual_choice_are_warnings():
    text = (
        STRONG["boogeymans_exam"]
        .replace("Moro deliberately drops the exam badge", "Moro consciously abandons the exam badge")
        .replace("choosing to shield Noah instead", "choosing to help Noah instead")
    )
    value = assess(text, {"guestCharacter": "Eddie"})
    codes = {r["code"] for r in value["findings"]}
    assert {"MORAL_CHOICE_VISUALLY_UNCLEAR", "DECORATIVE_GUEST"} <= codes


def test_keyword_order_in_one_sentence_cannot_fake_a_later_moral_choice():
    text = STRONG["boogeymans_exam"]
    text = text.replace("Moro can now scare Noah and pass his exam.", "")
    text = text.replace(
        "Moro deliberately drops the exam badge and rejects the chance to scare Noah, choosing to shield Noah instead.",
        "Moro deliberately rejects the exam and shields Noah before Moro can now scare Noah and pass his exam.",
    )
    assert row(assess(text), "MORAL_CHOICE_GATE")["outcome"] != "PASS"


def test_helping_in_a_different_way_is_not_sacrificing_a_selfish_goal():
    text = (
        "Duration: 60 seconds\nMoro the monster wants to help Noah, but a door blocks him.\n"
        "Moro shares a blanket with Noah.\nMoro can now help Noah.\n"
        "Moro deliberately rejects the chance to help Noah, choosing to shield Noah instead.\n"
        "Moro loses his chance to help Noah.\nMoro becomes a protector."
    )
    result = assess(text)
    assert not result["storyEngineSummary"]["selfInterestedGoalTextSupport"]
    assert row(result, "ROLE_CONTRADICTION")["outcome"] != "PASS"
    assert row(result, "MORAL_CHOICE_GATE")["outcome"] != "PASS"
