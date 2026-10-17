"""Opening evidence must be invariant under unrelated later-beat edits.

The saved P2/OpenAI pair is real-provider evidence.  Replaying it here is an
offline evaluator regression test; it is not a claim about provider quality.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.parser.prompt_parser import ParserConfig, parse_prompt
from app.workflow.review import _run_canonical_evaluation


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "backend/target/disposable-owner-http/run-oT9HS7/real-execution-runtime"


def saved_pair():
    run = json.loads((EVIDENCE / "run-a-final.json").read_text())
    replay = json.loads((EVIDENCE / "offline-real-response-replay.json").read_text())
    return run["scope"], run["scope"]["baselinePrompt"], replay["results"]["openai"]["candidatePrompt"]


def evaluate(scope, prompt):
    with patch("app.llm.semantic_checks.get_provider", side_effect=AssertionError("offline evaluation must not construct a provider")):
        return _run_canonical_evaluation({
            **scope["request"], "prompt": prompt, "canonicalRulesetVersion": "1.11"
        })


def row(result, rule_id):
    return next(item for group in ("passedRules", "failedRules", "unknownRules", "notApplicableRules")
                for item in result[group] if item["ruleId"] == rule_id)


def plan(prompt):
    return parse_prompt(prompt, ParserConfig(
        attempt_evidence_policy="ACTOR_SOURCE_BOUND_V2",
        motion_evidence_policy="TOKEN_MOTION_V2",
    )).video_plan_ir


def test_saved_real_candidate_keeps_identical_opening_inputs_and_hook_result():
    scope, baseline, candidate = saved_pair()
    left, right = plan(baseline), plan(candidate)
    keys = ("sourceQuote", "sourceAction", "action", "consequence", "visualState", "sourceReference")
    assert {key: left["beats"][0].get(key) for key in keys} == {
        key: right["beats"][0].get(key) for key in keys
    }
    assert left["hook"] == right["hook"]
    assert left["hook"]["startsMidAction"] is False

    baseline_result, candidate_result = evaluate(scope, baseline), evaluate(scope, candidate)
    assert row(baseline_result, "HOOK_002")["outcome"] == "PASS"
    assert row(candidate_result, "HOOK_002")["outcome"] == "PASS"
    assert candidate_result["score"] == pytest.approx(baseline_result["score"])
    assert candidate_result["score"] == pytest.approx(93.42708333333334)


@pytest.mark.parametrize("later_edit", [
    " [starting side visible]",
    " [  starting   side   visible  ]",
    " [locked lateral composition]",
    " [static camera with the result held beside the action]",
    "\nPRODUCTION NOTE: Keep later contact readable.",
])
def test_later_beat_and_metadata_edits_cannot_change_hook_002(later_edit):
    scope, baseline, _ = saved_pair()
    changed = baseline.replace("2-5s:", "2-5s:" + later_edit, 1)
    original, edited = evaluate(scope, baseline), evaluate(scope, changed)
    assert plan(baseline)["hook"] == plan(changed)["hook"]
    assert row(original, "HOOK_002") == row(edited, "HOOK_002")


def test_genuine_opening_change_is_detected():
    _, baseline, _ = saved_pair()
    changed = baseline.replace("Already mid-action, Pip", "Start action with Pip", 1)
    assert plan(baseline)["hook"]["startsMidAction"] is False
    assert plan(changed)["hook"]["startsMidAction"] is True


def test_missing_opening_evidence_never_becomes_pass_from_later_start_tokens():
    scope, baseline, _ = saved_pair()
    changed = baseline.replace(
        "Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched.",
        "Pip stands in the room.", 1,
    ).replace("2-5s:", "2-5s: Starting action on the side. ", 1)
    result = evaluate(scope, changed)
    assert plan(changed)["hook"]["startsMidAction"] is False
    assert row(result, "HOOK_002")["outcome"] != "PASS"


def test_actual_p2_stops_prompt_only_generation_but_preserves_score_and_evidence():
    from app.workflow.adaptive_optimization import feasibility
    scope, baseline, _ = saved_pair()
    canonical = evaluate(scope, baseline)
    before = json.dumps(canonical, sort_keys=True)
    decision = feasibility(canonical, baseline)
    assert decision['state'] == 'NO_MATERIAL_PROMPT_ONLY_CREATIVE_GAIN'
    assert not decision['generationAllowed']
    assert not decision['researchGenerationEligibility']['allowed']
    assert decision['creativeOpportunity']['nextAction'] == 'OWNER_APPROVED_STORY_EVOLUTION'
    assert decision['currentScore'] == pytest.approx(93.42708333333334)
    assert json.dumps(canonical, sort_keys=True) == before


def test_visual_uncertainty_alone_does_not_abandon_a_source_valid_concept():
    from app.workflow.adaptive_optimization import creative_scope_decision
    result = creative_scope_decision('0-2s: Already mid-action, Pip touches a light.\n2-15s: The light changes color.', {})
    assert not result['promptOnlyGainLimited']
    assert result['state'] == 'SOURCE_BOUND_PRESENTATION_IMPROVEMENT'


def test_formatting_only_preserves_all_rule_outcomes_and_score():
    scope, baseline, _ = saved_pair()
    before = evaluate(scope, baseline)
    after = evaluate(scope, baseline.replace('\n\n', '\n\n\n'))
    def outcomes(value):
        return {item['ruleId']: (item['outcome'], item['severity'])
                for group in ('passedRules','failedRules','unknownRules','notApplicableRules') for item in value[group]}
    assert outcomes(before) == outcomes(after)
    assert before['score'] == after['score']

