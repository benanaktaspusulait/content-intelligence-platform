"""Structured semantic evidence boundary.

This module intentionally returns explicit unavailable evidence until a
vision-capable provider is configured. That is safer than turning deterministic
motion evidence into invented story facts.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .llm import get_provider
from .semantic_provider import SemanticAnalysisRequest, SemanticFrame

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
) -> dict[str, Any]:
    """Run exactly one structured vision pass when explicitly enabled."""
    frames = [
        item.get("framePath")
        for item in frame_selection.get("selectedFrames", [])
        if item.get("frameAvailable") and item.get("framePath")
    ]
    if not frames:
        return unavailable_semantic_evidence(None, "", frame_selection, "No readable semantic frames were produced.")
    if os.getenv("POMPOM_SEMANTIC_ENABLED", "false").lower() != "true":
        return unavailable_semantic_evidence(None, "", frame_selection)
    try:
        provider_name = os.getenv("POMPOM_SEMANTIC_PROVIDER") or os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        provider = get_provider(provider_name)
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
        if not hasattr(provider, "analyze"):
            raise TypeError(f"Provider {provider_name} does not implement VisionLanguageModelProvider")
        semantic_result = provider.analyze(request)
        payload = semantic_result.payload
        payload.setdefault("status", "COMPLETED")
        payload.setdefault("schemaVersion", SEMANTIC_SCHEMA_VERSION)
        payload.setdefault("analyzerVersion", SEMANTIC_ANALYZER_VERSION)
        payload["frameSelection"] = frame_selection
        payload["provenance"] = {
            **dict(payload.get("provenance") or {}),
            "selectedFrameTimestamps": [frame["timestampSeconds"] for frame in frame_selection.get("selectedFrames", [])],
            "frameSelectionVersion": frame_selection.get("version"),
            **semantic_result.usage,
            "provider": semantic_result.provider,
            "providerModel": semantic_result.model,
        }
        payload.setdefault("limitations", [])
        return payload
    except Exception as error:
        result = unavailable_semantic_evidence(None, "", frame_selection, f"Semantic provider failed: {type(error).__name__}")
        result["status"] = "FAILED"
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
