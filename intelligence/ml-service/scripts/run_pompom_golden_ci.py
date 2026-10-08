from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import yaml

from app.golden.baseline import write_baseline
from app.golden.ci_gate import evaluate_ci_gate, verify_manifest_hashes
from app.golden.report import build_regression_report, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic POMPOM Golden regression")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--ruleset", required=True)
    parser.add_argument("--truth", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--reports", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    approved_hashes_path = manifest_path.with_name("approved_hashes.yaml")
    approved_hashes = yaml.safe_load(approved_hashes_path.read_text(encoding="utf-8"))["approvedPromptHashes"]
    verify_manifest_hashes(manifest, manifest_path.parent, approved_hashes)

    reports = Path(args.reports)
    reports.mkdir(parents=True, exist_ok=True)
    current_path = reports / "current.json"
    write_baseline(manifest_path, args.ruleset, current_path)
    report = build_regression_report(args.truth, args.policy, args.baseline, current_path)
    (reports / "golden-regression-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (reports / "golden-regression-report.md").write_text(render_markdown(report), encoding="utf-8")
    gate = evaluate_ci_gate(
        {
            "newSemanticRegressions": report["summary"]["newSemanticRegressions"],
            "unexpectedPolicyRegressions": report["summary"]["unexpectedPolicyRegressions"],
            "representationMismatches": report["summary"]["representationMismatches"],
        },
        provider_mode=os.getenv("POMPOM_GOLDEN_PROVIDER_MODE", "FROZEN_DETERMINISTIC"),
    )
    print(json.dumps({"releaseGate": gate, "summary": report["summary"]}, sort_keys=True))
    return 0 if gate == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
