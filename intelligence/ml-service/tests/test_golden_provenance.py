from __future__ import annotations

from pathlib import Path

import yaml

from app.golden.deterministic_runner import run_golden_asset
from app.golden.provenance import build_golden_fingerprint


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "golden" / "pompom-golden-v1" / "manifest.yaml"
RULESET = ROOT / "data" / "rules" / "RULESET_1.7.yaml"


def _manifest_asset() -> dict:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return next(item for item in manifest["assets"] if item["goldenId"] == "sticky-ball-01")


def test_fingerprint_has_explicit_unknown_versions_and_excludes_corpus_role() -> None:
    asset = _manifest_asset()
    fingerprint = build_golden_fingerprint(asset, ruleset_path=RULESET)

    assert fingerprint.golden_set_version == "POMPOM_GOLDEN_V1"
    assert fingerprint.ruleset_version == "1.7"
    assert fingerprint.canonical_evidence_version == "canonical-attempt-evidence-v2"
    assert fingerprint.semantic_prompt_version in {"UNKNOWN", None}
    assert fingerprint.semantic_schema_version in {"UNKNOWN", None}
    assert fingerprint.report_renderer_version in {"UNKNOWN", None}
    assert fingerprint.frontend_representation_version in {"UNKNOWN", None}
    assert "corpusRole" not in fingerprint.engine_input_metadata


def test_deterministic_runner_uses_prompt_text_without_corpus_role() -> None:
    asset = _manifest_asset()
    result = run_golden_asset(asset, manifest_path=MANIFEST, ruleset_path=RULESET)

    assert result.golden_id == "sticky-ball-01"
    assert result.engine_input == {"prompt": result.prompt_text}
    assert "corpusRole" not in result.engine_input
    assert "WINNER" not in str(result.engine_input)
    assert result.fingerprint.ruleset_version == "1.7"
    assert result.provider_mode == "FROZEN_DETERMINISTIC"


def test_frozen_semantic_attempt_helper_is_available_for_multi_attempt_rules() -> None:
    from app.golden.deterministic_runner import _semantic_attempt_judgments

    result = _semantic_attempt_judgments([{"action": "pull"}, {"action": "squeeze"}])
    assert [item["index"] for item in result] == [0, 1]
    assert all(item["is_executable"] for item in result)
