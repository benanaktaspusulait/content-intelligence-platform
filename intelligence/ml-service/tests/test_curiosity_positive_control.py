from app.workflow.review import _run_canonical_evaluation
from app.workflow.api import ReviewRequest
from app.config import settings
from app.rules.rule_engine import RuleEngine
from app.workflow.review import apply_profile_rule_exclusions


SOURCE = """Human/video-derived reconstruction; not provider-authored dialogue. Duration 15.104 seconds.
0.0-4.0 seconds: Two children pull at the lid of a visibly locked wooden chest; it does not open. Their apparent goal is to open the chest and discover what is inside. The view widens to the group around the chest; an adult owl holds a lantern.
4.0-6.5 seconds: The children gesture and look around the chest area while the adult holds the lantern. No key is readable yet.
6.5-8.0 seconds: A close-up clearly reveals a small golden key inside the lantern’s glass chamber. The key becomes a clue for the viewer.
8.0-11.5 seconds: Cuts return to the children and adult; a child looks/reacts toward the lantern and it is raised. No key handoff is clearly visible.
11.5-12.8 seconds: The chest is shown open with a paper bearing a map-like drawing and small lettering that is not legible enough to verify.
12.8-15.104 seconds: The group celebrates around the chest; in this wide ending the chest appears closed again, so open-to-closed continuity is uncertain.
Viewer-facing mystery inferred from the locked chest and later key clue: where is the key that can open it? The key is visible to viewers before the child’s apparent recognition, but only midway through the clip, not at frame zero. The payoff is opening the chest and exposing a map-like next clue; its meaning is unverified."""
OPENING_QUOTE = "Two children pull at the lid of a visibly locked wooden chest; it does not open."


def evaluate(source=SOURCE, *, profile="CURIOSITY_ADVENTURE", extra=None):
    request = {
        "prompt": source,
        "sourceId": "video:10_the_hidden_treasure_key",
        "sourceVersion": "video-derived-reconstruction-v1",
        "contentProfile": profile,
        "canonicalRulesetVersion": "1.12",
        "desiredDuration": 15.104,
    }
    if source is SOURCE:
        request.update({
            "viewerQuestion": "Where is the key that can open it?",
            "goalEvidence": {
                "description": "Open the locked wooden chest",
                "goalExplicitness": "IMPLICIT_BUT_OBSERVABLE",
                "obstruction": "visibly locked wooden chest; it does not open",
                "sourceQuote": OPENING_QUOTE,
            },
            "storyPlanEvidence": {
                "character": "children",
                "attempts": [{"strategy": "PULL", "action": "Pull at the chest lid", "sourceQuote": OPENING_QUOTE}],
            },
        })
    request.update(extra or {})
    return _run_canonical_evaluation(request)


def outcomes(result):
    return {
        row["ruleId"]: row["outcome"]
        for key in ("passedRules", "failedRules", "unknownRules", "notApplicableRules")
        for row in result.get(key, [])
    }


def test_historical_video_opening_and_viewer_question_are_evaluated_for_curiosity():
    result = evaluate()
    rules = outcomes(result)
    assert result["status"] == "EVALUATED"
    assert rules["HOOK_004"] == "PASS"
    assert rules["GOAL_VISIBLE_EARLY"] == "PASS"
    assert rules["MINI_STORY_LOCK"] == "PASS"
    assert rules["INSTANT_VISUAL_ABSURDITY_GATE"] == "NOT_APPLICABLE"
    assert rules["ENGINE_SILHOUETTE_DUPLICATE"] == "UNKNOWN"
    assert result["videoPlanIR"]["characters"]["primary"] == "children"
    assert result["videoPlanIR"]["beats"][-1]["endTime"] == 15.104
    assert "contentId" not in result
    assert "promptVersionId" not in result


def test_missing_hook_evidence_is_unknown_and_weak_mystery_stays_blocked():
    weak = """0.0-12.0 seconds: Kiko wants to draw a thank-you picture, but a magical line completes the drawing for her before she can draw it herself."""
    result = evaluate(weak, extra={"viewerQuestion": "What will happen next?"})
    rules = outcomes(result)
    assert rules["HOOK_004"] in {"UNKNOWN", "FAIL"}
    assert rules["MINI_STORY_LOCK"] == "FAIL"
    assert "contentId" not in result and "promptVersionId" not in result


def test_review_api_contract_accepts_source_bound_goal_evidence():
    request = ReviewRequest(
        prompt=SOURCE,
        sourceId="video:10_the_hidden_treasure_key",
        sourceVersion="video-derived-reconstruction-v1",
        profile="post-family-v1",
        contentProfile="CURIOSITY_ADVENTURE",
        canonicalRulesetVersion="1.12",
        goalEvidence={
            "description": "Open the locked wooden chest",
            "goalExplicitness": "IMPLICIT_BUT_OBSERVABLE",
            "obstruction": "visibly locked wooden chest; it does not open",
            "sourceQuote": OPENING_QUOTE,
        },
    )
    assert request.model_dump()["goalEvidence"]["sourceQuote"] == OPENING_QUOTE


def test_absurd_physics_keeps_its_instant_absurdity_gate():
    engine = RuleEngine(settings.rules_dir / "RULESET_1.12.yaml")
    apply_profile_rule_exclusions(engine, "ABSURD_PHYSICS")
    rule = next(row for row in engine.ruleset["rules"] if row["id"] == "INSTANT_VISUAL_ABSURDITY_GATE")
    assert engine._rule_applies(rule, {"metadata": {"contentProfile": "ABSURD_PHYSICS"}})
    failure = engine._evaluate_instant_visual_absurdity_gate({"hook": {}}, rule)
    assert failure.outcome.value == "FAIL"


def test_missing_silhouette_comparison_is_unknown_not_fail():
    engine = RuleEngine(settings.rules_dir / "RULESET_1.12.yaml")
    rule = next(row for row in engine.ruleset["rules"] if row["id"] == "ENGINE_SILHOUETTE_DUPLICATE")
    result = engine._evaluate_engine_silhouette_duplicate({"visualEvidence": {}}, rule)
    assert result.outcome.value == "UNKNOWN"
    duplicate = engine._evaluate_engine_silhouette_duplicate(
        {"visualEvidence": {"silhouette": {"status": "FAIL"}}}, rule
    )
    assert duplicate.outcome.value == "FAIL"
    compared = engine._evaluate_engine_silhouette_duplicate(
        {"visualEvidence": {"silhouette": {"status": "PASS"}}}, rule
    )
    assert compared.outcome.value == "PASS"
