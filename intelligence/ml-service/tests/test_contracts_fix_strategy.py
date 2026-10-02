"""PAYOFF_003 and CONSISTENCY_002 are semantic/visual judgment calls with no
automated patch — they must route to HUMAN_REVIEW, not the CONTROLLED_PATCH
default."""

from app.quality.contracts import FixStrategy, strategy_for_rule


def test_payoff_003_routes_to_human_review() -> None:
    assert strategy_for_rule("PAYOFF_003") is FixStrategy.HUMAN_REVIEW


def test_consistency_002_routes_to_human_review() -> None:
    assert strategy_for_rule("CONSISTENCY_002") is FixStrategy.HUMAN_REVIEW


def test_producibility_001_still_routes_to_human_review() -> None:
    """Regression guard: existing HUMAN_REVIEW rule must be unaffected."""
    assert strategy_for_rule("PRODUCIBILITY_001") is FixStrategy.HUMAN_REVIEW


def test_concept_006_still_routes_to_replace_concept() -> None:
    """Regression guard: existing REPLACE_CONCEPT rule must be unaffected."""
    assert strategy_for_rule("CONCEPT_006") is FixStrategy.REPLACE_CONCEPT


def test_unlisted_rule_defaults_to_controlled_patch() -> None:
    assert strategy_for_rule("HOOK_002") is FixStrategy.CONTROLLED_PATCH
