"""Family 9 RED-phase Golden representation consistency contracts."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from app.golden import deterministic_runner
from app.golden.comparator import compare_representation_consistency
from app.golden.deterministic_runner import GoldenAnalysisTimeout, run_golden_asset

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "data" / "golden" / "pompom-golden-v1"
MANIFEST = GOLDEN_ROOT / "manifest.yaml"
RULESET = ROOT / "data" / "rules" / "RULESET_1.7.yaml"


def authorization_reasons() -> list[dict[str, Any]]:
    return [
        {
            "code": "REQUIRED_EVIDENCE_MISSING",
            "source": "EVIDENCE_COMPLETENESS",
            "message": "Visual evidence pending",
            "references": ["first-frame", "silhouette"],
        },
        {
            "code": "ASSESSMENT_TECHNICAL_FAILURE",
            "source": "ASSESSMENT",
            "message": "Independent validation pending",
            "references": ["validation-record"],
        },
    ]


def coherent_snapshot() -> dict[str, Any]:
    family8 = {
        "creativeQuality": {
            "creativeScore": None,
            "creativeGrade": "A",
            "familyScores": {"family9_sticky_ball": None},
        },
        "evidenceCompleteness": {
            "status": "PARTIAL",
            "evaluationCoverage": 0.75,
            "aggregation": {
                "score": None,
                "scoredCount": 2,
                "denominator": 2,
                "passCount": 1,
                "failCount": 1,
                "unknownCount": 1,
                "notEvaluatedCount": 1,
                "notApplicableCount": 1,
                "serviceErrorCount": 1,
                "evaluationCoverage": 0.75,
                "aggregationState": "PARTIAL",
            },
        },
        "renderAuthorization": {
            "status": "BLOCKED_PENDING_EVIDENCE",
            "reasons": authorization_reasons(),
        },
        "legacy": {"readiness": "READY_TO_RENDER"},
    }
    assessment = {
        "creative_score": None,
        "creative_grade": "A",
        "assessment_coverage_percent": 75,
        "aggregation": family8["evidenceCompleteness"]["aggregation"],
        "evidence_completeness": {
            "status": family8["evidenceCompleteness"]["status"],
            "evaluationCoverage": family8["evidenceCompleteness"]["evaluationCoverage"],
        },
        "render_authorization": {
            "status": family8["renderAuthorization"]["status"],
        },
        "family8": family8,
    }
    return {
        "goldenId": "family9-synthetic",
        "status": "OK",
        "aggregation": deepcopy(family8["evidenceCompleteness"]["aggregation"]),
        "report": {
            "overallScore": None,
            "familyScores": {"family9_sticky_ball": None},
        },
        "assessment": assessment,
        "apiReport": {
            "overall_score": None,
            "family_scores": {"family9_sticky_ball": None},
            "score_card": {"score": None, "label": "Not evaluated", "color": "gray"},
            "pre_render_assessment": deepcopy(assessment),
        },
    }


def test_coherent_snapshot_has_zero_representation_mismatches() -> None:
    result = compare_representation_consistency(coherent_snapshot())

    assert result["checked"] is True
    assert result["consistent"] is True
    assert result["mismatches"] == []


def test_family8_authorization_reason_mutation_is_a_representation_mismatch() -> None:
    snapshot = coherent_snapshot()
    snapshot["apiReport"]["pre_render_assessment"]["family8"]["renderAuthorization"]["reasons"][0][
        "references"
    ] = [
        "mutated-reference"
    ]

    result = compare_representation_consistency(snapshot)

    assert result["consistent"] is False
    assert any(
        mismatch["path"] == "family8.renderAuthorization.reasons"
        for mismatch in result["mismatches"]
    )


def test_null_score_mutation_is_not_silently_coerced_to_zero() -> None:
    snapshot = coherent_snapshot()
    snapshot["apiReport"]["score_card"]["score"] = 0.0

    result = compare_representation_consistency(snapshot)

    assert result["consistent"] is False
    assert any("score" in mismatch["path"] for mismatch in result["mismatches"])


def test_missing_nested_authorization_reasons_is_a_representation_mismatch() -> None:
    snapshot = coherent_snapshot()
    del snapshot["apiReport"]["pre_render_assessment"]["family8"]["renderAuthorization"]["reasons"]

    result = compare_representation_consistency(snapshot)

    assert result["consistent"] is False
    mismatch = next(
        mismatch
        for mismatch in result["mismatches"]
        if mismatch["path"] == "family8.renderAuthorization.reasons"
    )
    assert mismatch["expectedPresent"] is True
    assert mismatch["actualPresent"] is False


def test_frozen_manifest_runner_checks_all_nine_assets_and_quarantines_parser_timeout(
    monkeypatch,
) -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assets = manifest["assets"]
    assert len(assets) == 9

    original_bounded_call = deterministic_runner._bounded_call
    checked: dict[str, tuple[Any, dict[str, Any]]] = {}

    for asset in assets:
        if asset["goldenId"] == "upside-chair-01":
            def raise_timeout(_function: Any, _timeout_seconds: int) -> Any:
                raise GoldenAnalysisTimeout("synthetic Family 9 parser timeout")

            monkeypatch.setattr(deterministic_runner, "_bounded_call", raise_timeout)
        else:
            monkeypatch.setattr(deterministic_runner, "_bounded_call", original_bounded_call)

        run = run_golden_asset(asset, manifest_path=MANIFEST, ruleset_path=RULESET)
        comparison = compare_representation_consistency(run.to_dict())
        checked[asset["goldenId"]] = (run, comparison)

        assert comparison["checked"] is True
        assert comparison["assetId"] == asset["goldenId"]
        assert comparison["consistent"] is True
        assert comparison["mismatches"] == []

    assert set(checked) == {asset["goldenId"] for asset in assets}
    timeout_run, timeout_comparison = checked["upside-chair-01"]
    assert timeout_run.status == "PARSER_TIMEOUT"
    timeout_snapshot = timeout_run.to_dict()
    assert timeout_snapshot["report"] is None
    assert timeout_snapshot["assessment"] is None
    assert timeout_snapshot["apiReport"] is None
    assert timeout_snapshot["aggregation"]["score"] is None
    assert not any(
        mismatch.get("category") == "CREATIVE"
        for mismatch in timeout_comparison["mismatches"]
    )


def test_ok_snapshot_missing_api_pre_render_projection_is_a_representation_mismatch() -> None:
    snapshot = coherent_snapshot()
    del snapshot["apiReport"]["pre_render_assessment"]

    result = compare_representation_consistency(snapshot)

    assert result["checked"] is True
    assert result["consistent"] is False
    assert any(
        mismatch["path"] == "apiReport.pre_render_assessment"
        for mismatch in result["mismatches"]
    )
