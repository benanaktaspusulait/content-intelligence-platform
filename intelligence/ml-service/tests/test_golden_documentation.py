from __future__ import annotations

from pathlib import Path


DOCS = Path(__file__).resolve().parents[2] / "docs"
REQUIRED = {
    "GOLDEN_CALIBRATION_AUDIT.md": ["EXISTS", "PARTIAL", "performance", "intelligence/docs"],
    "GOLDEN_CALIBRATION_ARCHITECTURE.md": ["Gold Truth", "Policy Expectation", "corpusRole", "FROZEN_DETERMINISTIC"],
    "GOLDEN_V17_BASELINE_REPORT.md": ["BASELINE_V1_7", "NEW semantic regressions", "Ruleset: `1.7`"],
    "GOLDEN_REGRESSION_WORKFLOW.md": ["NEW SEMANTIC REGRESSIONS = 0", "OpenAI", "GOLDEN_FIXTURE_DRIFT"],
}


def test_calibration_documents_are_tracked_area_contracts() -> None:
    for name, phrases in REQUIRED.items():
        text = (DOCS / name).read_text(encoding="utf-8")
        for phrase in phrases:
            assert phrase in text, f"{name} missing {phrase!r}"
