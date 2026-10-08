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


def test_release_gate_requires_zero_new_unexpected_and_representation_regressions() -> None:
    assert GoldenRegressionReport(new_semantic_regressions=1, unexpected_policy_regressions=0).release_gate == "FAIL"
    assert GoldenRegressionReport(new_semantic_regressions=0, unexpected_policy_regressions=1).release_gate == "FAIL"
    assert GoldenRegressionReport(representation_mismatches=1).release_gate == "FAIL"
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


def test_family5_comparator_emits_one_assertion_per_specialized_rule() -> None:
    import copy

    from app.golden.comparator import compare_cohort

    truth = {"assets": {"asset-1": {"dimensions": {
        "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP": {
            "expected": "APPLICABLE", "applicable": True, "confidence": "HIGH"
        },
        "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK": {
            "expected": "UNKNOWN", "applicable": True, "confidence": "HIGH"
        },
        "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF": {
            "expected": "APPLICABLE", "applicable": True, "confidence": "HIGH"
        },
    }}}}
    baseline = {"assets": {"asset-1": {
        "videoPlanIR": {"metadata": {"duration": 15.0}},
        "canonicalEvidence": {"specializedApplicability": {
            "STUBBORN_RETURN_LOOP": {"status": "APPLICABLE"},
            "STUBBORN_RETURN_HOOK": {"status": "UNKNOWN"},
            "STUBBORN_RETURN_PAYOFF": {"status": "APPLICABLE"},
        }},
    }}}
    current = copy.deepcopy(baseline)
    current["assets"]["asset-1"]["canonicalEvidence"]["specializedApplicability"]["STUBBORN_RETURN_HOOK"]["status"] = "NOT_APPLICABLE"

    result = compare_cohort(truth, baseline, current)

    rows = [row for row in result["assertions"] if row["dimension"].startswith("SPECIALIZED_RULE_APPLICABILITY:")]
    assert len(rows) == 3
    assert {row["dimension"] for row in rows} == {
        "SPECIALIZED_RULE_APPLICABILITY:STUBBORN_RETURN_LOOP",
        "SPECIALIZED_RULE_APPLICABILITY:STUBBORN_RETURN_HOOK",
        "SPECIALIZED_RULE_APPLICABILITY:STUBBORN_RETURN_PAYOFF",
    }
    assert next(row for row in rows if row["dimension"].endswith("HOOK"))["classification"] == "REGRESSED_FROM_BASELINE"
    assert result["newSemanticRegressions"] == 1
    assert result["releaseGate"] == "FAIL"


def test_family5_medium_confidence_mismatch_requires_gold_review() -> None:
    result = compare_dimension(
        gold={"expected": "UNKNOWN", "applicable": True, "confidence": "MEDIUM"},
        baseline={"actual": "UNKNOWN"},
        current={"actual": "NOT_APPLICABLE"},
        assertion_type="EXACT",
    )

    assert result.classification == "GOLD_REVIEW_REQUIRED"
    assert result.is_new_semantic_regression is False


def test_family5_projection_prefers_canonical_values_over_legacy_aggregate() -> None:
    from app.golden.comparator import extract_dimension_values

    snapshot = {
        "videoPlanIR": {"metadata": {"duration": 15.0}},
        "canonicalEvidence": {"specializedApplicability": {
            "STUBBORN_RETURN_LOOP": {"status": "APPLICABLE"},
            "STUBBORN_RETURN_HOOK": {"status": "UNKNOWN"},
            "STUBBORN_RETURN_PAYOFF": {"status": "APPLICABLE"},
        }},
        "dimensionValues": {
            "SPECIALIZED_RULE_APPLICABILITY": "NOT_APPLICABLE",
            "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP": "STALE",
            "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK": "STALE",
            "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF": "STALE",
        },
    }

    values = extract_dimension_values(snapshot)

    assert values["SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP"] == "APPLICABLE"
    assert values["SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK"] == "UNKNOWN"
    assert values["SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF"] == "APPLICABLE"


def test_family5_projection_recomputes_historical_ir_when_canonical_evidence_is_missing() -> None:
    from app.golden.comparator import extract_dimension_values

    snapshot = {
        "videoPlanIR": {"metadata": {"duration": 15.0}},
        "dimensionValues": {"SPECIALIZED_RULE_APPLICABILITY": "LEGACY_AGGREGATE"},
    }

    values = extract_dimension_values(snapshot)

    assert values["SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP"] == "NOT_APPLICABLE"
    assert values["SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK"] == "NOT_APPLICABLE"
    assert values["SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF"] == "NOT_APPLICABLE"


def test_family5_projection_preserves_stored_rule_values_without_ir() -> None:
    from app.golden.comparator import extract_dimension_values

    stored = {
        "SPECIALIZED_RULE_APPLICABILITY": "LEGACY_AGGREGATE",
        "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP": "UNKNOWN",
        "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK": "NOT_APPLICABLE",
        "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF": "APPLICABLE",
    }

    assert extract_dimension_values({"videoPlanIR": None, "dimensionValues": stored}) == stored


def test_family5_unknown_does_not_match_not_applicable() -> None:
    result = compare_dimension(
        gold={"expected": "UNKNOWN", "applicable": True, "confidence": "HIGH"},
        baseline={"actual": "UNKNOWN"},
        current={"actual": "NOT_APPLICABLE"},
        assertion_type="EXACT",
    )

    assert result.classification == "REGRESSED_FROM_BASELINE"
    assert result.is_new_semantic_regression is True


