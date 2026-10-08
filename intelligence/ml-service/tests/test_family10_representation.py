"""Family 10 ML/API/Golden representation and frozen policy contracts."""

from copy import deepcopy

import pytest
from test_family10_general_producibility import simple_sequential_ir

from app.api.quality import convert_quality_report
from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.golden.comparator import compare_representation_consistency
from app.quality.contracts import (
    ParserMetadata,
    QualityReport,
    QualityStatus,
    RuleEvaluation,
    RuleOutcome,
    Severity,
)
from app.quality.general_producibility import general_producibility_evidence
from app.scoring.quality_scorer import QualityScorer


def report_fixture():
    return QualityReport(
        98,
        QualityStatus.RENDER_READY,
        {},
        (
            RuleEvaluation(
                "SYNTHETIC_CREATIVE", "Creative", "concept", RuleOutcome.PASS, Severity.PASS, "Clear."
            ),
        ),
        "1.7",
        "FAMILY10_DETERMINISTIC",
    )


def test_grade_a_risky_projection_preserves_existing_policy_and_full_api_payload():
    ir = simple_sequential_ir()
    for row in ir["beats"]:
        row["visualStateId"] = row["id"]
    report = report_fixture()
    parser = ParserMetadata(1)
    before = build_pre_render_assessment(ir, parser, report, "1.7")
    ir["fineMotorRequirement"] = {"required": True, "precision": "HIGH"}
    after = build_pre_render_assessment(ir, parser, report, "1.7")
    for field in (
        "family8",
        "creative_score",
        "creative_grade",
        "evidence_completeness",
        "render_authorization",
    ):
        assert before[field] == after[field]
    assert after["creative_grade"] == "A"
    assert after["general_producibility"]["status"] == "RISKY"
    enhanced = QualityScorer().create_enhanced_report(report, ir, parser)
    api = convert_quality_report(enhanced, "1.7", video_plan_ir=ir).model_dump(mode="json")
    assert api["pre_render_assessment"]["general_producibility"] == after["general_producibility"]


def test_assumed_parser_duration_is_not_general_producibility_evidence():
    ir = simple_sequential_ir()
    parser = ParserMetadata(1, assumptions=("Duration not explicit, using default: 15.0s",))
    result = build_pre_render_assessment(ir, parser, report_fixture(), "1.7")["general_producibility"]
    assert result["status"] == "UNKNOWN"
    assert result["durationSeconds"] is None
    assert result["durationSource"] == "PARSER_DURATION_ASSUMPTION"


@pytest.mark.parametrize(
    "path",
    [
        ("status",),
        ("durationSeconds",),
        ("dimensions", "FINE_MOTOR_PRECISION", "level"),
        ("dimensions", "FINE_MOTOR_PRECISION", "reason"),
        ("dimensions", "FINE_MOTOR_PRECISION", "evidenceReferences"),
        ("provenance",),
    ],
)
def test_golden_comparator_detects_family10_transport_drift(path):
    from test_family9_golden_representation import coherent_snapshot

    snapshot = coherent_snapshot()
    value = general_producibility_evidence(None)
    snapshot["assessment"]["general_producibility"] = value
    snapshot["apiReport"]["pre_render_assessment"]["general_producibility"] = deepcopy(value)
    assert compare_representation_consistency(snapshot)["consistent"]
    target = snapshot["apiReport"]["pre_render_assessment"]["general_producibility"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = "MUTATED"
    assert not compare_representation_consistency(snapshot)["consistent"]


def test_dedicated_family10_comparator_checks_canonical_api_provenance_and_timeout():
    from app.golden.family10 import compare_general_producibility

    projection = general_producibility_evidence(None)
    snapshot = {
        "status": "OK",
        "generalProducibility": projection,
        "canonicalEvidence": {"generalProducibility": deepcopy(projection)},
        "assessment": {"general_producibility": deepcopy(projection)},
        "apiReport": {"pre_render_assessment": {"general_producibility": deepcopy(projection)}},
    }
    assert compare_general_producibility(snapshot)["consistent"]
    snapshot["canonicalEvidence"]["generalProducibility"]["durationSeconds"] = 0
    assert not compare_general_producibility(snapshot)["consistent"]
    snapshot = {"status": "PARSER_TIMEOUT", "generalProducibility": general_producibility_evidence(None)}
    assert compare_general_producibility(snapshot)["consistent"]
    snapshot["generalProducibility"]["status"] = "NOT_PRODUCIBLE"
    assert not compare_general_producibility(snapshot)["consistent"]
