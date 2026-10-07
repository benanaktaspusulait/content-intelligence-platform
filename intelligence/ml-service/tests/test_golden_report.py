from __future__ import annotations

from pathlib import Path

from app.golden.report import build_regression_report


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data" / "golden" / "pompom-golden-v1"
TRUTH = BASE / "truth" / "gold_truth.yaml"
POLICY = BASE / "policy" / "policy_expectations_v1.7.yaml"
BASELINE = BASE / "baselines" / "v1.7" / "baseline.json"


def test_baseline_report_has_release_gate_and_summary_metrics() -> None:
    report = build_regression_report(TRUTH, POLICY, BASELINE, BASELINE)
    assert report["goldenSetVersion"] == "POMPOM_GOLDEN_V1"
    assert report["baselineRulesetVersion"] == "1.7"
    assert report["summary"]["assets"] == 9
    assert "newSemanticRegressions" in report["summary"]
    assert report["releaseGate"] in {"PASS", "FAIL"}
    assert len(report["assets"]) == 9