def test_family5_legacy_aggregate_is_not_a_comparator_assertion() -> None:
    from app.golden.comparator import compare_cohort

    truth = {"assets": {"asset-1": {"dimensions": {
        "SPECIALIZED_RULE_APPLICABILITY": {
            "expected": "NOT_APPLICABLE", "applicable": True, "confidence": "HIGH"
        },
    }}}}
    baseline = {"assets": {"asset-1": {"dimensionValues": {
        "SPECIALIZED_RULE_APPLICABILITY": "NOT_APPLICABLE",
    }}}}
    current = {"assets": {"asset-1": {"dimensionValues": {
        "SPECIALIZED_RULE_APPLICABILITY": "APPLICABLE",
    }}}}

    result = compare_cohort(truth, baseline, current)

    assert not any(row["dimension"] == "SPECIALIZED_RULE_APPLICABILITY" for row in result["assertions"])



def test_family6_missing_baseline_dimension_is_non_gating_even_with_ir() -> None:
    from app.golden.comparator import compare_cohort

    truth = {
        "assets": {
            "asset-1": {
                "dimensions": {
                    "TEMPORAL_GENERATION_LOAD": {
                        "expected": "HIGH",
                        "applicable": True,
                        "confidence": "HIGH",
                        "evidenceReferences": [{"excerpt": "structured load"}],
                        "notes": "",
                    }
                }
            }
        }
    }
    baseline = {
        "assets": {
            "asset-1": {
                "dimensionValues": {},
                "videoPlanIR": {
                    "metadata": {"duration": 15.0, "generationMode": "SINGLE_15S"},
                    "beats": [{
                        "id": "beat_01",
                        "startTime": 0.0,
                        "endTime": 3.0,
                        "duration": 3.0,
                        "objectStates": {"box": "closed"},
                        "heldObjects": ["box"],
                        "camera": "locked",
                        "environment": "room",
                    }],
                },
            }
        }
    }
    current = {
        "assets": {
            "asset-1": {
                "canonicalEvidence": {"temporalGenerationLoad": {"status": "HIGH"}},
                "dimensionValues": {"TEMPORAL_GENERATION_LOAD": "HIGH"},
            }
        }
    }

    result = compare_cohort(truth, baseline, current)
    row = result["assertions"][0]
    assert row["classification"] == "BASELINE_NOT_CAPTURED"
    assert row["isNewSemanticRegression"] is False
    assert result["baselineNotCaptured"] == 1
    assert result["newSemanticRegressions"] == 0



def test_family6_stored_baseline_and_canonical_override_are_cohort_safe() -> None:
    from app.golden.comparator import compare_cohort

    truth = {
        "assets": {
            "asset-1": {
                "dimensions": {
                    "TEMPORAL_GENERATION_LOAD": {
                        "expected": "HIGH",
                        "applicable": True,
                        "confidence": "HIGH",
                        "evidenceReferences": [{"excerpt": "stored Family 6 status"}],
                        "notes": "",
                    }
                }
            }
        }
    }
    baseline = {
        "assets": {
            "asset-1": {
                "dimensionValues": {"TEMPORAL_GENERATION_LOAD": "MANAGEABLE"},
            }
        }
    }
    current = {
        "assets": {
            "asset-1": {
                "canonicalEvidence": {"temporalGenerationLoad": {"status": "HIGH"}},
                "dimensionValues": {"TEMPORAL_GENERATION_LOAD": "MANAGEABLE"},
            }
        }
    }
    improved = compare_cohort(truth, baseline, current)
    assert improved["assertions"][0]["classification"] == "IMPROVED_FROM_BASELINE"

    baseline_with_canonical = {
        "assets": {
            "asset-1": {
                "canonicalEvidence": {"temporalGenerationLoad": {"status": "HIGH"}},
                "dimensionValues": {"TEMPORAL_GENERATION_LOAD": "MANAGEABLE"},
            }
        }
    }
    passed = compare_cohort(truth, baseline_with_canonical, current)
    assert passed["assertions"][0]["classification"] == "PASS"


def test_cohort_representation_mismatch_is_independent_release_metric() -> None:
    from app.golden.comparator import compare_cohort

    truth = {"assets": {"asset-1": {"dimensions": {}}}}
    snapshot = {
        "goldenId": "asset-1",
        "status": "OK",
        "report": {"overallScore": 82.5},
        "assessment": {"creative_score": 82.5},
        "apiReport": {
            "overall_score": 82.5,
            "score_card": {"score": 0.0},
            "pre_render_assessment": {"creative_score": 82.5},
        },
    }

    result = compare_cohort(
        truth,
        {"assets": {"asset-1": snapshot}},
        {"assets": {"asset-1": snapshot}},
    )

    assert result["representationMismatches"] == 1
    representation_rows = [
        row for row in result["assertions"]
        if row["classification"] == "REPRESENTATION_MISMATCH"
    ]
    assert len(representation_rows) == 1
    assert representation_rows[0]["category"] == "REPRESENTATION"
    assert representation_rows[0]["path"] == "overall_score"
    assert result["newSemanticRegressions"] == 0
    assert result["unexpectedPolicyRegressions"] == 0
    assert result["releaseGate"] == "FAIL"
