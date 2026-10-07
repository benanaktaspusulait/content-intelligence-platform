from __future__ import annotations

import pytest

from app.golden.ci_gate import GoldenGateFailure, evaluate_ci_gate, verify_manifest_hashes


def test_ci_gate_passes_only_with_zero_new_regressions() -> None:
    assert evaluate_ci_gate({"newSemanticRegressions": 0, "unexpectedPolicyRegressions": 0}) == "PASS"
    assert evaluate_ci_gate({"newSemanticRegressions": 1, "unexpectedPolicyRegressions": 0}) == "FAIL"
    assert evaluate_ci_gate({"newSemanticRegressions": 0, "unexpectedPolicyRegressions": 1}) == "FAIL"


def test_ci_gate_fails_on_hash_drift() -> None:
    with pytest.raises(GoldenGateFailure, match="GOLDEN_FIXTURE_DRIFT"):
        verify_manifest_hashes({"assets": [{"goldenId": "a", "promptFile": "missing", "promptHash": "x"}]}, base_directory=None)


def test_ci_gate_rejects_live_provider_mode() -> None:
    with pytest.raises(GoldenGateFailure, match="LIVE_PROVIDER_NOT_ALLOWED"):
        evaluate_ci_gate({"newSemanticRegressions": 0, "unexpectedPolicyRegressions": 0}, provider_mode="LIVE")


def test_ci_gate_fails_closed_when_required_metrics_are_missing_or_malformed() -> None:
    with pytest.raises(GoldenGateFailure, match="INVALID_GATE_METRICS"):
        evaluate_ci_gate({})
    with pytest.raises(GoldenGateFailure, match="INVALID_GATE_METRICS"):
        evaluate_ci_gate({"newSemanticRegressions": "0", "unexpectedPolicyRegressions": 0})
    with pytest.raises(GoldenGateFailure, match="INVALID_GATE_METRICS"):
        evaluate_ci_gate({"newSemanticRegressions": False, "unexpectedPolicyRegressions": 0})
