"""Deterministic representative-frame selection for semantic video analysis.

The selector is deliberately independent from the V5 score. It produces a small,
auditable set of frame assets for a future/optional vision pass and records why
each frame was selected.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2

from .config import settings

FRAME_SELECTION_VERSION = "semantic-frame-selection-v1"
DEFAULT_MAX_FRAMES = 14
MIN_FRAME_GAP_SECONDS = 0.18


def _add(
    candidates: list[dict[str, Any]],
    timestamp: float,
    reason: str,
    event_id: str | None = None,
    beat_id: str | None = None,
) -> None:
    if not math.isfinite(timestamp) or timestamp < 0:
        return
    candidates.append({
        "timestampSeconds": round(timestamp, 3),
        "selectionReason": reason,
        "relatedEventId": event_id,
        "relatedBeatId": beat_id,
    })


def _deduplicate(candidates: list[dict[str, Any]], max_frames: int, duration: float) -> list[dict[str, Any]]:
    candidates.sort(key=lambda item: (float(item["timestampSeconds"]), str(item["selectionReason"])))
    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        timestamp = float(candidate["timestampSeconds"])
        if timestamp > duration:
            continue
        if selected and timestamp - float(selected[-1]["timestampSeconds"]) < MIN_FRAME_GAP_SECONDS:
            # Prefer an event/beat explanation over a generic anchor when the
            # same visual moment was selected for multiple reasons.
            if candidate["selectionReason"] not in {"OPENING_ANCHOR", "ENDING_ANCHOR"}:
                selected[-1] = candidate
            continue
        selected.append(candidate)
    if len(selected) <= max_frames:
        return selected
    # Keep anchors and spread the remaining event/beat evidence across the
    # available budget. This avoids flooding a provider with near-identical
    # frames from a dense V5 event list.
    anchors = [item for item in selected if item["selectionReason"] in {"OPENING_ANCHOR", "ENDING_ANCHOR"}]
    others = [item for item in selected if item not in anchors]
    remaining = max(0, max_frames - len(anchors))
    if remaining == 0:
        return anchors[:max_frames]
    stride = max(1, math.ceil(len(others) / remaining))
    return sorted((anchors + others[::stride])[:max_frames], key=lambda item: float(item["timestampSeconds"]))


def _write_frame_assets(path: Path, selected: list[dict[str, Any]], asset_hash: str) -> list[dict[str, Any]]:
    output_dir = settings.data_root.expanduser().resolve() / "semantic-frames" / asset_hash[:24]
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(path))
    try:
        for index, item in enumerate(selected, start=1):
            capture.set(cv2.CAP_PROP_POS_MSEC, float(item["timestampSeconds"]) * 1000)
            ok, frame = capture.read()
            if not ok:
                item["framePath"] = None
                item["frameAvailable"] = False
                continue
            destination = output_dir / f"frame-{index:02d}-{float(item['timestampSeconds']):07.3f}.jpg"
            if not cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 88]):
                item["framePath"] = None
                item["frameAvailable"] = False
                continue
            item["framePath"] = str(destination)
            item["frameAvailable"] = True
    finally:
        capture.release()
    return selected


def select_semantic_frames(
    path: Path,
    duration_seconds: float,
    asset_hash: str,
    temporal_profile: dict[str, Any] | None = None,
    beat_windows: list[dict[str, Any]] | None = None,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> dict[str, Any]:
    """Select and materialize a small set of representative frame assets."""
    duration = max(0.0, float(duration_seconds))
    candidates: list[dict[str, Any]] = []
    for timestamp in (0.0, 0.5, 1.0, 1.5):
        if timestamp <= duration:
            _add(candidates, timestamp, "OPENING_ANCHOR")
    for offset in (1.5, 1.0, 0.5):
        if duration > 0:
            _add(candidates, max(0.0, duration - offset), "ENDING_ANCHOR")

    profile = temporal_profile or {}
    events = profile.get("temporalActivityEvents") or profile.get("events") or []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        start = event.get("startSeconds", event.get("start"))
        end = event.get("endSeconds", event.get("end"))
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        event_id = str(event.get("eventId", f"v5-event-{index + 1}"))
        _add(candidates, float(start) - 0.25, "V5_EVENT_BEFORE", event_id=event_id)
        _add(candidates, (float(start) + float(end)) / 2.0, "V5_EVENT_DURING", event_id=event_id)
        _add(candidates, float(end) + 0.25, "V5_EVENT_AFTER", event_id=event_id)

    for index, beat in enumerate(beat_windows or []):
        if not isinstance(beat, dict):
            continue
        start = beat.get("startSeconds")
        end = beat.get("endSeconds")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)):
            beat_id = str(beat.get("beatId", f"plan-beat-{index + 1}"))
            _add(candidates, (float(start) + float(end)) / 2.0, "PLAN_BEAT", beat_id=beat_id)

    selected = _deduplicate(candidates, max(4, min(int(max_frames), DEFAULT_MAX_FRAMES)), duration)
    selected = _write_frame_assets(path, selected, asset_hash)
    return {
        "version": FRAME_SELECTION_VERSION,
        "assetHash": asset_hash,
        "durationSeconds": round(duration, 3),
        "maxFrames": max_frames,
        "selectedFrameCount": len(selected),
        "selectedFrames": selected,
        "coverage": {
            "openingAnchors": sum(item["selectionReason"] == "OPENING_ANCHOR" for item in selected),
            "endingAnchors": sum(item["selectionReason"] == "ENDING_ANCHOR" for item in selected),
            "v5Events": sum(str(item["selectionReason"]).startswith("V5_EVENT") for item in selected),
            "planBeats": sum(item["selectionReason"] == "PLAN_BEAT" for item in selected),
        },
    }
