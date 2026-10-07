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


def test_realization_mode_is_a_comparator_assertion_and_mutation_fails_gate() -> None:
    from app.golden.comparator import compare_cohort

    truth = {
        "assets": {
            "asset-1": {
                "dimensions": {
                    "REALIZATION": {
                        "expected": "AVAILABLE",
                        "mode": "IMPLICIT_BUT_OBSERVABLE",
                        "applicable": True,
                        "confidence": "HIGH",
                        "evidenceReferences": [{"excerpt": "object becomes normal; character relaxes"}],
                        "notes": "",
                    }
                }
            }
        }
    }
    baseline = {"assets": {"asset-1": {"dimensionValues": {"REALIZATION": "AVAILABLE", "REALIZATION_MODE": "IMPLICIT_BUT_OBSERVABLE"}, "knownIssues": []}}}
    current = {"assets": {"asset-1": {"dimensionValues": {"REALIZATION": "AVAILABLE", "REALIZATION_MODE": "IMPLICIT_BUT_OBSERVABLE"}, "knownIssues": []}}}
    passing = compare_cohort(truth, baseline, current)
    assert any(row["dimension"] == "REALIZATION_MODE" and row["classification"] == "PASS" for row in passing["assertions"])
    assert passing["newSemanticRegressions"] == 0

    current["assets"]["asset-1"]["dimensionValues"]["REALIZATION_MODE"] = "EXPLICIT"
    failing = compare_cohort(truth, baseline, current)
    mode_rows = [row for row in failing["assertions"] if row["dimension"] == "REALIZATION_MODE"]
    assert mode_rows[0]["classification"] == "REGRESSED_FROM_BASELINE"
    assert failing["newSemanticRegressions"] == 1
    assert failing["releaseGate"] == "FAIL"


def test_family4_projection_prefers_canonical_evidence_and_falls_back_for_unavailable_fields() -> None:
    from app.golden.comparator import extract_dimension_values

    ir = {
        "coreMechanic": {"physicalRule": "The sticky ball sticks to surfaces."},
        "beats": [
            {
                "beatRole": "ATTEMPT",
                "action": "Mimi pulls the sticky ball",
                "consequence": "it sticks to the table",
                "consequenceType": "new",
            },
            {
                "beatRole": "FAKE_RESOLUTION",
                "action": "Mimi relaxes",
                "consequence": "the ball behaves normally",
                "consequenceType": "fake_win",
            },
            {
                "beatRole": "TWIST",
                "action": "the sticky ball returns",
                "consequence": "it sticks again",
                "consequenceType": "new",
            },
        ],
        "finalPayoff": {"description": "The sticky ball sticks to the entire wall."},
    }
    snapshot = {
        "status": "OK",
        "videoPlanIR": ir,
        "dimensionValues": {
            "HOOK": "STORED_HOOK",
            "CENTRAL_MECHANIC": "stale mechanic",
            "MECHANIC_INTERACTION": "stale interaction",
            "FAKE_RESOLUTION": "OPTIONAL",
            "RECURRENCE": "NOT_ESTABLISHED",
            "PAYOFF": "AVAILABLE",
            "PAYOFF_RELATION": "NOT_ESTABLISHED",
        },
    }

    values = extract_dimension_values(snapshot)

    assert values["HOOK"] == "STORED_HOOK"
    assert values["CENTRAL_MECHANIC"] == "STICKY_DEFORMATION"
    assert values["MECHANIC_INTERACTION"] == "ACTIVE"
    assert values["FAKE_RESOLUTION"] == "PRESENT"
    assert values["RECURRENCE"] == "PRESENT"
    assert values["PAYOFF"] == "STRONG"
    assert values["PAYOFF_RELATION"] == "SAME_RULE"


def test_extract_dimension_values_preserves_stored_values_without_video_plan_ir() -> None:
    from app.golden.comparator import extract_dimension_values

    stored = {
        "HOOK": "STORED_HOOK",
        "CENTRAL_MECHANIC": "STORED_MECHANIC",
        "MECHANIC_INTERACTION": "STORED_INTERACTION",
        "FAKE_RESOLUTION": "STORED_FAKE",
        "RECURRENCE": "STORED_RECURRENCE",
        "PAYOFF": "STORED_PAYOFF",
        "PAYOFF_RELATION": "STORED_RELATION",
    }

    for snapshot in (
        {"status": "PARSER_TIMEOUT", "videoPlanIR": None, "dimensionValues": stored},
        {"status": "OK", "videoPlanIR": None, "dimensionValues": stored},
    ):
        assert extract_dimension_values(snapshot) == stored
