"""Deterministic provenance, beat normalization, and consistency checks for semantic evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEMANTIC_PROMPT_VERSION = "semantic-prompt-v2"
SEMANTIC_NORMALIZATION_VERSION = "semantic-normalization-v1"
SEMANTIC_BEAT_CANONICALIZER_VERSION = "semantic-beat-canonicalizer-v1"
SEMANTIC_HOOK_EVALUATOR_VERSION = "semantic-hook-evaluator-v1"
SEMANTIC_PAYOFF_EVALUATOR_VERSION = "semantic-payoff-evaluator-v1"
SEMANTIC_LOOP_EVALUATOR_VERSION = "semantic-loop-evaluator-v1"
SEMANTIC_CONTEXT_VERSION = "semantic-context-v1"
SEMANTIC_IMAGE_PREPARATION_VERSION = "semantic-image-preparation-v1"
SEMANTIC_SCHEMA_VERSION = "semantic-evidence-v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: Any) -> str:
    return sha256_bytes(_canonical_json(value).encode("utf-8"))


def sha256_file(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return sha256_bytes(Path(path).read_bytes())
    except OSError:
        return None


def build_frame_manifest(frame_selection: dict[str, Any]) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for index, frame in enumerate(frame_selection.get("selectedFrames") or []):
        path = str(frame.get("framePath") or "")
        frame_hash = frame.get("frameHash") or sha256_file(path)
        manifest.append({
            "frameIndex": index,
            "timestampSeconds": float(frame.get("timestampSeconds") or 0.0),
            "selectionReason": frame.get("selectionReason", "OTHER"),
            "sourceTemporalEvent": frame.get("relatedEventId"),
            "sourcePlanBeat": frame.get("relatedBeatId"),
            "frameHash": frame_hash,
            "preparedImageHash": frame.get("preparedImageHash") or frame_hash,
            "width": frame.get("width"),
            "height": frame.get("height"),
            "frameAvailable": bool(frame.get("frameAvailable")),
        })
    return manifest


def request_fingerprint(
    frame_selection: dict[str, Any],
    provider: str,
    model: str,
    policy_version: str,
    known_characters: list[str] | None,
    transcript_context: list[dict[str, Any]] | None = None,
    planned_context: dict[str, Any] | None = None,
    prompt_version: str = SEMANTIC_PROMPT_VERSION,
    schema_version: str = SEMANTIC_SCHEMA_VERSION,
    image_preparation_profile: str = "STANDARD",
) -> tuple[str, dict[str, Any]]:
    manifest = build_frame_manifest(frame_selection)
    effective = {
        "assetHash": frame_selection.get("assetHash"),
        "provider": provider,
        "model": model,
        "semanticPromptVersion": prompt_version,
        "semanticSchemaVersion": schema_version,
        "frameSelectorVersion": frame_selection.get("version"),
        "orderedFrames": [
            {"frameHash": item.get("frameHash"), "timestampSeconds": item.get("timestampSeconds")}
            for item in manifest
        ],
        "imagePreparationVersion": SEMANTIC_IMAGE_PREPARATION_VERSION,
        "imagePreparationProfile": image_preparation_profile,
        "canonicalContextVersion": SEMANTIC_CONTEXT_VERSION,
        "characterContext": sorted(known_characters or []),
        "planContextHash": sha256_text(planned_context or {}),
        "transcriptContextHash": sha256_text(transcript_context or []),
        "temporalEventContextHash": sha256_text(frame_selection.get("temporalEvents") or []),
        "requestPolicyVersion": policy_version,
    }
    return sha256_text(effective), effective


def _same_family(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get("primaryCharacter") == right.get("primaryCharacter")
        and left.get("targetObject") == right.get("targetObject")
        and left.get("primaryAction") == right.get("primaryAction")
        and left.get("objectStateBefore") == right.get("objectStateBefore")
        and left.get("objectStateAfter") == right.get("objectStateAfter")
        and left.get("consequence") == right.get("consequence")
    )


def canonicalize_beats(raw_beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge adjacent provider segments that describe one continuous visual beat."""
    canonical: list[dict[str, Any]] = []
    for raw in raw_beats:
        if not isinstance(raw, dict):
            continue
        beat = dict(raw)
        beat["supportingFrames"] = list(raw.get("supportingFrames") or [])
        if canonical and _same_family(canonical[-1], beat):
            previous = canonical[-1]
            previous["endSeconds"] = max(float(previous.get("endSeconds") or 0.0), float(beat.get("endSeconds") or 0.0))
            previous["confidence"] = min(float(previous.get("confidence") or 0.0), float(beat.get("confidence") or 0.0))
            previous["supportingFrames"] = list(dict.fromkeys(previous["supportingFrames"] + beat["supportingFrames"]))
            continue
        beat["canonicalBeatIndex"] = len(canonical)
        canonical.append(beat)
    return canonical


def validate_consistency(evidence: dict[str, Any]) -> dict[str, Any]:
    opening = evidence.get("opening") if isinstance(evidence.get("opening"), dict) else {}
    payoff = evidence.get("payoff") if isinstance(evidence.get("payoff"), dict) else {}
    loop = evidence.get("loop") if isinstance(evidence.get("loop"), dict) else {}
    contradictions: list[str] = []
    if opening.get("semanticHookReadability") == "NOT_READABLE" and opening.get("problemOrAnomalyReadable") is True:
        contradictions.append("hook_not_readable_but_anomaly_readable")
    if str(loop.get("status", "")).upper() == "CONSISTENT" and all(loop.get(key) is False for key in ("samePrimaryCharacter", "samePrimaryObject", "restartPlausibility")):
        contradictions.append("consistent_loop_without_identity_or_restart_support")
    if str(payoff.get("status", "")).upper() == "COMPLETED" and payoff.get("payoffDetected") is False and payoff.get("stateChangeDetected") is False:
        contradictions.append("completed_payoff_without_observed_resolution")
    unsupported = []
    if not opening or opening.get("semanticHookReadability") in {None, "UNKNOWN"}:
        unsupported.append("hook")
    if not payoff or payoff.get("status") in {None, "UNKNOWN"}:
        unsupported.append("payoff")
    if not loop or loop.get("status") in {None, "UNKNOWN"}:
        unsupported.append("loop")
    status = "INVALID" if contradictions else ("QUESTIONABLE" if unsupported else "VALID")
    return {
        "status": status,
        "contradictions": contradictions,
        "unsupportedFields": unsupported,
        "version": "semantic-consistency-validator-v1",
    }
