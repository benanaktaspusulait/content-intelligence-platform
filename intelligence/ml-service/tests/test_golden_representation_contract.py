from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.golden.deterministic_runner import run_golden_asset
from app.quality.canonical_evidence import specialized_applicability_evidence
from app.scoring.quality_scorer import QualityScorer


ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "data" / "golden" / "pompom-golden-v1"
FIXTURE = GOLDEN_ROOT / "reports" / "representation_contract.json"
MANIFEST = GOLDEN_ROOT / "manifest.yaml"
RULESET = ROOT / "data" / "rules" / "RULESET_1.7.yaml"


def test_canonical_representation_fixture_is_percent_unit_and_three_outcome_aware() -> None:
    contract = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert contract["stateShareUnit"] == "PERCENT_0_100"
    assert contract["stateSharePercent"] == 20.0
    assert contract["stateShareFormatted"] == "20%"
    assert set(contract["outcomes"]) == {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE", "SERVICE_ERROR"}
    assert contract["creativeGrade"] != contract["renderAuthorization"]


def test_existing_scorer_produces_the_contract_percent_without_second_multiplication() -> None:
    ir = {
        "metadata": {"duration": 15.0},
        "beats": [{
            "startTime": 0.0,
            "endTime": 3.0,
            "action": "Mimi pulls",
            "consequence": "object moves",
            "intensity": 5,
            "isNewConsequence": True,
            "consequenceType": "new",
            "visualStateId": "state",
        }],
    }
    timeline = QualityScorer()._create_timeline_data(ir)
    assert timeline["state_segments"][0]["percentage"] == 20.0
    assert timeline["state_segments"][0]["percentage"] != 2000.0


def test_deterministic_snapshot_projects_specialized_applicability_into_assessment() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    asset = next(item for item in manifest["assets"] if item["goldenId"] == "box-cat-01")

    result = run_golden_asset(asset, manifest_path=MANIFEST, ruleset_path=RULESET)

    assert result.status == "OK"
    assert result.parse_result is not None
    expected_assessment_map = {
        rule_id: evidence.to_dict()
        for rule_id, evidence in specialized_applicability_evidence(result.parse_result.video_plan_ir).items()
    }
    snapshot = result.to_dict()
    specialized_applicability = snapshot["canonicalEvidence"]["specializedApplicability"]

    assert set(specialized_applicability) == {
        "STUBBORN_RETURN_LOOP",
        "STUBBORN_RETURN_HOOK",
        "STUBBORN_RETURN_PAYOFF",
    }
    assert set(specialized_applicability["STUBBORN_RETURN_LOOP"]) == {
        "status",
        "confidence",
        "evidenceReferences",
        "reason",
    }
    assert specialized_applicability == expected_assessment_map
    assert snapshot["assessment"]["specialized_applicability"] == expected_assessment_map
