from app.workflow.review import _run_canonical_evaluation


STORY = (
    "Frame zero: Kiko, mouth wide open, jabs the toothbrush toward his teeth — "
    "but the brush bends sharply sideways, bristles pressing flat against his cheek. "
    "He blinks, pulls it back, tries again. Same bend, same cheek. "
    "He rotates the handle, aims from a new angle; the brush curves away like it's dodging. "
    "Frustrated, Kiko squeezes his eyes shut to concentrate. Instantly the brush "
    "straightens and lands on his teeth. Then one eye peeks open — the brush whips "
    "sideways to his cheek again, mid-stroke. Kiko slowly closes both eyes. "
    "The brush snaps back to his teeth. Final beat: the brush gives one tiny "
    "contented wiggle on his teeth."
)


def _outcomes(result):
    return {
        row["ruleId"]: row
        for group in ("passedRules", "failedRules", "unknownRules", "notApplicableRules")
        for row in result[group]
    }


def test_prose_story_does_not_fail_motion_or_uninspected_visual_gates_from_empty_timecodes():
    result = _run_canonical_evaluation({
        "prompt": STORY,
        "sourceId": "story:shy-bristles",
        "sourceVersion": "1",
        "contentProfile": "ABSURD_PHYSICS",
        "canonicalRulesetVersion": "1.12",
        "desiredDuration": 15,
        "validationStage": "STORY",
    })

    rules = _outcomes(result)
    assert result["status"] == "EVALUATED"
    assert result["validationStage"] == "STORY"
    assert result["videoPlanIR"]["beats"] == []
    assert result["storyNarrativeEvidence"]["progressionSignal"] is True
    for rule_id in ("CONCEPT_006", "ATTEMPT_001", "CHAR_002", "BEAT_DENSITY_RULE"):
        assert rules[rule_id]["outcome"] == "NOT_APPLICABLE"
        assert rules[rule_id]["details"]["requiredEvidence"] == "TIMECODED_MOTION_PLAN"
    for rule_id in ("INSTANT_VISUAL_ABSURDITY_GATE", "MINI_STORY_LOCK", "GOAL_VISIBLE_EARLY"):
        assert rules[rule_id]["outcome"] == "UNKNOWN"
        assert rules[rule_id]["details"]["requiredEvidence"] == "MOTION_PLAN_OR_VISUAL_REVIEW"


def test_timecoded_video_prompt_keeps_its_existing_canonical_evaluation_path():
    result = _run_canonical_evaluation({
        "prompt": "0.0-2.0 seconds: Kiko brushes his teeth while the brush bends away.",
        "sourceId": "motion:shy-bristles",
        "sourceVersion": "1",
        "contentProfile": "ABSURD_PHYSICS",
        "canonicalRulesetVersion": "1.12",
        "desiredDuration": 2,
        "validationStage": "VIDEO_PROMPT",
    })

    rules = _outcomes(result)
    assert result["validationStage"] == "VIDEO_PROMPT"
    assert rules["ATTEMPT_001"]["outcome"] != "NOT_APPLICABLE"
