"""Long-form policy revision: attempts remain separate from story development."""
from copy import deepcopy

from app.config import settings
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager
from app.workflow.creative_roles import _story_plan_errors
from test_creative_roles import _structured_long_form_candidate


def engine(version="1.12"):
    return RuleEngine(str(settings.rules_dir / f"RULESET_{version}.yaml"))


def attempts_ir(duration, verbs):
    span = duration / len(verbs)
    beats = []
    for index, verb in enumerate(verbs):
        beats.append({
            "id": f"b{index}", "startTime": index * span, "endTime": (index + 1) * span,
            "duration": span, "isAttempt": True, "primaryVerb": verb,
            "action": f"Kiko {verb.lower()} the cup", "consequence": f"The cup changes state {index}",
        })
    return {"metadata": {"duration": float(duration)}, "beats": beats}


def rule(e, rule_id):
    return next(item for item in e.ruleset["rules"] if item["id"] == rule_id)


def test_22_second_story_with_three_attempts_is_not_rejected_for_seven(monkeypatch):
    e = engine()
    ir = attempts_ir(22, ["PULL", "TURN", "CATCH"])
    e._active_rule_id = "ATTEMPT_002"
    monkeypatch.setattr("app.rules.rule_engine.find_duplicate_strategy_pairs", lambda *_: [])
    assert e._evaluate_attempt_001(ir, rule(e, "ATTEMPT_001")).outcome is RuleOutcome.PASS
    assert e._evaluate_attempt_002(ir, rule(e, "ATTEMPT_002")).outcome is RuleOutcome.PASS
    assert rule(e, "ATTEMPT_001")["minimumAttemptsByTier"]["long"] == 3


def test_seven_repetitive_attempts_do_not_earn_distinct_attempt_pass():
    e = engine()
    ir = attempts_ir(30, ["PULL"] * 7)
    assert e._evaluate_attempt_001(ir, rule(e, "ATTEMPT_001")).outcome is RuleOutcome.PASS
    result = e._evaluate_attempt_002(ir, rule(e, "ATTEMPT_002"))
    assert result.outcome is RuleOutcome.FAIL
    assert result.actual_value == 1


def test_30_second_padding_fails_existing_removal_test_validation():
    candidate = _structured_long_form_candidate()
    candidate["text"] = candidate["text"].replace("20 seconds", "30 seconds").replace("16.0-20.0 SEC:", "16.0-30.0 SEC:")
    plan = candidate["storyPlan"]
    plan["recommendedRuntimeSeconds"] = 30
    plan["timecodedBeats"][-1]["endSeconds"] = 30
    plan["timecodedBeats"][-1]["sourceQuote"] = candidate["text"].splitlines()[-1]
    plan["durationJustification"]["meaningfulLossIfShortened"] = False
    assert "LONG_FORM_DURATION_NOT_JUSTIFIED" in _story_plan_errors(candidate, 30)


def test_existing_story_gate_failures_still_block():
    e = engine()
    ir = attempts_ir(22, ["PULL", "TURN", "CATCH"])
    ir["goalEvidence"] = {"goalExplicitness": "UNKNOWN"}
    result = e._evaluate_mini_story_lock(ir, rule(e, "MINI_STORY_LOCK"))
    assert result.outcome is RuleOutcome.FAIL


def test_historical_1_1_threshold_and_version_remain_traceable():
    manager = RuleVersionManager(settings.rules_dir)
    assert manager.get_latest_version() == "1.12"
    assert manager.get_version_info("1.1").ruleset_path == "RULESET_1.1.yaml"
    old = engine("1.1")
    new = engine("1.12")
    ir = attempts_ir(22, ["PULL", "TURN", "CATCH"])
    assert old._evaluate_attempt_001(ir, rule(old, "ATTEMPT_001")).outcome is RuleOutcome.FAIL
    assert rule(old, "ATTEMPT_001").get("minimumAttemptsByTier") is None
    assert new._evaluate_attempt_001(ir, rule(new, "ATTEMPT_001")).outcome is RuleOutcome.PASS
