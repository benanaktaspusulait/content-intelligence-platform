"""Integration checks for the immutable RULESET_1.4 successor."""

from app.config import settings
from app.rules.rule_engine import RuleEngine
from app.rules.rule_versioning import RuleVersionManager

NEW_RULE_IDS = {
    "CONTINUOUS_ACTION_MOMENTUM",
    "INSTANT_VISUAL_ABSURDITY_GATE",
    "ENGINE_SILHOUETTE_DUPLICATE",
}


def test_ruleset_1_4_remains_registered_at_its_original_path() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    assert manager.get_version_info("1.4").ruleset_path == "RULESET_1.4.yaml"


def test_ruleset_1_4_contains_the_three_new_rules_and_summary() -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.4.yaml"))
    rule_ids = {rule["id"] for rule in engine.ruleset["rules"]}
    assert NEW_RULE_IDS <= rule_ids
    assert len(rule_ids) == 37
    assert engine.ruleset["ruleset_summary"]["total_rules"] == 37


def test_ruleset_1_3_remains_unchanged_and_comparison_is_additive() -> None:
    manager = RuleVersionManager(settings.rules_dir)
    comparison = manager.compare_versions("1.3", "1.4")
    assert set(comparison.new_rules) == NEW_RULE_IDS
    assert comparison.removed_rules == []
    assert comparison.is_backward_compatible is False
