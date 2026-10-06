"""Focused coverage for the scoped RULESET_1.5 concept gate."""

from unittest.mock import patch

from app.config import settings
from app.llm.semantic_checks import SemanticCheckServiceError
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager


def ir(primary="Kiko", obj="umbrella", carrier="OBJECT_INTERACTION", participants=None, series="social_reel"):
    return {
        "metadata": {"duration": 15, "seriesType": series},
        "characters": {"primary": primary, "secondary": ["Flying Boy"]},
        "coreMechanic": {
            "physicalRule": "The object behaves impossibly.",
            "causeEffect": "Character touches the object and the object causes the consequence.",
            "primaryObject": obj,
            "mechanicCarrier": carrier,
            "causalParticipants": participants if participants is not None else [primary],
        },
        "beats": [],
    }


def evaluator():
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.5.yaml"))
    return engine, engine.ruleset["rules"][-1]


def test_object_owned_mechanic_passes_and_background_character_is_ignored():
    engine, rule = evaluator()
    result = engine._evaluate_concept_009(ir(obj="umbrella"), rule)
    assert result.outcome is RuleOutcome.PASS
    assert result.details["causalParticipants"] == ["Kiko"]


def test_second_character_that_steals_or_solves_the_object_mechanic_fails():
    engine, rule = evaluator()
    result = engine._evaluate_concept_009(ir(obj="sticky ball", participants=["Luca", "Child"]), rule)
    assert result.outcome is RuleOutcome.FAIL
    assert result.configured_severity.value == "BLOCKER"


def test_multi_agent_carrier_fails_even_with_one_named_object():
    engine, rule = evaluator()
    result = engine._evaluate_concept_009(
        ir(primary="Luca", obj="ball", carrier="MULTI_AGENT", participants=["Luca", "Child"]), rule
    )
    assert result.outcome is RuleOutcome.FAIL


def test_mimi_and_self_refilling_cup_is_a_valid_object_mechanic():
    engine, rule = evaluator()
    result = engine._evaluate_concept_009(ir(primary="Mimi", obj="self-refilling cup"), rule)
    assert result.outcome is RuleOutcome.PASS


def test_other_content_families_are_not_applicable():
    engine, rule = evaluator()
    result = engine.evaluate(ir(series="whats_wrong"))
    scoped = next(item for item in result.evaluations if item.rule_id == "CONCEPT_009")
    assert scoped.outcome is RuleOutcome.NOT_APPLICABLE


def test_missing_explicit_evidence_is_unknown_when_semantic_judgment_is_ambiguous():
    engine, rule = evaluator()
    plan = ir()
    del plan["coreMechanic"]["primaryObject"]
    del plan["coreMechanic"]["mechanicCarrier"]
    del plan["coreMechanic"]["causalParticipants"]
    with patch("app.rules.rule_engine.check_single_agent_object_mechanic", return_value=(
        {"reasoning": "The causal structure is not clear."}, "UNKNOWN"
    )):
        result = engine._evaluate_concept_009(plan, rule)
    assert result.outcome is RuleOutcome.UNKNOWN


def test_semantic_provider_failure_is_service_error():
    engine, rule = evaluator()
    plan = ir()
    del plan["coreMechanic"]["primaryObject"]
    del plan["coreMechanic"]["mechanicCarrier"]
    del plan["coreMechanic"]["causalParticipants"]
    with patch(
        "app.rules.rule_engine.check_single_agent_object_mechanic",
        side_effect=SemanticCheckServiceError("provider unavailable"),
    ):
        result = engine._evaluate_concept_009(plan, rule)
    assert result.outcome is RuleOutcome.SERVICE_ERROR


def test_blocker_failure_blocks_render_authorization():
    engine, rule = evaluator()
    scoped = engine._evaluate_concept_009(
        ir(primary="Kiko", obj="flying boy", carrier="SECONDARY_AGENT", participants=["Kiko", "Flying Boy"]), rule
    )
    result = engine._generate_report([scoped], ir())
    assert scoped.outcome is RuleOutcome.FAIL
    assert result.status.value == "BLOCKED"


def test_ruleset_1_4_and_1_5_remain_immutable_with_1_6_latest():
    manager = RuleVersionManager(settings.rules_dir)
    assert manager.get_latest_version() == "1.6"
    old = RuleEngine(str(settings.rules_dir / "RULESET_1.4.yaml"))
    stable = RuleEngine(str(settings.rules_dir / "RULESET_1.5.yaml"))
    latest = RuleEngine(str(settings.rules_dir / "RULESET_1.6.yaml"))
    assert "CONCEPT_009" not in {rule["id"] for rule in old.ruleset["rules"]}
    assert "CONCEPT_009" in {rule["id"] for rule in stable.ruleset["rules"]}
    assert "MINI_STORY_LOCK" not in {rule["id"] for rule in stable.ruleset["rules"]}
    assert "MINI_STORY_LOCK" in {rule["id"] for rule in latest.ruleset["rules"]}
    comparison = manager.compare_versions("1.4", "1.5")
    assert comparison.new_rules == ["CONCEPT_009"]
    assert comparison.removed_rules == []
