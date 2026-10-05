"""Canonical local fusion of V5 evidence and persisted semantic evidence."""

from __future__ import annotations

from typing import Any


def _map(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _status(value: Any) -> str:
    return str(value or "UNKNOWN").upper()


def _semantic_available(semantic: dict[str, Any]) -> bool:
    return _status(semantic.get("status")) in {"COMPLETED", "PARTIAL", "CACHE_HIT"} and bool(semantic.get("provenance"))


def fuse_canonical_assessments(temporal: dict[str, Any], semantic: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical interpretation without changing raw evidence."""
    opening = _map(semantic.get("opening"))
    payoff = _map(semantic.get("payoff"))
    loop = _map(semantic.get("loop"))
    beats = semantic.get("beats") if isinstance(semantic.get("beats"), list) else []
    semantic_available = _semantic_available(semantic)

    visual_opening = _map(temporal.get("hook"))
    visual_payoff = _map(temporal.get("payoff"))
    visual_loop = _map(temporal.get("loop"))
    visual_similarity = float(visual_loop.get("visualEndpointSimilarity") or 0.0)

    hook_readable = opening.get("semanticHookReadable")
    if semantic_available and hook_readable is True:
        hook_strength = "STRONG" if float(visual_opening.get("visualOpeningActivity") or 0.0) >= 0.30 else "MODERATE"
        hook_summary = "The opening situation is semantically readable in the supplied frames."
    elif semantic_available and hook_readable is False:
        hook_strength = "WEAK"
        hook_summary = "The opening frames do not establish a readable semantic situation quickly."
    else:
        hook_strength = str(visual_opening.get("status") or "UNKNOWN")
        hook_summary = str(visual_opening.get("reason") or "Semantic opening evidence is unavailable.")
    hook = {
        "version": "hook-assessment-v1",
        "status": "AVAILABLE" if semantic_available or visual_opening else "UNKNOWN",
        "strength": hook_strength,
        "coverage": "SEMANTIC_AND_VISUAL" if semantic_available else "VISUAL_ONLY",
        "semanticReadability": hook_readable if semantic_available else None,
        "visualOpeningSupport": visual_opening.get("visualOpeningActivity"),
        "expressionSupport": opening.get("expressionReadable") if semantic_available else None,
        "textSupport": opening.get("textPresent") if semantic_available else None,
        "transcriptSupport": "NOT_AVAILABLE",
        "planAlignment": "NOT_AVAILABLE",
        "summary": hook_summary,
        "limitations": [] if semantic_available else ["Semantic opening evidence is unavailable."],
        "evidenceReferences": ["V5 temporalProfile.hook", "semanticVideoEvidence.opening"],
    }

    semantic_payoff_status = _status(payoff.get("status")) if semantic_available else "UNKNOWN"
    motion_rebound = str(visual_payoff.get("motionRebound") or "NOT_ESTABLISHED")
    if semantic_payoff_status in {"OBSERVED", "OBSERVED_WITH_PARTIAL_TIMING", "PARTIAL"}:
        payoff_strength = "STRONG" if semantic_payoff_status == "OBSERVED" else "MODERATE"
        payoff_summary = "Semantic payoff evidence is observed; timing is partial." if semantic_payoff_status != "OBSERVED" else "Semantic payoff evidence is observed."
    elif semantic_payoff_status in {"NOT_ESTABLISHED", "WEAK"}:
        payoff_strength = "NOT_ESTABLISHED"
        payoff_summary = "The semantic evidence does not establish a distinct payoff."
    else:
        payoff_strength = "UNKNOWN"
        payoff_summary = "Payoff cannot be resolved from the available evidence."
    canonical_payoff = {
        "version": "payoff-assessment-v1",
        "strength": payoff_strength,
        "semanticStatus": semantic_payoff_status,
        "visualEndingEmphasis": visual_payoff.get("visualEndingEmphasis", "UNKNOWN"),
        "motionRebound": motion_rebound,
        "emotionalResolution": payoff.get("emotionalResolution") if semantic_available else None,
        "stateChange": payoff.get("stateChangeDetected") if semantic_available else None,
        "planAlignment": "NOT_AVAILABLE",
        "timingConfidence": payoff.get("confidence") if semantic_available else None,
        "summary": payoff_summary,
        "limitations": [] if semantic_available else ["Semantic payoff evidence is unavailable."],
    }

    semantic_loop_status = _status(loop.get("status")) if semantic_available else "UNKNOWN"
    visual_strength = "STRONG" if visual_similarity >= 0.90 else "MODERATE" if visual_similarity >= 0.75 else "WEAK"
    if semantic_loop_status in {"PARTIAL", "MODERATE"}:
        loop_strength = "MODERATE" if visual_strength in {"STRONG", "MODERATE"} else "WEAK"
    elif semantic_loop_status in {"STRONG", "EXCELLENT"}:
        loop_strength = "STRONG"
    elif semantic_loop_status in {"WEAK", "NO_LOOP"}:
        loop_strength = "WEAK" if visual_strength != "WEAK" else "NO_LOOP"
    else:
        loop_strength = visual_strength if not semantic_available else "UNKNOWN"
    canonical_loop = {
        "version": "loop-assessment-v1",
        "strength": loop_strength,
        "visualEvidence": visual_strength,
        "semanticEvidence": semantic_loop_status,
        "actionContinuity": loop.get("actionContinuity") if semantic_available else None,
        "planIntent": "NOT_AVAILABLE",
        "summary": f"Visual endpoint evidence is {visual_strength.lower()}; semantic loop evidence is {semantic_loop_status.lower()}.",
        "limitations": [] if semantic_available else ["Semantic loop evidence is unavailable."],
    }

    temporal_events = temporal.get("temporalActivityEvents") if isinstance(temporal.get("temporalActivityEvents"), list) else []
    joined = []
    for event in temporal_events:
        start = float(event.get("startSeconds") or 0.0)
        end = float(event.get("endSeconds") or start)
        overlaps = []
        for beat in beats:
            beat_start, beat_end = beat.get("startSeconds"), beat.get("endSeconds")
            if isinstance(beat_start, (int, float)) and isinstance(beat_end, (int, float)) and beat_start <= end + 0.25 and beat_end >= start - 0.25:
                overlaps.append(beat)
        joined.append({**event, "semanticContextAvailable": bool(overlaps), "semanticBeats": overlaps})
    contextual = "LIKELY_PURPOSEFUL_HOLD" if any(item.get("semanticContextAvailable") for item in joined) else "NEUTRAL_DIP" if joined else "UNKNOWN"
    temporal_assessment = {
        "version": "temporal-structure-assessment-v1",
        "status": "AVAILABLE" if joined else "UNKNOWN",
        "interpretation": contextual,
        "events": joined,
        "summary": "Temporal events are joined to overlapping semantic beats." if joined and semantic_available else "No semantic context was available for temporal events.",
        "limitations": [] if joined and semantic_available else ["Contextual semantic beat evidence is unavailable."],
    }

    applicable = [hook["status"] != "UNKNOWN", bool(beats), canonical_payoff["strength"] != "UNKNOWN", canonical_loop["strength"] != "UNKNOWN", temporal_assessment["status"] != "UNKNOWN"]
    coverage = round(100 * sum(applicable) / len(applicable))
    missing = [name for name, ok in zip(("hook", "beats", "payoff", "loop", "temporal structure"), applicable) if not ok]
    return {
        "version": "semantic-fusion-v1",
        "hook": hook,
        "payoff": canonical_payoff,
        "loop": canonical_loop,
        "temporalStructure": temporal_assessment,
        "planRenderFidelity": {"status": "NOT_AVAILABLE", "reason": "No resolved production plan or matching source prompt was available in this analysis."},
        "coverage": {"percent": coverage, "missing": missing},
        "semanticEvidenceAvailable": semantic_available,
    }
