"""TDD contracts for Family 6 Golden snapshot and comparator propagation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.golden.comparator import extract_dimension_values
from app.golden.deterministic_runner import run_golden_asset
from app.quality.canonical_evidence import temporal_generation_load_evidence

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "data" / "golden" / "pompom-golden-v1"
MANIFEST = GOLDEN_ROOT / "manifest.yaml"
RULESET = ROOT / "data" / "rules" / "RULESET_1.7.yaml"


def _asset(asset_id: str) -> dict[str, Any]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return next(item for item in manifest["assets"] if item["goldenId"] == asset_id)


def _evaluation_signature(result: Any) -> list[tuple[str, str, str]]:
    assert result.report is not None
    return [
        (item.rule_id, item.outcome.value, item.configured_severity.value)
        for item in result.report.evaluations
    ]


def test_deterministic_snapshot_projects_family6_canonical_evidence() -> None:
    result = run_golden_asset(_asset("sticky-ball-01"), manifest_path=MANIFEST, ruleset_path=RULESET)

    assert result.status == "OK"
    assert result.parse_result is not None
    expected = temporal_generation_load_evidence(result.parse_result.video_plan_ir).to_dict()
    snapshot = result.to_dict()

    assert snapshot["canonicalEvidence"]["temporalGenerationLoad"] == expected
    assert set(snapshot["canonicalEvidence"]["temporalGenerationLoad"]) == {
        "status",
        "axes",
        "severeAxisCount",
        "elevatedAxisCount",
        "highBasis",
        "evidenceStatus",
        "version",
    }


def test_family6_snapshot_serialization_does_not_change_policy_or_rule_output() -> None:
    result = run_golden_asset(_asset("sticky-ball-01"), manifest_path=MANIFEST, ruleset_path=RULESET)

    assert result.report is not None
    before_evaluations = _evaluation_signature(result)
    before_score = result.report.overall_score
    before_authorization = (result.assessment or {}).get("render_authorization")
    snapshot = result.to_dict()

    assert _evaluation_signature(result) == before_evaluations
    assert result.report.overall_score == before_score
    assert snapshot["assessment"]["render_authorization"] == before_authorization
    assert "creativeScore" not in snapshot["canonicalEvidence"]["temporalGenerationLoad"]
    assert "renderAuthorization" not in snapshot["canonicalEvidence"]["temporalGenerationLoad"]


def test_family6_comparator_uses_canonical_snapshot_before_stored_value() -> None:
    snapshot = {
        "canonicalEvidence": {"temporalGenerationLoad": {"status": "HIGH"}},
        "dimensionValues": {"TEMPORAL_GENERATION_LOAD": "MANAGEABLE"},
    }

    assert extract_dimension_values(snapshot)["TEMPORAL_GENERATION_LOAD"] == "HIGH"



def test_missing_v17_family6_baseline_is_non_gating() -> None:
    from app.golden.comparator import compare_dimension

    comparison = compare_dimension(
        gold={"expected": "HIGH", "applicable": True, "confidence": "HIGH"},
        baseline={},
        current={"actual": "UNKNOWN"},
        assertion_type="EXACT",
        baseline_captured=False,
    )
    assert comparison.classification == "BASELINE_NOT_CAPTURED"
    assert comparison.is_new_semantic_regression is False


def test_family6_does_not_read_assessment_temporal_complexity() -> None:
    snapshot = {
        "canonicalEvidence": {"temporalGenerationLoad": {"status": "HIGH"}},
        "assessment": {"temporal_complexity": {"status": "MANAGEABLE"}},
    }
    assert extract_dimension_values(snapshot)["TEMPORAL_GENERATION_LOAD"] == "HIGH"
