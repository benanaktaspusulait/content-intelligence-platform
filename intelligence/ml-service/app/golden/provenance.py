from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..config import settings
from ..llm.provider import get_provider_identity
from ..quality.canonical_evidence import CANONICAL_EVIDENCE_VERSION


@dataclass(frozen=True)
class GoldenFingerprint:
    golden_set_version: str
    gold_label_version: str
    prompt_hash: str
    parser_version: str
    canonical_evidence_version: str
    ruleset_version: str
    rule_engine_version: str
    assessment_version: str
    scoring_version: str
    semantic_provider: str
    semantic_model_version: str
    semantic_prompt_version: str
    semantic_schema_version: str
    report_renderer_version: str
    frontend_representation_version: str
    git_commit: str
    engine_input_metadata: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unknown(value: object) -> str:
    return str(value) if value not in {None, ""} else "UNKNOWN"


def _git_commit() -> str:
    repository_root = Path(__file__).resolve().parents[4]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"
    return _unknown(result.stdout.strip())


def build_golden_fingerprint(
    asset: dict[str, Any],
    *,
    ruleset_path: str | Path,
    golden_set_version: str = "POMPOM_GOLDEN_V1",
    gold_label_version: str = "GOLD_LABELS_V1",
) -> GoldenFingerprint:
    try:
        provider, model = get_provider_identity()
    except Exception:
        provider, model = "UNKNOWN", "UNKNOWN"
    ruleset_version = str(ruleset_path).rsplit("RULESET_", 1)[-1].removesuffix(".yaml")
    return GoldenFingerprint(
        golden_set_version=golden_set_version,
        gold_label_version=gold_label_version,
        prompt_hash=_unknown(asset.get("promptHash")),
        parser_version=_unknown(getattr(settings, "parser_version", None)),
        canonical_evidence_version=CANONICAL_EVIDENCE_VERSION,
        ruleset_version=ruleset_version,
        rule_engine_version=_unknown(getattr(settings, "rule_engine_version", None)),
        assessment_version="pre-render-assessment-v2",
        scoring_version="quality-scorer-v2",
        semantic_provider=_unknown(provider),
        semantic_model_version=_unknown(model),
        semantic_prompt_version="UNKNOWN",
        semantic_schema_version="UNKNOWN",
        report_renderer_version="UNKNOWN",
        frontend_representation_version="UNKNOWN",
        git_commit=_git_commit(),
        engine_input_metadata={
            "goldenId": _unknown(asset.get("goldenId")),
            "promptHash": _unknown(asset.get("promptHash")),
        },
    )
