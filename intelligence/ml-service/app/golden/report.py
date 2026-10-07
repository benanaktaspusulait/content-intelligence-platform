from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .comparator import compare_cohort


def _read_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_regression_report(
    truth_path: str | Path,
    policy_path: str | Path,
    baseline_path: str | Path,
    current_path: str | Path,
) -> dict[str, Any]:
    truth = _read_yaml(truth_path)
    policy = _read_yaml(policy_path)
    baseline = _read_json(baseline_path)
    current = _read_json(current_path)
    comparison = compare_cohort(truth, baseline, current, policy)
    assets: dict[str, dict[str, Any]] = {}
    for assertion in comparison["assertions"]:
        assets.setdefault(assertion["assetId"], {"assertions": []})["assertions"].append(assertion)
    for asset_id, item in assets.items():
        item["displayName"] = (truth.get("assets", {}).get(asset_id) or {}).get("displayName", asset_id)
        item["corpusRole"] = (baseline.get("assets", {}).get(asset_id) or {}).get("corpusRole", "UNKNOWN")
    summary = {
        "assets": len(assets),
        "goldAssertions": len(comparison["assertions"]),
        "semanticPassed": comparison["passed"],
        "semanticFailed": comparison["failed"],
        "improvedFromBaseline": comparison["improvedFromBaseline"],
        "unchangedKnownIssues": comparison["unchangedKnownIssues"],
        "newSemanticRegressions": comparison["newSemanticRegressions"],
        "expectedPolicyChanges": comparison["expectedPolicyChanges"],
        "unexpectedPolicyRegressions": comparison["unexpectedPolicyRegressions"],
        "goldReviewRequired": comparison["goldReviewRequired"],
    }
    return {
        "goldenSetVersion": truth.get("goldenSetVersion", "UNKNOWN"),
        "goldLabelVersion": truth.get("goldTruthVersion", "UNKNOWN"),
        "baselineRulesetVersion": baseline.get("rulesetVersion", "UNKNOWN"),
        "fingerprint": baseline.get("fingerprint", {}),
        "releaseGate": comparison["releaseGate"],
        "summary": summary,
        "assets": assets,
        "assertions": comparison["assertions"],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"# {report['goldenSetVersion']} Golden Regression Report",
        "",
        f"**Calibration release gate:** `{report['releaseGate']}`",
        f"**Baseline:** RULESET `{report['baselineRulesetVersion']}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    labels = {
        "assets": "Assets",
        "goldAssertions": "Golden assertions",
        "semanticPassed": "Semantic passed",
        "semanticFailed": "Semantic failed",
        "improvedFromBaseline": "Improved from baseline",
        "unchangedKnownIssues": "Unchanged known issues",
        "newSemanticRegressions": "NEW semantic regressions",
        "expectedPolicyChanges": "Expected policy changes",
        "unexpectedPolicyRegressions": "Unexpected policy regressions",
        "goldReviewRequired": "Gold review required",
    }
    lines.extend(f"| {labels[key]} | {summary[key]} |" for key in labels)
    lines.extend(["", "## Asset Matrix", "", "| Asset | Corpus role | Assertions |", "|---|---|---:|"])
    for asset_id, asset in sorted(report["assets"].items()):
        lines.append(f"| {asset['displayName']} (`{asset_id}`) | {asset['corpusRole']} | {len(asset['assertions'])} |")
    lines.extend(["", "## Full-stack Fingerprint", "", "```json", json.dumps(report["fingerprint"], indent=2, sort_keys=True), "```", ""])
    return "\n".join(lines)


def write_regression_report(
    truth_path: str | Path,
    policy_path: str | Path,
    baseline_path: str | Path,
    current_path: str | Path,
    output_directory: str | Path,
) -> dict[str, Any]:
    report = build_regression_report(truth_path, policy_path, baseline_path, current_path)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    (output / "golden-regression-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "golden-regression-report.md").write_text(render_markdown(report), encoding="utf-8")
    return report
