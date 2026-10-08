"""The Family 10 freeze gate rejects status or representation drift, not unknowns."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.golden.baseline import capture_baseline
from scripts.run_family10_golden_review import build_review

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "data/golden/pompom-golden-v1"


@pytest.fixture(scope="module")
def snapshots():
    return capture_baseline(GOLDEN / "manifest.yaml", ROOT / "data/rules/RULESET_1.7.yaml")


def regression():
    return {
        "summary": {
            "assets": 9,
            "newSemanticRegressions": 0,
            "unexpectedPolicyRegressions": 0,
            "representationMismatches": 0,
        }
    }


def test_nine_asset_source_review_and_transport_gate_passes(snapshots):
    review = build_review(GOLDEN, snapshots, regression())
    assert review["releaseGate"] == "PASS"
    assert len(review["assets"]) == 9
    assert review["summary"]["family10FailedAssertions"] == 0
    assert review["summary"]["family10RepresentationMismatches"] == 0
    assert all(asset["resultExpected"] for asset in review["assets"])
    assert {asset["reviewedStatus"] for asset in review["assets"]} == {"PRODUCIBLE", "RISKY"}


def test_family10_canonical_drift_fails_gate_even_if_family9_did_not_change(snapshots):
    changed = deepcopy(snapshots)
    changed["assets"]["box-cat-01"]["apiReport"]["pre_render_assessment"]["general_producibility"][
        "status"
    ] = "NOT_PRODUCIBLE"
    review = build_review(GOLDEN, changed, regression())
    assert review["releaseGate"] == "FAIL"
    assert review["summary"]["family10RepresentationMismatches"] > 0


def test_general_release_regressions_are_not_hidden_by_family10_success(snapshots):
    changed = regression()
    changed["summary"]["unexpectedPolicyRegressions"] = 1
    assert build_review(GOLDEN, snapshots, changed)["releaseGate"] == "FAIL"


def test_reviewed_expectation_mutation_fails_family10_gate(snapshots, tmp_path):
    import shutil

    root = tmp_path / "golden"
    shutil.copytree(GOLDEN / "prompts", root / "prompts")
    shutil.copyfile(GOLDEN / "manifest.yaml", root / "manifest.yaml")
    path = root / "frozen-semantic/family10/requirements.json"
    path.parent.mkdir(parents=True)
    fixture = json.loads((GOLDEN / "frozen-semantic/family10/requirements.json").read_text())
    fixture["assets"]["box-cat-01"]["expectedStatus"] = "NOT_PRODUCIBLE"
    path.write_text(json.dumps(fixture))
    review = build_review(root, snapshots, regression())
    assert review["releaseGate"] == "FAIL"
    assert review["summary"]["family10FailedAssertions"] == 1
