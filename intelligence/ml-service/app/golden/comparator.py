from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..quality.canonical_evidence import mechanic_payoff_evidence, specialized_applicability_evidence


SPECIALIZED_APPLICABILITY_DIMENSIONS = {
    "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP": "STUBBORN_RETURN_LOOP",
    "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK": "STUBBORN_RETURN_HOOK",
    "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF": "STUBBORN_RETURN_PAYOFF",
}


@dataclass(frozen=True)
class AssertionComparison:
    classification: str
    expected: Any
    baseline: Any
    current: Any
    confidence: str | None = None
    is_new_semantic_regression: bool = False
    is_unexpected_policy_regression: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "expected": self.expected,
            "baseline": self.baseline,
            "current": self.current,
            "confidence": self.confidence,
            "isNewSemanticRegression": self.is_new_semantic_regression,
            "isUnexpectedPolicyRegression": self.is_unexpected_policy_regression,
            "message": self.message,
        }


def _matches(actual: Any, expected: Any, assertion_type: str) -> bool:
    if assertion_type in {"EXACT", "ENUM", "STATUS"}:
        if actual == expected:
            return True
        equivalent_pairs = {
            ("STRONG", "PASS"),
            ("PASS", "STRONG"),
            ("WEAK", "FAIL"),
            ("FAIL", "WEAK"),
        }
        return (str(actual), str(expected)) in equivalent_pairs
    if assertion_type == "COUNT":
        return actual == expected
    if assertion_type == "SET_EQUALS":
        return set(actual or ()) == set(expected or ())
    if assertion_type == "SET_CONTAINS":
        return set(expected or ()) <= set(actual or ())
    if assertion_type == "RANGE":
        return expected["min"] <= actual <= expected["max"]
    if assertion_type == "APPLICABILITY":
        return bool(actual) is bool(expected)
    if assertion_type == "EVIDENCE_EXISTS":
        return bool(actual) is bool(expected)
    raise ValueError(f"Unsupported Golden assertion type: {assertion_type}")


def compare_dimension(
    *,
    gold: dict[str, Any],
    baseline: dict[str, Any],
    current: dict[str, Any],
    assertion_type: str,
    known_issue: bool = False,
) -> AssertionComparison:
    if gold.get("applicable") is False:
        return AssertionComparison(
            classification="NOT_APPLICABLE",
            expected=gold.get("expected"),
            baseline=baseline.get("actual"),
            current=current.get("actual"),
            confidence=gold.get("confidence"),
            message="Gold Truth marks this dimension not applicable.",
        )
    expected = gold.get("expected")
    baseline_actual = baseline.get("actual")
    current_actual = current.get("actual")
    baseline_match = _matches(baseline_actual, expected, assertion_type)
    current_match = _matches(current_actual, expected, assertion_type)
    confidence = gold.get("confidence")
    if confidence in {"MEDIUM", "LOW"} and not current_match:
        return AssertionComparison(
            classification="GOLD_REVIEW_REQUIRED",
            expected=expected,
            baseline=baseline_actual,
            current=current_actual,
            confidence=confidence,
            message="Current output disagrees with a non-high-confidence Gold Truth label.",
        )
    if current_match and not baseline_match:
        classification = "IMPROVED_FROM_BASELINE"
    elif current_match:
        classification = "PASS"
    elif not baseline_match and known_issue and current_actual == baseline_actual:
        classification = "UNCHANGED_KNOWN_ISSUE"
    elif not baseline_match and current_actual != baseline_actual:
        classification = "REGRESSED_FROM_BASELINE"
    elif baseline_match:
        classification = "REGRESSED_FROM_BASELINE"
    else:
        classification = "FAIL"
    return AssertionComparison(
        classification=classification,
        expected=expected,
        baseline=baseline_actual,
        current=current_actual,
        confidence=confidence,
        is_new_semantic_regression=classification == "REGRESSED_FROM_BASELINE",
        message="Golden structural assertion comparison.",
    )


def compare_policy(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    expectation_updated: bool,
) -> AssertionComparison:
    baseline_value = baseline.get("creativeGrade")
    current_value = current.get("creativeGrade")
    if baseline_value == current_value:
        classification = "UNCHANGED"
    elif expectation_updated:
        classification = "EXPECTED_POLICY_CHANGE"
    else:
        classification = "UNEXPECTED_POLICY_REGRESSION"
    return AssertionComparison(
        classification=classification,
        expected=current_value,
        baseline=baseline_value,
        current=current_value,
        is_unexpected_policy_regression=classification == "UNEXPECTED_POLICY_REGRESSION",
        message="Policy output comparison is independent from structural Gold Truth.",
    )


