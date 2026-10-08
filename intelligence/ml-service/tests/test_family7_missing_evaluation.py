"""Task 4 tests for runtime missing-evaluation snapshot semantics."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.golden import deterministic_runner
from app.golden.deterministic_runner import GoldenAnalysisTimeout, run_golden_asset
from app.quality.contracts import RuleOutcome

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "data" / "golden" / "pompom-golden-v1"
MANIFEST = GOLDEN_ROOT / "manifest.yaml"
RULESET = ROOT / "data" / "rules" / "RULESET_1.7.yaml"


def asset(asset_id: str) -> dict[str, object]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return next(item for item in manifest["assets"] if item["goldenId"] == asset_id)


def test_ok_snapshot_exposes_status_aware_aggregation_without_changing_rule_rows() -> None:
    result = run_golden_asset(asset("sticky-ball-01"), manifest_path=MANIFEST, ruleset_path=RULESET)
    assert result.status == "OK"
    assert result.report is not None

    snapshot = result.to_dict()
    aggregation = snapshot["aggregation"]
    evaluations = result.report.evaluations
    assert aggregation["passCount"] == sum(item.outcome is RuleOutcome.PASS for item in evaluations)
    assert aggregation["failCount"] == sum(item.outcome is RuleOutcome.FAIL for item in evaluations)
    assert aggregation["unknownCount"] == sum(item.outcome is RuleOutcome.UNKNOWN for item in evaluations)
    assert aggregation["notApplicableCount"] == sum(item.outcome is RuleOutcome.NOT_APPLICABLE for item in evaluations)
    assert aggregation["serviceErrorCount"] == sum(item.outcome is RuleOutcome.SERVICE_ERROR for item in evaluations)
    assert aggregation["notEvaluatedCount"] == 0
    assert snapshot["report"]["evaluations"]


def test_parser_timeout_snapshot_is_not_evaluated_with_null_score(monkeypatch) -> None:
    def raise_timeout(_function, _timeout_seconds):
        raise GoldenAnalysisTimeout("synthetic parser timeout")

    monkeypatch.setattr(deterministic_runner, "_bounded_call", raise_timeout)
    result = run_golden_asset(asset("upside-chair-01"), manifest_path=MANIFEST, ruleset_path=RULESET)

    assert result.status == "PARSER_TIMEOUT"
    snapshot = result.to_dict()
    aggregation = snapshot["aggregation"]
    assert aggregation["score"] is None
    assert aggregation["aggregationState"] == "NO_EVALUATED_ITEMS"
    assert aggregation["notEvaluatedCount"] == 8
    assert aggregation["passCount"] == 0
    assert aggregation["failCount"] == 0
    assert snapshot["error"] == "synthetic parser timeout"
    assert snapshot["report"] is None
    assert snapshot["assessment"] is None
    assert snapshot["apiReport"] is None
