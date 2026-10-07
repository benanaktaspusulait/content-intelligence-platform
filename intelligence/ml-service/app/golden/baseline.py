from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .comparator import extract_dimension_values
from .deterministic_runner import GoldenRun, run_golden_asset


def _load_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _asset_by_id(manifest: dict[str, Any], golden_id: str) -> dict[str, Any]:
    try:
        return next(item for item in manifest["assets"] if item["goldenId"] == golden_id)
    except StopIteration as error:
        raise KeyError(f"Golden asset not found: {golden_id}") from error


def _known_issues(asset: dict[str, Any], result: GoldenRun) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    for code in [*asset.get("knownIssues", []), *(item.get("code") for item in result.known_issues)]:
        if not code or code in seen:
            continue
        seen.add(str(code))
        issues.append({"code": str(code), "source": "manifest" if code in asset.get("knownIssues", []) else "runner"})
    return issues


def capture_baseline_asset(
    golden_id: str,
    manifest_path: str | Path,
    ruleset_path: str | Path,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    asset = _asset_by_id(manifest, golden_id)
    result = run_golden_asset(asset, manifest_path=manifest_path, ruleset_path=ruleset_path)
    snapshot = result.to_dict()
    snapshot["corpusRole"] = asset["corpusRole"]
    snapshot["displayName"] = asset["displayName"]
    snapshot["knownIssues"] = _known_issues(asset, result)
    snapshot["dimensionValues"] = extract_dimension_values(snapshot)
    return snapshot


def capture_baseline(
    manifest_path: str | Path,
    ruleset_path: str | Path,
) -> dict[str, Any]:
    manifest = _load_manifest(manifest_path)
    assets = {
        item["goldenId"]: capture_baseline_asset(item["goldenId"], manifest_path, ruleset_path)
        for item in manifest["assets"]
    }
    first = next(iter(assets.values()))
    return {
        "baselineVersion": "BASELINE_V1_7",
        "goldenSetVersion": manifest["goldenSetVersion"],
        "rulesetVersion": "1.7",
        "fingerprint": first["fingerprint"],
        "assets": assets,
    }


def write_baseline(
    manifest_path: str | Path,
    ruleset_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    baseline = capture_baseline(manifest_path, ruleset_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return baseline


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Capture a deterministic POMPOM Golden baseline")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--ruleset", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    baseline = write_baseline(args.manifest, args.ruleset, args.out)
    print(json.dumps({"assets": len(baseline["assets"]), "rulesetVersion": baseline["rulesetVersion"]}))


if __name__ == "__main__":
    main()
