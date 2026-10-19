"""Versioned admission projection. Frozen evaluations are preserved as provenance."""
from dataclasses import replace
from typing import Any

from app.quality.contracts import QualityStatus, RuleEvaluation, RuleOutcome, Severity
from .review import (
    PROFILE_ADMISSION_VERSION,
    PROFILE_OPTIONAL_RULES,
    binding_fingerprint,
    review_prompt,
)

VERSION = PROFILE_ADMISSION_VERSION


def project_admission(report: Any, engine: Any, request: dict[str, Any], capabilities: dict[str, Any]):
    if request.get("profile") != "post-family-v1":
        raise ValueError("Explicit operational profile required")
    reviewed = review_prompt(request, capabilities)
    profile = reviewed["routing"]["contentProfile"]
    rows = []
    for original in report.evaluations:
        if profile in {"CURIOSITY_ADVENTURE", "EDUCATIONAL"} and original.rule_id in PROFILE_OPTIONAL_RULES:
            rows.append(replace(original, outcome=RuleOutcome.NOT_APPLICABLE,
                message=f"{VERSION}: physical-rule template is not mandatory for {profile}",
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
