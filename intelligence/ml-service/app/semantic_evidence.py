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
        prompt = _semantic_prompt(canonical_characters or [])
        response, usage = provider.complete_images(prompt, [str(frame) for frame in frames], system=_semantic_system())
        payload = json.loads(response)
        if not isinstance(payload, dict):
            raise ValueError("Semantic provider response must be an object")
        payload.setdefault("status", "COMPLETED")
        payload.setdefault("schemaVersion", SEMANTIC_SCHEMA_VERSION)
        payload.setdefault("analyzerVersion", SEMANTIC_ANALYZER_VERSION)
        payload["frameSelection"] = frame_selection
        payload["provenance"] = {
            **dict(payload.get("provenance") or {}),
            "selectedFrameTimestamps": [frame["timestampSeconds"] for frame in frame_selection.get("selectedFrames", [])],
            "frameSelectionVersion": frame_selection.get("version"),
            **usage,
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
