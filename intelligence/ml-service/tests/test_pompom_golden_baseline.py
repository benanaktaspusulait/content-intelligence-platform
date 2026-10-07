from __future__ import annotations

from pathlib import Path

from app.golden.baseline import capture_baseline, capture_baseline_asset


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "golden" / "pompom-golden-v1" / "manifest.yaml"
RULESET = ROOT / "data" / "rules" / "RULESET_1.7.yaml"
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


def test_baseline_has_all_nine_assets_and_current_ruleset() -> None:
    baseline = capture_baseline(MANIFEST, RULESET)
    assert set(baseline["assets"]) == APPROVED_IDS
    assert baseline["fingerprint"]["ruleset_version"] == "1.7"
    assert len(baseline["assets"]) == 9


def test_baseline_preserves_parser_incompatibility_as_observed_issue() -> None:
    asset = capture_baseline_asset("box-cat-01", MANIFEST, RULESET)
    assert asset["goldenId"] == "box-cat-01"
    assert asset["status"] in {"OK", "ANALYSIS_ERROR", "PARSER_TIMEOUT"}
    assert asset["knownIssues"]
    assert any("TIMELINE_PARSE_INCOMPATIBLE" in issue["code"] for issue in asset["knownIssues"])
    assert "corpusRole" not in asset["engineInput"]
