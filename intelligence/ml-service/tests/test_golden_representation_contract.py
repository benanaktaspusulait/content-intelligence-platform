from __future__ import annotations

import json
from pathlib import Path

from app.scoring.quality_scorer import QualityScorer


FIXTURE = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1" / "reports" / "representation_contract.json"


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
