from __future__ import annotations

from app.golden.comparator import (
    GoldenRegressionReport,
    compare_dimension,
    compare_policy,
)


def test_strategy_improvement_is_not_a_new_regression() -> None:
    result = compare_dimension(
        gold={"expected": ["PULL", "TEST"], "confidence": "HIGH"},
        baseline={"actual": ["PULL", "CATCH"]},
        current={"actual": ["PULL", "TEST"]},
        assertion_type="SET_EQUALS",
    )
    assert result.classification == "IMPROVED_FROM_BASELINE"
    assert result.is_new_semantic_regression is False


def test_unchanged_known_issue_is_not_new_regression() -> None:
    result = compare_dimension(
        gold={"expected": "STRONG", "confidence": "HIGH"},
        baseline={"actual": "FAIL"},
        current={"actual": "FAIL"},
        known_issue=True,
        assertion_type="ENUM",
    )
    assert result.classification == "UNCHANGED_KNOWN_ISSUE"
    assert result.is_new_semantic_regression is False


def test_policy_only_change_is_expected_when_policy_version_changed() -> None:
    result = compare_policy(
        baseline={"creativeGrade": "B", "rulesetVersion": "1.7"},
        current={"creativeGrade": "C", "rulesetVersion": "1.8"},
        expectation_updated=True,
    )
    assert result.classification == "EXPECTED_POLICY_CHANGE"
    assert result.is_unexpected_policy_regression is False


def test_release_gate_requires_zero_new_and_unexpected_regressions() -> None:
    assert GoldenRegressionReport(new_semantic_regressions=1, unexpected_policy_regressions=0).release_gate == "FAIL"
    assert GoldenRegressionReport(new_semantic_regressions=0, unexpected_policy_regressions=1).release_gate == "FAIL"
    assert GoldenRegressionReport(new_semantic_regressions=0, unexpected_policy_regressions=0).release_gate == "PASS"


def test_cohort_comparison_reports_known_issue_and_release_metrics() -> None:
    from app.golden.comparator import compare_cohort

    truth = {
        "assets": {
            "asset-1": {
                "dimensions": {
                    "DISTINCT_STRATEGIES": {
                        "expected": ["PULL", "TEST"],
                        "applicable": True,
                        "confidence": "HIGH",
                        "evidenceReferences": [{"excerpt": "pull / squeeze"}],
                        "notes": "",
                    }
                }
            }
        }
    }
    baseline = {"assets": {"asset-1": {"dimensionValues": {"DISTINCT_STRATEGIES": ["PULL", "CATCH"]}, "knownIssues": [{"code": "STRATEGY_BASELINE"}]}}}
    current = {"assets": {"asset-1": {"dimensionValues": {"DISTINCT_STRATEGIES": ["PULL", "TEST"]}, "knownIssues": []}}}
    result = compare_cohort(truth, baseline, current)
    assert result["newSemanticRegressions"] == 0
    assert result["improvedFromBaseline"] == 1
    assert result["releaseGate"] == "PASS"


def test_known_issue_does_not_suppress_an_unrelated_changed_dimension() -> None:
    from app.golden.comparator import compare_cohort

    truth = {
        "assets": {
            "asset-1": {
                "dimensions": {
                    "HOOK": {
                        "expected": "STRONG",
                        "applicable": True,
                        "confidence": "HIGH",
                        "evidenceReferences": [{"excerpt": "hook"}],
                        "notes": "",
                    }
                }
            }
        }
    }
    baseline = {"assets": {"asset-1": {"dimensionValues": {"HOOK": "FAIL"}, "knownIssues": [{"code": "TIMELINE_PARSE_INCOMPATIBLE"}]}}}
    current = {"assets": {"asset-1": {"dimensionValues": {"HOOK": "NEEDS_ATTENTION"}, "knownIssues": [{"code": "TIMELINE_PARSE_INCOMPATIBLE"}]}}}
    result = compare_cohort(truth, baseline, current)
    assert result["unchangedKnownIssues"] == 0
    assert result["newSemanticRegressions"] == 1
    assert result["releaseGate"] == "FAIL"


def test_policy_comparison_covers_declared_policy_fields() -> None:
    from app.golden.comparator import compare_policy_fields

    policy = {
        "creativeGrade": {"expected": "C"},
        "creativeScore": {"expected": 70.0, "tolerance": 0.01},
        "evidenceCompleteness": {"expected": 90},
        "renderAuthorization": {"expected": "AUTHORIZED"},
        "baselineStatus": "OK",
    }
    result = compare_policy_fields(
        policy,
        baseline={"creativeGrade": "B", "creativeScore": 80.0, "evidenceCompleteness": 90, "renderAuthorization": "AUTHORIZED", "baselineStatus": "OK"},
        current={"creativeGrade": "C", "creativeScore": 70.0, "evidenceCompleteness": 90, "renderAuthorization": "AUTHORIZED", "baselineStatus": "PARSER_TIMEOUT"},
    )
    assert len(result) == 5
    assert any(item.classification == "EXPECTED_POLICY_CHANGE" for item in result)
    assert any(item.message == "Policy field: baselineStatus" and item.is_unexpected_policy_regression for item in result)
