"""Safety-boundary tests for offline production validation."""

import pytest

from app.config import settings
from app.rules.rule_engine import RuleEngine, SemanticEvidenceUnavailable


@pytest.mark.parametrize(
    ("offline", "authorized"), [("true", "true"), ("false", "false")]
)
def test_nested_semantic_dispatch_is_not_evaluated_without_authorization(
    monkeypatch, offline: str, authorized: str
) -> None:
    engine = RuleEngine(str(settings.rules_dir / "RULESET_1.12.yaml"))
    monkeypatch.setenv("POMPOM_OFFLINE_MODE", offline)
    monkeypatch.setenv("POMPOM_EXTERNAL_AI_AUTHORIZED", authorized)

    def nested_call():
        pytest.fail("Nested semantic provider call must be denied before dispatch")

    with pytest.raises(SemanticEvidenceUnavailable, match="NOT_EVALUATED"):
        engine._semantic_check(nested_call)
