from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


class GoldenGateFailure(RuntimeError):
    """Raised when deterministic Golden release conditions are not satisfied."""


def verify_manifest_hashes(
    manifest: dict[str, Any],
    base_directory: str | Path | None,
    approved_hashes: dict[str, str] | None = None,
) -> None:
    if base_directory is None:
        raise GoldenGateFailure("GOLDEN_FIXTURE_DRIFT: manifest base directory is missing")
    root = Path(base_directory)
    for asset in manifest.get("assets", []):
        golden_id = str(asset["goldenId"])
        expected_hash = asset.get("promptHash")
        if approved_hashes is not None and approved_hashes.get(golden_id) != expected_hash:
            raise GoldenGateFailure(f"GOLDEN_FIXTURE_DRIFT: manifest hash contract mismatch for {golden_id}")
        prompt_path = root / str(asset["promptFile"])
        if not prompt_path.is_file():
            raise GoldenGateFailure(f"GOLDEN_FIXTURE_DRIFT: missing {golden_id}")
        actual = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
        if actual != expected_hash or (approved_hashes is not None and actual != approved_hashes.get(golden_id)):
            raise GoldenGateFailure(f"GOLDEN_FIXTURE_DRIFT: hash mismatch for {golden_id}")


def evaluate_ci_gate(report: dict[str, Any], *, provider_mode: str = "FROZEN_DETERMINISTIC") -> str:
    if provider_mode != "FROZEN_DETERMINISTIC":
        raise GoldenGateFailure("LIVE_PROVIDER_NOT_ALLOWED: deterministic Golden CI requires frozen mode")
    required = ("newSemanticRegressions", "unexpectedPolicyRegressions")
    if any(
        key not in report
        or isinstance(report[key], bool)
        or not isinstance(report[key], int)
        or report[key] < 0
        for key in required
    ):
        raise GoldenGateFailure("INVALID_GATE_METRICS: release counters must be non-negative integers")
    if report["newSemanticRegressions"] != 0:
        return "FAIL"
    if report["unexpectedPolicyRegressions"] != 0:
        return "FAIL"
    return "PASS"
