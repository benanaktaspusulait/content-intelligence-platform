"""Evidence reliability gate used only for model routing.

This deliberately measures evidence completeness and consistency, never creative
quality. A weak payoff or loop can be a valid high-confidence result and must not
by itself trigger another billable vision call.
"""

from __future__ import annotations

from typing import Any


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def assess_semantic_evidence(payload: dict[str, Any], frame_count: int) -> dict[str, Any]:
    reasons: list[str] = []
    opening = payload.get("opening") if isinstance(payload.get("opening"), dict) else {}
    ending = payload.get("ending") if isinstance(payload.get("ending"), dict) else {}
    payoff = payload.get("payoff") if isinstance(payload.get("payoff"), dict) else {}
    loop = payload.get("loop") if isinstance(payload.get("loop"), dict) else {}
    characters = payload.get("characters") if isinstance(payload.get("characters"), list) else []
    beats = payload.get("beats") if isinstance(payload.get("beats"), list) else []

    coverage = _status(payload.get("semanticCoverage"))
    schema_ok = isinstance(payload, dict) and bool(payload.get("schemaVersion") or payload.get("semanticCoverage"))
    character_resolved = bool(characters) or bool(opening.get("primaryCharacterVisible"))
    opening_resolved = bool(opening) and bool(opening.get("summary") or opening.get("actionAlreadyStarted") is not None)
    ending_resolved = _status(ending.get("status")) not in {"UNKNOWN", "NOT_EVALUATED", ""} or bool(ending.get("summary"))
    payoff_resolved = _status(payoff.get("status")) not in {"UNKNOWN", "NOT_EVALUATED", ""} or payoff.get("payoffDetected") is not None
    loop_resolved = _status(loop.get("status")) not in {"UNKNOWN", "NOT_EVALUATED", ""} or loop.get("semanticLoopCompatibility") is not None

    internal_consistency = True
    for beat in beats:
        if not isinstance(beat, dict):
            internal_consistency = False
            break
        start, end = beat.get("startSeconds"), beat.get("endSeconds")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end < start:
            internal_consistency = False
            break

    if not schema_ok:
        reasons.append("SCHEMA_PARTIAL")
    if not frame_count or frame_count < 4:
        reasons.append("FRAME_COVERAGE_INSUFFICIENT")
    if not character_resolved:
        reasons.append("PRIMARY_CHARACTER_UNRESOLVED")
    if not opening_resolved:
        reasons.append("OPENING_UNRESOLVED")
    if not ending_resolved:
        reasons.append("ENDING_UNRESOLVED")
    if not internal_consistency:
        reasons.append("INTERNAL_CONTRADICTION")

    # Payoff and loop are intentionally not hard blockers: NOT_ESTABLISHED or
    # UNKNOWN can be truthful evidence for a format without a clear payoff.
    resolved_count = sum((character_resolved, opening_resolved, ending_resolved, payoff_resolved, loop_resolved))
    confidence = payload.get("confidence")
    confidence_ok = isinstance(confidence, (int, float)) and 0 <= confidence <= 1 and confidence >= 0.55
    if not confidence_ok:
        reasons.append("LOW_CONFIDENCE")

    if reasons or coverage == "NONE":
        quality_status = "INSUFFICIENT"
    elif coverage == "PARTIAL" or resolved_count < 4:
        quality_status = "MARGINAL"
    else:
        quality_status = "SUFFICIENT"
    return {
        "qualityStatus": quality_status,
        "coverage": coverage,
        "characterResolved": character_resolved,
        "openingResolved": opening_resolved,
        "beatCoverage": bool(beats),
        "payoffResolved": payoff_resolved,
        "endingResolved": ending_resolved,
        "loopResolved": loop_resolved,
        "criticalUnknownCount": sum(not value for value in (character_resolved, opening_resolved, ending_resolved)),
        "internalConsistency": internal_consistency,
        "frameCoverageAdequate": frame_count >= 4,
        "confidence": confidence,
        "qualityReasons": reasons,
        "version": "semantic-evidence-quality-gate-v1",
    }
