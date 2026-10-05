"""Structured semantic evidence boundary.

This module intentionally returns explicit unavailable evidence until a
vision-capable provider is configured. That is safer than turning deterministic
motion evidence into invented story facts.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from .llm import get_provider
from .semantic_provider import SemanticAnalysisRequest, SemanticFrame
from .semantic_quality_gate import assess_semantic_evidence
from .semantic_routing import SemanticModelRoutingPolicy

SEMANTIC_ANALYZER_VERSION = "semantic-video-intelligence-v1"
SEMANTIC_SCHEMA_VERSION = "semantic-evidence-v1"


def unavailable_semantic_evidence(
    video_id: str | None,
    asset_hash: str,
    frame_selection: dict[str, Any],
    reason: str = "No vision-capable semantic provider is configured.",
) -> dict[str, Any]:
    return {
        "status": "NOT_EVALUATED",
        "evidenceId": None,
        "videoId": video_id,
        "variantId": None,
        "assetHash": asset_hash,
        "provider": None,
        "model": None,
        "modelVersion": None,
        "schemaVersion": SEMANTIC_SCHEMA_VERSION,
        "analyzerVersion": SEMANTIC_ANALYZER_VERSION,
        "frameSelection": frame_selection,
        "opening": {"status": "UNKNOWN"},
        "characters": [],
        "objects": [],
        "beats": [],
        "storyArc": {"arcType": "UNKNOWN", "sequence": [], "status": "UNKNOWN"},
        "emotionalArc": {"status": "UNKNOWN"},
        "payoff": {"status": "UNKNOWN"},
        "ending": {"status": "UNKNOWN"},
        "loop": {"status": "UNKNOWN"},
        "textEvidence": {"status": "UNKNOWN"},
        "semanticCoverage": "NONE",
        "confidence": None,
        "limitations": [reason],
        "provenance": {
            "selectedFrameTimestamps": [frame["timestampSeconds"] for frame in frame_selection.get("selectedFrames", [])],
            "frameSelectionVersion": frame_selection.get("version"),
            "inputTokens": None,
            "outputTokens": None,
            "estimatedCost": None,
            "actualCost": None,
            "requestId": None,
        },
    }


def analyse_semantic_video(
    frame_selection: dict[str, Any],
    canonical_characters: list[str] | None = None,
    cached_evidence: dict[str, Any] | None = None,
    semantic_requested: bool = False,
) -> dict[str, Any]:
    """Reuse fresh evidence or run exactly one structured vision pass."""
    cached = dict(cached_evidence or {})
    cache_selection = cached.get("frameSelection") if isinstance(cached.get("frameSelection"), dict) else {}
    if (
        str(cached.get("status") or "").upper() in {"COMPLETED", "PARTIAL", "CACHE_HIT"}
        and str(cached.get("assetHash") or "") == str(frame_selection.get("assetHash") or "")
        and str(cached.get("schemaVersion") or "") == SEMANTIC_SCHEMA_VERSION
        and cache_selection.get("version") == frame_selection.get("version")
        and isinstance(cached.get("provenance"), dict)
    ):
        cached["status"] = "CACHE_HIT"
        cached["frameSelection"] = frame_selection
        cached["provenance"] = {**dict(cached.get("provenance") or {}), "cacheHit": True, "cacheSource": "persisted-semantic-video-evidence", "providerCallCount": 0}
        return cached
    frames = [
        item.get("framePath")
        for item in frame_selection.get("selectedFrames", [])
        if item.get("frameAvailable") and item.get("framePath")
    ]
    if not frames:
        return unavailable_semantic_evidence(None, "", frame_selection, "No readable semantic frames were produced.")
    enabled = semantic_requested or any(os.getenv(name, "false").lower() == "true" for name in ("POMPOM_SEMANTIC_ENABLED", "SEMANTIC_VIDEO_AI_ENABLED"))
    if not enabled:
        return unavailable_semantic_evidence(None, "", frame_selection)
    try:
        selected = [item for item in frame_selection.get("selectedFrames", []) if item.get("frameAvailable") and item.get("framePath")]
        request = SemanticAnalysisRequest(
            asset_hash=str(frame_selection.get("assetHash") or ""),
            duration_seconds=float(frame_selection.get("durationSeconds") or 0.0),
            frames=tuple(SemanticFrame(
                timestamp_seconds=float(item["timestampSeconds"]),
                selection_reason=str(item.get("selectionReason", "OTHER")),
                image_path=str(item["framePath"]),
                image_hash=item.get("imageHash"),
                related_event_id=item.get("relatedEventId"),
                related_beat_id=item.get("relatedBeatId"),
            ) for item in selected),
            known_characters=tuple(canonical_characters or ()),
            temporal_events=tuple(frame_selection.get("temporalEvents") or ()),
            analysis_requirements=_semantic_prompt(canonical_characters or []),
        )
        policy = SemanticModelRoutingPolicy.from_environment()

        def run(selection, reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
            started = time.perf_counter()
            provider = get_provider(selection.provider, selection.model)
            if not hasattr(provider, "analyze"):
                raise TypeError(f"Provider {selection.provider} does not implement VisionLanguageModelProvider")
            result = provider.analyze(request)
            payload = dict(result.payload)
            quality = assess_semantic_evidence(payload, len(request.frames))
            usage = {
                **dict(result.usage),
                "provider": result.provider,
                "providerModel": result.model,
                "role": selection.role,
                "reason": reason,
                "latencyMs": round((time.perf_counter() - started) * 1000),
                "framesSent": len(request.frames),
                "imagePreparationProfile": os.getenv("SEMANTIC_IMAGE_PREPARATION_PROFILE", "STANDARD"),
                "cacheHit": False,
            }
            input_rate = os.getenv("SEMANTIC_INPUT_COST_PER_1M")
            output_rate = os.getenv("SEMANTIC_OUTPUT_COST_PER_1M")
            if input_rate and output_rate and usage.get("inputTokens") is not None and usage.get("outputTokens") is not None:
                usage["estimatedCost"] = round(
                    (float(usage["inputTokens"]) / 1_000_000) * float(input_rate)
                    + (float(usage["outputTokens"]) / 1_000_000) * float(output_rate),
                    6,
                )
            else:
                usage["estimatedCost"] = None
            return payload, {"usage": usage, "quality": quality, "selection": selection}

        payload, primary = run(policy.primary, policy.primary.reason)
        attempts = [{"selection": primary["selection"].__dict__, "quality": primary["quality"], "usage": primary["usage"]}]
        final = primary
        if primary["quality"]["qualityStatus"] == "INSUFFICIENT" and policy.fallback is not None:
            fallback_payload, fallback = run(policy.fallback, "PRIMARY_EVIDENCE_INSUFFICIENT")
            attempts.append({"selection": fallback["selection"].__dict__, "quality": fallback["quality"], "usage": fallback["usage"]})
            payload, final = fallback_payload, fallback
        payload.setdefault("status", "COMPLETED")
        payload.setdefault("schemaVersion", SEMANTIC_SCHEMA_VERSION)
        payload.setdefault("analyzerVersion", SEMANTIC_ANALYZER_VERSION)
        payload["frameSelection"] = frame_selection
        payload["provenance"] = {
            **dict(payload.get("provenance") or {}),
            "selectedFrameTimestamps": [frame["timestampSeconds"] for frame in frame_selection.get("selectedFrames", [])],
            "frameSelectionVersion": frame_selection.get("version"),
            **final["usage"],
            "routingPolicyVersion": policy.version,
            "routingMode": policy.mode,
            "primaryQuality": primary["quality"],
            "fallbackTriggered": len(attempts) > 1,
            "fallbackReason": "PRIMARY_EVIDENCE_INSUFFICIENT" if len(attempts) > 1 else None,
            "attempts": attempts,
            "finalSelectedRole": final["selection"].role,
        }
        payload.setdefault("limitations", [])
        return payload
    except ValueError as error:
        result = unavailable_semantic_evidence(None, "", frame_selection, "Semantic provider is not configured.")
        result["status"] = "NOT_CONFIGURED"
        result["provenance"]["configurationError"] = type(error).__name__
        return result
    except Exception as error:
        result = unavailable_semantic_evidence(None, "", frame_selection, f"Semantic provider failed: {type(error).__name__}")
        result["status"] = "SERVICE_ERROR"
        return result


def _semantic_system() -> str:
    return (
        "Return only JSON matching the requested evidence shape. Use only visible evidence in the supplied frames. "
        "Do not invent characters, objects, actions, emotions, text, or performance outcomes. "
        "Use UNKNOWN when evidence is insufficient. Canonical character names are limited to the provided registry."
    )


def _semantic_prompt(canonical_characters: list[str]) -> str:
    names = ", ".join(canonical_characters) if canonical_characters else "none supplied"
    return f'''Analyze this ordered representative frame set as one video. Canonical characters allowed: {names}.
Return JSON with these keys:
opening: {{primaryCharacterVisible, primaryObjectVisible, actionAlreadyStarted, conflictVisible, anomalyVisible, expressionReadable, textPresent, detectedText, semanticHookReadable, summary, confidence}}
characters: [{{canonicalName, present, role, firstSeenSeconds, lastSeenSeconds, actions, emotions, confidence}}]
objects: [{{objectType, label, role, stateChanges, interactions, firstSeen, lastSeen, confidence}}]
beats: [{{beatIndex, startSeconds, endSeconds, primaryCharacter, primaryAction, targetObject, interactionType, characterStateBefore, characterStateAfter, objectStateBefore, objectStateAfter, consequence, emotion, semanticDistinctnessFromPrevious, confidence}}]
storyArc: {{arcType, sequence, status}}
emotionalArc: {{openingEmotion, intermediateEmotions, endingEmotion, emotionShift, conflictPresent, conflictResolved, positiveResolution, confidence}}
payoff: {{payoffDetected, payoffStartSeconds, payoffEndSeconds, payoffType, consequenceDetected, stateChangeDetected, characterReaction, emotionalResolution, objectResolution, distinctFromPreviousBeat, confidence, summary, status}}
ending: {{status, summary}}
loop: {{openingSceneState, endingSceneState, samePrimaryCharacter, samePrimaryObject, objectStateCompatibility, characterStateCompatibility, spatialCompatibility, actionContinuity, mechanicContinuity, semanticLoopCompatibility, confidence, summary, status}}
textEvidence: {{textPresent, detectedText, readabilityConfidence, status}}
semanticCoverage: "FULL" or "PARTIAL"
confidence: number or null
'''
