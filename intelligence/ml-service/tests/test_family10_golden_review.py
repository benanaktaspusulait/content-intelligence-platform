"""Family 10 source-reviewed calibration without reopening parser/Gold Truth."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from app.api.quality import convert_quality_report
from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.quality.contracts import ParserMetadata, QualityReport, QualityStatus
from app.quality.general_producibility import GENERAL_PRODUCIBILITY_DIMENSIONS, general_producibility_evidence
from app.scoring.quality_scorer import QualityScorer

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "data/golden/pompom-golden-v1"
REVIEW = json.loads((GOLDEN / "frozen-semantic/family10/requirements.json").read_text())
API_CONTRACT = json.loads((GOLDEN / "frozen-semantic/family10/api-contract.json").read_text())
MANIFEST = yaml.safe_load((GOLDEN / "manifest.yaml").read_text())


@pytest.mark.parametrize("golden_id", [asset["goldenId"] for asset in MANIFEST["assets"]])
def test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api(golden_id):
    source = next(asset for asset in MANIFEST["assets"] if asset["goldenId"] == golden_id)
    fixture = REVIEW["assets"][golden_id]
    raw = (GOLDEN / source["promptFile"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source["promptHash"] == fixture["promptHash"]
    lines = raw.decode().splitlines()
    for evidence in fixture["sourceEvidence"]:
        excerpt = "\n".join(lines[evidence["startLine"] - 1 : evidence["endLine"]])
        assert evidence["quote"] in excerpt
    ir = fixture["videoPlanIR"]
    frozen_ir = deepcopy(ir)
    projection = general_producibility_evidence(ir)
    assert projection["status"] == fixture["expectedStatus"]
    assert set(projection["dimensions"]) == set(GENERAL_PRODUCIBILITY_DIMENSIONS)
    assert projection["durationSeconds"] == ir["metadata"]["duration"]
    assert projection["provenance"]["sourceEvidence"]["promptHash"] == fixture["promptHash"]
    # Existing scoring/admission sees exactly the same old report with/without risk fields.
    report = QualityReport(None, QualityStatus.NEEDS_REVISION, {}, (), "1.7", "FAMILY10_REVIEW")
    parser = ParserMetadata(1)
    assessment = build_pre_render_assessment(ir, parser, report, "1.7")
    enhanced = QualityScorer().create_enhanced_report(report, ir, parser)
    api = convert_quality_report(enhanced, "1.7", video_plan_ir=ir).model_dump(mode="json")
    assert assessment["general_producibility"] == projection
    assert api["pre_render_assessment"]["general_producibility"] == projection
    transport = API_CONTRACT["assets"][golden_id]
    assert transport["pre_render_assessment"] == api["pre_render_assessment"]
    assert transport["overall_score"] is None
    assert assessment["creative_score"] is None
    assert api["overall_score"] is None
    assert ir == frozen_ir
    assert not any(field in ir for field in ("corpusRole", "performanceClass", "virality", "engagement"))


def test_calibration_is_exactly_the_frozen_nine_asset_set():
    assert set(REVIEW["assets"]) == {asset["goldenId"] for asset in MANIFEST["assets"]}
    assert len(REVIEW["assets"]) == 9
    assert REVIEW["scope"] == "FAMILY_10_ONLY"
