"""Verify scoped source-reviewed Family 10 calibration alongside the frozen Golden gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from app.api.quality import convert_quality_report
from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.golden.ci_gate import evaluate_ci_gate
from app.golden.family10 import compare_general_producibility
from app.quality.contracts import ParserMetadata, QualityReport, QualityStatus
from app.quality.general_producibility import GENERAL_PRODUCIBILITY_DIMENSIONS, general_producibility_evidence
from app.scoring.quality_scorer import QualityScorer


def build_review(golden_root: Path, current: dict[str, Any], regression: dict[str, Any]) -> dict[str, Any]:
    manifest = yaml.safe_load((golden_root / "manifest.yaml").read_text())
    fixtures = json.loads((golden_root / "frozen-semantic/family10/requirements.json").read_text())
    assertions: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    transport_mismatches: list[dict[str, Any]] = []

    def check(asset_id: str, name: str, actual: Any, expected: Any) -> None:
        assertions.append(
            {
                "assetId": asset_id,
                "path": name,
                "actual": actual,
                "expected": expected,
                "passed": actual == expected,
            }
        )

    check("COHORT", "assetIds", sorted(fixtures["assets"]), sorted(current["assets"]))
    check("COHORT", "assetCount", len(fixtures["assets"]), 9)
    for source in manifest["assets"]:
        key = source["goldenId"]
        fixture = fixtures["assets"][key]
        snapshot = current["assets"][key]
        pipeline = snapshot["generalProducibility"]
        transport = compare_general_producibility(snapshot)
        transport_mismatches.extend(transport["mismatches"])
        raw = (golden_root / source["promptFile"]).read_bytes()
        check(key, "fixture.promptHash", fixture["promptHash"], source["promptHash"])
        check(key, "source.sha256", hashlib.sha256(raw).hexdigest(), source["promptHash"])
        lines = raw.decode().splitlines()
        for evidence in fixture["sourceEvidence"]:
            excerpt = "\n".join(lines[evidence["startLine"] - 1 : evidence["endLine"]])
            check(key, evidence["reference"], evidence["quote"] in excerpt, True)
        ir = fixture["videoPlanIR"]
        projection = general_producibility_evidence(ir)
        check(key, "reviewed.status", projection["status"], fixture["expectedStatus"])
        check(
            key,
            "reviewed.dimensions",
            sorted(projection["dimensions"]),
            sorted(GENERAL_PRODUCIBILITY_DIMENSIONS),
        )
        for dimension, risk in projection["dimensions"].items():
            check(
                key,
                f"{dimension}.level",
                risk["level"] in {"LOW", "MODERATE", "HIGH", "UNKNOWN", "NOT_APPLICABLE"},
                True,
            )
        check(key, "durationSeconds", projection["durationSeconds"], ir["metadata"]["duration"])
        check(
            key,
            "provenance.promptHash",
            projection["provenance"]["sourceEvidence"]["promptHash"],
            fixture["promptHash"],
        )
        report = QualityReport(None, QualityStatus.NEEDS_REVISION, {}, (), "1.7", "FAMILY10_REVIEW")
        parser = ParserMetadata(1)
        assessment = build_pre_render_assessment(ir, parser, report, "1.7")
        enhanced = QualityScorer().create_enhanced_report(report, ir, parser)
        api = convert_quality_report(enhanced, "1.7", video_plan_ir=ir).model_dump(mode="json")
        review_snapshot = {
            "goldenId": key,
            "status": "OK",
            "generalProducibility": projection,
            "canonicalEvidence": {"generalProducibility": projection},
            "assessment": assessment,
            "apiReport": api,
        }
        review_transport = compare_general_producibility(review_snapshot)
        transport_mismatches.extend(review_transport["mismatches"])
        check(key, "assessment.general_producibility", assessment["general_producibility"], projection)
        check(
            key,
            "api.general_producibility",
            api["pre_render_assessment"]["general_producibility"],
            projection,
        )
        assets.append(
            {
                "goldenId": key,
                "displayName": source["displayName"],
                "pipelineStatus": pipeline["status"],
                "pipelineEvidence": pipeline,
                "reviewedStatus": projection["status"],
                "mlApiReport": api,
                "reviewedEvidence": projection,
                "moderateHighRisks": {
                    dimension: risk
                    for dimension, risk in projection["dimensions"].items()
                    if risk["level"] in {"MODERATE", "HIGH"}
                },
                "applicableDimensions": [
                    dimension
                    for dimension, risk in projection["dimensions"].items()
                    if risk["level"] not in {"UNKNOWN", "NOT_APPLICABLE"}
                ],
                "sourceEvidence": fixture["sourceEvidence"],
                "expected": fixture["expectedStatus"],
                "resultExpected": projection["status"] == fixture["expectedStatus"],
                "reviewNote": fixture["reviewNote"],
            }
        )
    summary = regression["summary"]
    gate = evaluate_ci_gate(
        {
            "newSemanticRegressions": summary["newSemanticRegressions"],
            "unexpectedPolicyRegressions": summary["unexpectedPolicyRegressions"],
            "representationMismatches": summary["representationMismatches"] + len(transport_mismatches),
        }
    )
    failed = sum(not row["passed"] for row in assertions)
    return {
        "family": "FAMILY_10",
        "evidenceMode": "MANUAL_SOURCE_REVIEW_AND_PRODUCTION_IR",
        "releaseGate": "PASS" if gate == "PASS" and failed == 0 else "FAIL",
        "summary": {
            **summary,
            "family10Assertions": len(assertions),
            "family10FailedAssertions": failed,
            "family10RepresentationMismatches": len(transport_mismatches),
            "pipelineUnknownAssets": sum(row["pipelineStatus"] == "UNKNOWN" for row in assets),
        },
        "assets": assets,
        "assertions": assertions,
        "transportMismatches": transport_mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden-root", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--api-contract", type=Path)
    args = parser.parse_args()
    current = json.loads((args.reports / "current.json").read_text())
    regression = json.loads((args.reports / "golden-regression-report.json").read_text())
    review = build_review(args.golden_root, current, regression)
    (args.reports / "family10-review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n"
    )
    if args.api_contract is not None:
        contract = {
            "fixtureVersion": "family10-api-contract-v1",
            "evidenceMode": "MANUAL_SOURCE_REVIEW",
            "assets": {asset["goldenId"]: asset["mlApiReport"] for asset in review["assets"]},
        }
        args.api_contract.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"releaseGate": review["releaseGate"], "summary": review["summary"]}, sort_keys=True))
    return 0 if review["releaseGate"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