@dataclass
class GoldenRegressionReport:
    new_semantic_regressions: int = 0
    unexpected_policy_regressions: int = 0
    assertions: list[AssertionComparison] = field(default_factory=list)

    @property
    def release_gate(self) -> str:
        return "PASS" if self.new_semantic_regressions == 0 and self.unexpected_policy_regressions == 0 else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "newSemanticRegressions": self.new_semantic_regressions,
            "unexpectedPolicyRegressions": self.unexpected_policy_regressions,
            "releaseGate": self.release_gate,
            "assertions": [item.to_dict() for item in self.assertions],
        }


def extract_dimension_values(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Project existing report evidence into comparator values; no new scoring logic."""
    stored = dict(snapshot.get("dimensionValues") or {})
    ir = snapshot.get("videoPlanIR")
    specialized_values: dict[str, Any] = {}
    canonical_specialized = (snapshot.get("canonicalEvidence") or {}).get("specializedApplicability") or {}
    for dimension, rule_id in SPECIALIZED_APPLICABILITY_DIMENSIONS.items():
        entry = canonical_specialized.get(rule_id)
        if isinstance(entry, dict) and entry.get("status") is not None:
            specialized_values[dimension] = entry["status"]

    if isinstance(ir, dict) and ir:
        recomputed = specialized_applicability_evidence(ir)
        for dimension, rule_id in SPECIALIZED_APPLICABILITY_DIMENSIONS.items():
            if dimension in specialized_values:
                continue
            evidence = recomputed.get(rule_id)
            status = getattr(evidence, "status", None)
            if status is not None:
                specialized_values[dimension] = status

    for dimension in SPECIALIZED_APPLICABILITY_DIMENSIONS:
        if dimension not in specialized_values and dimension in stored:
            specialized_values[dimension] = stored[dimension]

    if not isinstance(ir, dict) or not ir:
        return {**stored, **specialized_values}

    assessment = snapshot.get("assessment") or {}
    story = assessment.get("story_structure") or {}
    temporal = assessment.get("temporal_complexity") or {}
    canonical = snapshot.get("canonicalEvidence") or {}
    attempts = canonical.get("attempts") or {}
    dimensions = {item.get("key"): item.get("status") for item in assessment.get("dimensions", [])}
    mechanic_payoff = mechanic_payoff_evidence(ir)
    projected = {
        "HOOK": dimensions.get("OPENING_HOOK"),
        "GOAL": story.get("goal"),
        "CENTRAL_MECHANIC": mechanic_payoff.mechanic_family,
        "MECHANIC_INTERACTION": mechanic_payoff.interaction_status,
        "ACTIVE_ATTEMPT_COUNT": story.get("attempts", attempts.get("count")),
        "DISTINCT_STRATEGY_COUNT": story.get("distinct_strategies", len(set(attempts.get("strategyFamilies", [])))),
        "DISTINCT_STRATEGIES": attempts.get("strategyFamilies", []),
        "ESCALATION": dimensions.get("ESCALATION"),
        "PROGRESSION": dimensions.get("PROGRESSION"),
        "REALIZATION": story.get("realization"),
        "REALIZATION_MODE": story.get("realization_mode"),
        "FAKE_RESOLUTION": mechanic_payoff.fake_resolution_status,
        "PAYOFF": mechanic_payoff.payoff_status,
        "PAYOFF_RELATION": mechanic_payoff.same_rule_relation,
        "RECURRENCE": mechanic_payoff.recurrence_status,
        "LOOP": dimensions.get("LOOP_INTENT"),
        "CHARACTER_PERFORMANCE": dimensions.get("CHARACTER_PERFORMANCE_INTENT"),
        "PRODUCIBILITY": dimensions.get("PRODUCIBILITY"),
        "SOUND_OFF_READABILITY": dimensions.get("SOUND_OFF_READABILITY"),
        "TIMING_PACING": temporal.get("status"),
        "CONTENT_FAMILY_FIT": dimensions.get("CONTENT_FAMILY_FIT"),
        "FIRST_FRAME_ANOMALY_INTENT": (assessment.get("first_frame") or {}).get("textual_intent", {}).get("status"),
        "SPECIALIZED_RULE_APPLICABILITY": dimensions.get("ENGINE_PROFILE"),
        **specialized_values,
    }
    return {key: value if value is not None else stored.get(key) for key, value in projected.items()}


def compare_cohort(
    truth: dict[str, Any],
    baseline: dict[str, Any],
    current: dict[str, Any],
    policy_expectations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = []
    counts = {
        "passed": 0,
        "failed": 0,
        "improvedFromBaseline": 0,
        "unchangedKnownIssues": 0,
        "goldReviewRequired": 0,
        "newSemanticRegressions": 0,
        "expectedPolicyChanges": 0,
        "unexpectedPolicyRegressions": 0,
    }
    for asset_id, truth_asset in truth.get("assets", {}).items():
        baseline_asset = (baseline.get("assets") or {}).get(asset_id, {})
        current_asset = (current.get("assets") or {}).get(asset_id, {})
        baseline_values = extract_dimension_values(baseline_asset)
        current_values = extract_dimension_values(current_asset)
        known_issue = bool(baseline_asset.get("knownIssues"))
        for dimension, gold in (truth_asset.get("dimensions") or {}).items():
            if dimension == "SPECIALIZED_RULE_APPLICABILITY":
                continue
            if dimension in SPECIALIZED_APPLICABILITY_DIMENSIONS:
                rule_id = SPECIALIZED_APPLICABILITY_DIMENSIONS[dimension]
                comparison = compare_dimension(
                    gold=gold,
                    baseline={"actual": baseline_values.get(dimension)},
                    current={"actual": current_values.get(dimension)},
                    assertion_type="EXACT",
                    known_issue=known_issue,
                )
                assertions.append({
                    "assetId": asset_id,
                    "dimension": f"SPECIALIZED_RULE_APPLICABILITY:{rule_id}",
                    **comparison.to_dict(),
                })
                classification = comparison.classification
                if classification == "PASS":
                    counts["passed"] += 1
                elif classification == "FAIL":
                    counts["failed"] += 1
                elif classification == "IMPROVED_FROM_BASELINE":
                    counts["improvedFromBaseline"] += 1
                elif classification == "UNCHANGED_KNOWN_ISSUE":
                    counts["unchangedKnownIssues"] += 1
                elif classification == "GOLD_REVIEW_REQUIRED":
                    counts["goldReviewRequired"] += 1
                if comparison.is_new_semantic_regression:
                    counts["newSemanticRegressions"] += 1
                continue
            assertion_type = "SET_EQUALS" if dimension == "DISTINCT_STRATEGIES" else "EXACT"
            comparison = compare_dimension(
                gold=gold,
                baseline={"actual": baseline_values.get(dimension)},
                current={"actual": current_values.get(dimension)},
                assertion_type=assertion_type,
                known_issue=known_issue,
            )
            row = {"assetId": asset_id, "dimension": dimension, **comparison.to_dict()}
            assertions.append(row)
            classification = comparison.classification
            if classification == "PASS":
                counts["passed"] += 1
            elif classification == "FAIL":
                counts["failed"] += 1
            elif classification == "IMPROVED_FROM_BASELINE":
                counts["improvedFromBaseline"] += 1
            elif classification == "UNCHANGED_KNOWN_ISSUE":
                counts["unchangedKnownIssues"] += 1
            elif classification == "GOLD_REVIEW_REQUIRED":
                counts["goldReviewRequired"] += 1
            if comparison.is_new_semantic_regression:
                counts["newSemanticRegressions"] += 1
            if dimension == "REALIZATION" and gold.get("mode") is not None:
                mode_gold = dict(gold)
                mode_gold["expected"] = gold["mode"]
                mode_comparison = compare_dimension(
                    gold=mode_gold,
                    baseline={"actual": baseline_values.get("REALIZATION_MODE")},
                    current={"actual": current_values.get("REALIZATION_MODE")},
                    assertion_type="ENUM",
                    known_issue=known_issue,
                )
                assertions.append({"assetId": asset_id, "dimension": "REALIZATION_MODE", **mode_comparison.to_dict()})
                if mode_comparison.classification == "PASS":
                    counts["passed"] += 1
                elif mode_comparison.classification == "FAIL":
                    counts["failed"] += 1
                elif mode_comparison.classification == "IMPROVED_FROM_BASELINE":
                    counts["improvedFromBaseline"] += 1
                elif mode_comparison.classification == "UNCHANGED_KNOWN_ISSUE":
                    counts["unchangedKnownIssues"] += 1
                elif mode_comparison.classification == "GOLD_REVIEW_REQUIRED":
                    counts["goldReviewRequired"] += 1
                if mode_comparison.is_new_semantic_regression:
                    counts["newSemanticRegressions"] += 1
            if dimension == "PAYOFF" and gold.get("sameRuleRelation") is not None:
                relation_gold = dict(gold)
                relation_gold["expected"] = gold["sameRuleRelation"]
                relation_comparison = compare_dimension(
                    gold=relation_gold,
                    baseline={"actual": baseline_values.get("PAYOFF_RELATION")},
                    current={"actual": current_values.get("PAYOFF_RELATION")},
                    assertion_type="ENUM",
                    known_issue=known_issue,
                )
                assertions.append({"assetId": asset_id, "dimension": "PAYOFF_RELATION", **relation_comparison.to_dict()})
                if relation_comparison.classification == "PASS":
                    counts["passed"] += 1
                elif relation_comparison.classification == "FAIL":
                    counts["failed"] += 1
                elif relation_comparison.classification == "IMPROVED_FROM_BASELINE":
                    counts["improvedFromBaseline"] += 1
                elif relation_comparison.classification == "UNCHANGED_KNOWN_ISSUE":
                    counts["unchangedKnownIssues"] += 1
                elif relation_comparison.classification == "GOLD_REVIEW_REQUIRED":
                    counts["goldReviewRequired"] += 1
                if relation_comparison.is_new_semantic_regression:
                    counts["newSemanticRegressions"] += 1
        if policy_expectations:
            policy = (policy_expectations.get("assets") or {}).get(asset_id) or {}
            baseline_policy = _policy_projection(baseline_asset, baseline)
            current_policy = _policy_projection(current_asset, current)
            for policy_result in compare_policy_fields(
                policy,
                baseline=baseline_policy,
                current=current_policy,
            ):
                assertions.append({"assetId": asset_id, "dimension": "POLICY_OUTPUT", **policy_result.to_dict()})
                if policy_result.classification == "EXPECTED_POLICY_CHANGE":
                    counts["expectedPolicyChanges"] += 1
                if policy_result.is_unexpected_policy_regression:
                    counts["unexpectedPolicyRegressions"] += 1
    counts["releaseGate"] = "PASS" if counts["newSemanticRegressions"] == 0 and counts["unexpectedPolicyRegressions"] == 0 else "FAIL"
    return {**counts, "assertions": assertions}


def compare_policy_fields(
    policy: dict[str, Any],
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[AssertionComparison]:
    results: list[AssertionComparison] = []
    for field, specification in policy.items():
        if isinstance(specification, dict):
            if "expected" not in specification:
                continue
            expected = specification.get("expected")
            tolerance = specification.get("tolerance")
        else:
            expected = specification
            tolerance = None
        baseline_value = baseline.get(field)
        current_value = current.get(field)
        if baseline_value == current_value:
            classification = "UNCHANGED"
        elif isinstance(expected, (int, float)) and isinstance(current_value, (int, float)) and tolerance is not None and abs(current_value - expected) <= tolerance:
            classification = "EXPECTED_POLICY_CHANGE"
        elif current_value == expected:
            classification = "EXPECTED_POLICY_CHANGE"
        elif _policy_change_is_improvement(field, baseline_value, current_value):
            classification = "EXPECTED_POLICY_CHANGE"
        else:
            classification = "UNEXPECTED_POLICY_REGRESSION"
        results.append(
            AssertionComparison(
                classification=classification,
                expected=expected,
                baseline=baseline_value,
                current=current_value,
                is_unexpected_policy_regression=classification == "UNEXPECTED_POLICY_REGRESSION",
                message=f"Policy field: {field}",
            )
        )
    return results


def _policy_projection(asset: dict[str, Any], cohort: dict[str, Any]) -> dict[str, Any]:
    report = asset.get("report") or {}
    assessment = asset.get("assessment") or {}
    evaluations = report.get("evaluations") or []
    return {
        "creativeGrade": assessment.get("creative_grade"),
        "creativeScore": report.get("overallScore"),
        "evidenceCompleteness": assessment.get("assessment_coverage_percent"),
        "renderAuthorization": (assessment.get("render_authorization") or {}).get("status"),
        "blockers": sum(1 for item in evaluations if item.get("outcome") == "FAIL" and item.get("severity") == "BLOCKER"),
        "criticals": sum(1 for item in evaluations if item.get("outcome") == "FAIL" and item.get("severity") == "CRITICAL"),
        "warnings": sum(1 for item in evaluations if item.get("outcome") in {"FAIL", "PASS"} and item.get("severity") == "WARNING"),
        "unknowns": sum(1 for item in evaluations if item.get("outcome") == "UNKNOWN"),
        "notApplicable": sum(1 for item in evaluations if item.get("outcome") == "NOT_APPLICABLE"),
        "baselineStatus": asset.get("status"),
    }


def _policy_change_is_improvement(field: str, baseline: Any, current: Any) -> bool:
    if isinstance(baseline, (int, float)) and isinstance(current, (int, float)) and not isinstance(baseline, bool) and not isinstance(current, bool):
        if field in {"blockers", "criticals", "warnings", "unknowns", "notApplicable"}:
            return current < baseline
        return current > baseline
    if field == "creativeGrade" and isinstance(baseline, str) and isinstance(current, str):
        rank = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4, "INCOMPLETE": 5}
        return rank.get(current, 99) < rank.get(baseline, 99)
    if field == "renderAuthorization" and isinstance(baseline, str) and isinstance(current, str):
        rank = {
            "AUTHORIZED": 0,
            "BLOCKED_PENDING_EVIDENCE": 1,
            "HUMAN_REVIEW": 2,
            "BLOCKED_TECHNICAL_FAILURE": 3,
            "BLOCKED_CREATIVE_FAILURE": 4,
        }
        return rank.get(current, 99) < rank.get(baseline, 99)
    return False
