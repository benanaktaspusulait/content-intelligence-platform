from unittest.mock import patch
from app.quality.contracts import QualityReport, QualityStatus, RuleEvaluation, RuleOutcome, Severity
from app.rules.rule_engine import RuleEngine
from app.workflow.admission import project_admission
from app.workflow.review import PROFILE_ADMISSION_VERSION, PROFILE_OPTIONAL_RULES, PROFILE_SHARED_RULES, apply_profile_rule_exclusions


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
    assert f"+{PROFILE_ADMISSION_VERSION}:" in projected.ruleset_version


def test_actual_safety_and_visual_failures_remain_blocked():
    for rule in ("CONSISTENCY_001", "PRODUCIBILITY_001", "ENGINE_SILHOUETTE_DUPLICATE"):
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


def test_curiosity_waives_physics_mechanic_but_keeps_shared_story_gates():
    original, projected, _ = project([
        row("CONCEPT_007", RuleOutcome.FAIL),
        row("HOOK_004", RuleOutcome.FAIL),
        row("PROGRESSION_006", RuleOutcome.FAIL),
        row("PAYOFF_001", RuleOutcome.FAIL),
    ])
    outcomes = {item.rule_id: item.outcome for item in projected.evaluations}
    assert outcomes["CONCEPT_007"] == RuleOutcome.NOT_APPLICABLE
    assert outcomes["HOOK_004"] == RuleOutcome.FAIL
    assert outcomes["PROGRESSION_006"] == RuleOutcome.FAIL
    assert outcomes["PAYOFF_001"] == RuleOutcome.FAIL
    assert projected.status == QualityStatus.BLOCKED
    assert original.evaluations[0].outcome == RuleOutcome.FAIL


def test_profile_specific_physics_checks_are_excluded_before_dispatch_only_for_mystery():
    from app.config import settings

    curiosity = RuleEngine(settings.rules_dir / "RULESET_1.12.yaml")
    apply_profile_rule_exclusions(curiosity, "CURIOSITY_ADVENTURE")
    concept_rule = next(rule for rule in curiosity.ruleset["rules"] if rule["id"] == "CONCEPT_007")
    absurdity_rule = next(rule for rule in curiosity.ruleset["rules"] if rule["id"] == "INSTANT_VISUAL_ABSURDITY_GATE")
    shared_rule = next(rule for rule in curiosity.ruleset["rules"] if rule["id"] == "HOOK_004")
    assert not curiosity._rule_applies(concept_rule, {"metadata": {"contentProfile": "CURIOSITY_ADVENTURE"}})
    assert not curiosity._rule_applies(absurdity_rule, {"metadata": {"contentProfile": "CURIOSITY_ADVENTURE"}})
    for rule_id in ("CONCEPT_009", "STUBBORN_RETURN_LOOP", "STUBBORN_RETURN_HOOK", "STUBBORN_RETURN_PAYOFF"):
        profile_rule = next(rule for rule in curiosity.ruleset["rules"] if rule["id"] == rule_id)
        assert not curiosity._rule_applies(profile_rule, {"metadata": {"contentProfile": "CURIOSITY_ADVENTURE", "seriesType": "social_reel"}})
    assert curiosity._rule_applies(shared_rule, {"metadata": {"contentProfile": "CURIOSITY_ADVENTURE"}})

    physics = RuleEngine(settings.rules_dir / "RULESET_1.12.yaml")
    apply_profile_rule_exclusions(physics, "ABSURD_PHYSICS")
    physics_rule = next(rule for rule in physics.ruleset["rules"] if rule["id"] == "CONCEPT_007")
    physics_absurdity_rule = next(rule for rule in physics.ruleset["rules"] if rule["id"] == "INSTANT_VISUAL_ABSURDITY_GATE")
    assert physics._rule_applies(physics_rule, {"metadata": {"contentProfile": "ABSURD_PHYSICS"}})
    assert physics._rule_applies(physics_absurdity_rule, {"metadata": {"contentProfile": "ABSURD_PHYSICS"}})
    for rule_id in ("CONCEPT_009", "STUBBORN_RETURN_LOOP", "STUBBORN_RETURN_HOOK", "STUBBORN_RETURN_PAYOFF"):
        profile_rule = next(rule for rule in physics.ruleset["rules"] if rule["id"] == rule_id)
        assert physics._rule_applies(profile_rule, {"metadata": {"contentProfile": "ABSURD_PHYSICS", "seriesType": "social_reel"}})


def test_shared_legibility_goal_and_progression_gates_are_not_profile_optional():
    assert {"HOOK_004", "PROGRESSION_006", "PAYOFF_001"} == PROFILE_SHARED_RULES
    assert not PROFILE_SHARED_RULES & PROFILE_OPTIONAL_RULES
    assert {"CONCEPT_007", "CONCEPT_008", "GOAL_001", "CONCEPT_009", "INSTANT_VISUAL_ABSURDITY_GATE"} <= PROFILE_OPTIONAL_RULES
    assert {"STUBBORN_RETURN_LOOP", "STUBBORN_RETURN_HOOK", "STUBBORN_RETURN_PAYOFF"} <= PROFILE_OPTIONAL_RULES
