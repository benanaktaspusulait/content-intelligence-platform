import pytest

from app.rules.rule_engine import RuleEngine, SemanticEvidenceUnavailable


def _engine(rule_id: str) -> RuleEngine:
    engine = RuleEngine.__new__(RuleEngine)
    engine.ruleset = {"semanticPolicy": "TARGETED_STORY_GATES"}
    engine._active_rule_id = rule_id
    return engine


@pytest.mark.parametrize("rule_id", ["GOAL_001", "ATTEMPT_002"])
def test_targeted_story_gates_can_use_existing_semantic_provider(rule_id: str) -> None:
    assert _engine(rule_id)._semantic_check(lambda: "evidence") == "evidence"


def test_other_semantic_rules_remain_provider_free() -> None:
    with pytest.raises(SemanticEvidenceUnavailable, match="TARGETED_STORY_GATES"):
        _engine("CONCEPT_007")._semantic_check(lambda: "must not dispatch")


def test_historical_provider_free_policy_remains_unchanged() -> None:
    engine = _engine("GOAL_001")
    engine.ruleset = {"semanticPolicy": "EXISTING_EVIDENCE_ONLY"}
    with pytest.raises(SemanticEvidenceUnavailable, match="provider dispatch is disabled"):
        engine._semantic_check(lambda: "must not dispatch")
