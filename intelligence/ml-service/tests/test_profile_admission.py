from unittest.mock import patch
from app.quality.contracts import QualityReport, QualityStatus, RuleEvaluation, RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine
from app.workflow.admission import project_admission


def row(rule, outcome=RuleOutcome.FAIL):
    return RuleEvaluation(rule, rule, "concept_strength", outcome, Severity.BLOCKER, "Frozen result")


def source_review(profile="CURIOSITY_ADVENTURE", quality="PASS"):
    return {"routing": {"contentProfile": profile}, "planQuality": {"status": quality}, "executionRisk": {"status": "PASS"}, "generalProducibility": {"status": "LOW"}, "intentRequirements": [], "bindingHash": "a" * 64}


def project(rows, review=None):
    original = QualityReport(50, QualityStatus.BLOCKED, {}, tuple(rows), "1.7", "fixture")
    from app.config import settings
    engine = RuleEngine(settings.rules_dir / "RULESET_1.0.yaml")
    request = {"profile": "post-family-v1", "prompt": "Source fixture", "sourceId": "content:1", "sourceVersion": "1"}
    with patch("app.workflow.admission.review_prompt", return_value=review or source_review()):
        projected, provenance = project_admission(original, engine, request, {})
    return original, projected, provenance


def test_curiosity_optional_attempts_do_not_erase_frozen_results():
    original, projected, metadata = project([row("ATTEMPT_001"), row("CONSISTENCY_001", RuleOutcome.PASS)])
    assert original.blocker_count == 1 and original.evaluations[0].outcome == RuleOutcome.FAIL
    assert projected.evaluations[0].outcome == RuleOutcome.NOT_APPLICABLE
    assert projected.status == QualityStatus.RENDER_READY
    assert metadata["frozenBlockerCount"] == 1 and metadata["requiredEvidencePreserved"]
    assert "+profile-admission-v1:" in projected.ruleset_version


def test_actual_safety_and_visual_failures_remain_blocked():
    for rule in ("CONSISTENCY_001", "PRODUCIBILITY_001", "INSTANT_VISUAL_ABSURDITY_GATE", "ENGINE_SILHOUETTE_DUPLICATE"):
        _, projected, _ = project([row("ATTEMPT_001"), row(rule)])
        assert projected.status == QualityStatus.BLOCKED
        assert projected.blocker_count >= 1


def test_unknown_evidence_and_essential_intent_cannot_authorize():
    _, projected, _ = project([row("ATTEMPT_001"), row("CONSISTENCY_001", RuleOutcome.UNKNOWN)])
    assert projected.status == QualityStatus.NEEDS_REVISION
    _, projected, _ = project([row("ATTEMPT_001")], source_review(quality="FAIL"))
    assert projected.status == QualityStatus.BLOCKED


def test_absurd_and_unknown_profiles_do_not_waive_required_attempt_template():
    for profile in ("ABSURD_PHYSICS", "UNKNOWN"):
        _, projected, _ = project([row("ATTEMPT_001")], source_review(profile))
        assert projected.evaluations[0].outcome == RuleOutcome.FAIL
        assert projected.status == QualityStatus.BLOCKED
