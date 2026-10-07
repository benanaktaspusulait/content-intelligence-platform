from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2] / "data" / "golden" / "pompom-golden-v1"
TRUTH = ROOT / "truth" / "gold_truth.yaml"
POLICY = ROOT / "policy" / "policy_expectations_v1.7.yaml"
APPROVED_IDS = {
    "sticky-ball-01",
    "ball-crocodile-01",
    "upside-chair-01",
    "lamp-01",
    "snack-box-01",
    "box-cat-01",
    "spot-cat-01",
    "sneaky-door-01",
    "island-journal-01",
}
FAMILY5_DIMENSIONS = {
    "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_LOOP",
    "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_HOOK",
    "SPECIALIZED_RULE_APPLICABILITY_STUBBORN_RETURN_PAYOFF",
}
FAMILY5_EXPECTED = {
    "sticky-ball-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "ball-crocodile-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "upside-chair-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "lamp-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "snack-box-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "box-cat-01": {"LOOP": "APPLICABLE", "HOOK": "UNKNOWN", "PAYOFF": "APPLICABLE"},
    "spot-cat-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "sneaky-door-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
    "island-journal-01": {"LOOP": "NOT_APPLICABLE", "HOOK": "NOT_APPLICABLE", "PAYOFF": "NOT_APPLICABLE"},
}
REQUIRED_DIMENSIONS = {
    "HOOK",
    "GOAL",
    "CENTRAL_MECHANIC",
    "ACTIVE_ATTEMPT_COUNT",
    "DISTINCT_STRATEGY_COUNT",
    "DISTINCT_STRATEGIES",
    "ESCALATION",
    "PROGRESSION",
    "REALIZATION",
    "FAKE_RESOLUTION",
    "PAYOFF",
    "LOOP",
    "CHARACTER_PERFORMANCE",
    "PRODUCIBILITY",
    "SOUND_OFF_READABILITY",
    "TIMING_PACING",
    "CONTENT_FAMILY_FIT",
    "FIRST_FRAME_ANOMALY_INTENT",
    *FAMILY5_DIMENSIONS,
    "MECHANIC_INTERACTION",
    "RECURRENCE",
}
FAMILY_REVIEW_DIMENSIONS = {"GOAL", "ACTIVE_ATTEMPT_COUNT", "DISTINCT_STRATEGY_COUNT", "DISTINCT_STRATEGIES", "ESCALATION", "REALIZATION"}


def test_family5_uses_per_rule_applicability_dimensions() -> None:
    truth = yaml.safe_load(TRUTH.read_text(encoding="utf-8"))
    for asset_id, asset in truth["assets"].items():
        dimensions = asset["dimensions"]
        assert FAMILY5_DIMENSIONS <= dimensions.keys()
        assert "SPECIALIZED_RULE_APPLICABILITY" not in dimensions
        for dimension_name in FAMILY5_DIMENSIONS:
            dimension = dimensions[dimension_name]
            assert dimension["applicable"] is True
            assert dimension["expected"] in {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
            assert dimension["expected"] == FAMILY5_EXPECTED[asset_id][dimension_name.rsplit("_", 1)[-1]]
            assert dimension["reviewStatus"] == "APPROVED"


def test_gold_truth_is_independent_and_evidence_backed() -> None:
    truth = yaml.safe_load(TRUTH.read_text(encoding="utf-8"))
    assert truth["goldTruthVersion"] == "GOLD_TRUTH_V1"
    assert truth["evidenceReferencePolicy"]["excerptMode"] == "HUMAN_REVIEWED_VERBATIM_OR_SHORT_PARAPHRASE"
    assert set(truth["assets"]) == APPROVED_IDS
    for asset_id, asset in truth["assets"].items():
        assert REQUIRED_DIMENSIONS <= set(asset["dimensions"])
        for name, dimension in asset["dimensions"].items():
            assert {"expected", "applicable", "confidence", "evidenceReferences", "notes"} <= set(dimension)
            assert dimension["confidence"] in {"HIGH", "MEDIUM", "LOW"}
            if name in FAMILY_REVIEW_DIMENSIONS:
                assert dimension.get("reviewStatus") == "APPROVED", f"Family review missing: {asset_id}/{name}"
            if name == "REALIZATION":
                assert dimension.get("mode") in {"EXPLICIT", "IMPLICIT_BUT_OBSERVABLE", None}
            if name == "PAYOFF":
                assert dimension.get("sameRuleRelation") in {"SAME_RULE", "NOT_ESTABLISHED"}
            if dimension["confidence"] == "HIGH" and dimension["applicable"]:
                assert dimension["evidenceReferences"]
            if dimension["confidence"] in {"MEDIUM", "LOW"} and dimension.get("reviewStatus") != "APPROVED":
                assert "HUMAN_REVIEW_REQUIRED" in dimension["notes"]


def test_policy_expectations_are_separate_from_gold_truth() -> None:
    truth_text = TRUTH.read_text(encoding="utf-8")
    assert "creativeGrade" not in truth_text
    assert "familyScores" not in truth_text
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    assert policy["rulesetVersion"] == "1.7"
    assert set(policy["assets"]) == APPROVED_IDS
    assert all("corpusRole" not in str(value) for value in policy["assets"].values())
