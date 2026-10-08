"""Versioned admission projection. Frozen evaluations are preserved as provenance."""
from dataclasses import replace
from typing import Any

from app.quality.contracts import QualityStatus, RuleEvaluation, RuleOutcome, Severity
from .review import review_prompt, binding_fingerprint

VERSION = "profile-admission-v1"
# Only mechanics-specific templates. Source, identity, safety, visual and producibility gates remain.
OPTIONAL_MECHANIC_RULES = frozenset({
    "CONCEPT_006", "ATTEMPT_001", "ATTEMPT_002", "CHAR_002", "HOOK_002", "HOOK_004",
    "ESCALATION_004", "ESCALATION_005", "PAYOFF_001", "PAYOFF_002", "PAYOFF_003",
    "PAYOFF_004", "PAYOFF_005", "PAYOFF_006", "PROGRESSION_005", "PROGRESSION_006",
    "REPETITION_004", "GOAL_001", "CONCEPT_008",
})


def project_admission(report: Any, engine: Any, request: dict[str, Any], capabilities: dict[str, Any]):
    if request.get("profile") != "post-family-v1":
        raise ValueError("Explicit operational profile required")
    reviewed = review_prompt(request, capabilities)
    profile = reviewed["routing"]["contentProfile"]
    rows = []
    for original in report.evaluations:
        if profile in {"CURIOSITY_ADVENTURE", "EDUCATIONAL"} and original.rule_id in OPTIONAL_MECHANIC_RULES:
            rows.append(replace(original, outcome=RuleOutcome.NOT_APPLICABLE,
                message=f"{VERSION}: physical-attempt template is not mandatory for {profile}",
                details={**original.details, "profileAdmission": {
                    "version": VERSION, "contentProfile": profile, "originalOutcome": original.outcome.value,
                    "originalMessage": original.message, "bindingFingerprint": binding_fingerprint(request),
                }}))
        else:
            rows.append(original)
    quality = reviewed["planQuality"]["status"]
    risk = reviewed["executionRisk"]["status"]
    unknown = profile in {"UNKNOWN", "MIXED"} or quality == "UNKNOWN" or risk == "UNKNOWN" or reviewed["generalProducibility"]["status"] == "UNKNOWN" or any(i["status"] == "UNKNOWN" for i in reviewed["intentRequirements"])
    failed = quality in {"FAIL", "BLOCK"} or risk in {"FAIL", "BLOCK"}
    rows.append(RuleEvaluation(rule_id="PROFILE_SOURCE_IMPACT", rule_name="Source-bound intent and execution", family="profile_admission",
        outcome=RuleOutcome.FAIL if failed else RuleOutcome.UNKNOWN if unknown else RuleOutcome.PASS,
        configured_severity=Severity.BLOCKER, message="Source-bound operational plan and execution evidence",
        details={"planQuality": reviewed["planQuality"], "executionRisk": reviewed["executionRisk"], "intentRequirements": reviewed["intentRequirements"]}))
    families = engine._calculate_family_scores(rows)
    score = engine._calculate_overall_score(families, rows)
    pending = any(r.outcome in {RuleOutcome.UNKNOWN, RuleOutcome.SERVICE_ERROR} for r in rows)
    blockers = any(r.outcome == RuleOutcome.FAIL for r in rows)
    decision = QualityStatus.BLOCKED if blockers else QualityStatus.NEEDS_REVISION if pending or score is None else QualityStatus.RENDER_READY
    projected = replace(report, evaluations=tuple(rows), family_scores=families,
        family_assessments=engine._calculate_family_assessments(rows), overall_score=score, status=decision,
        ruleset_version=f"{report.ruleset_version}+{VERSION}:{binding_fingerprint(request)}")
    metadata = {"version": VERSION, "contentProfile": profile, "bindingFingerprint": binding_fingerprint(request),
        "workflowBindingHash": reviewed["bindingHash"], "boundRequest": request,
        "frozenStatus": report.status.value, "frozenBlockerCount": report.blocker_count,
        "frozenCriticalCount": report.critical_count,
        "rows": [{"ruleId": r.rule_id, "outcome": r.outcome.value, "reason": r.message} for r in rows],
        "requiredEvidencePreserved": True}
    return projected, metadata
