import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import settings
from .contracts import VideoAnalysisResponse, VideoMetadata

# ``settings`` is re-exported deliberately: tests patch ``app.video.settings`` directly
# (e.g. to point ``data_root`` at a tmp dir) rather than reaching into ``app.config``.
# Declaring it in ``__all__`` tells mypy this is an intentional public re-export, not an
# unused import.
__all__ = ["settings", "safe_video_path", "probe", "analyse"]

SAMPLE_TIMES = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0)


def safe_video_path(relative_path: str) -> Path:
    root = settings.data_root.expanduser().resolve()
    candidate = (root / relative_path).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise ValueError("Video must be a file inside POMPOM_DATA_ROOT")
    if candidate.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
        raise ValueError("Unsupported video extension")
    return candidate


def probe(path: Path) -> VideoMetadata:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    video = next(stream for stream in payload["streams"] if stream.get("codec_type") == "video")
    numerator, denominator = (video.get("avg_frame_rate") or "0/1").split("/")
    fps = float(numerator) / max(float(denominator), 1.0)
    width, height = int(video["width"]), int(video["height"])
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return VideoMetadata(
        durationMs=round(float(payload["format"]["duration"]) * 1000),
        width=width,
        height=height,
        fps=fps,
        aspectRatio=width / height,
        codec=video.get("codec_name", "unknown"),
        audioPresent=any(stream.get("codec_type") == "audio" for stream in payload["streams"]),
        sha256=digest.hexdigest(),
    )


def _frames(path: Path, duration: float) -> tuple[list[np.ndarray], list[float]]:
    capture = cv2.VideoCapture(str(path))
    times = sorted(
        {
            *SAMPLE_TIMES,
            *[float(second) for second in range(4, max(4, math.ceil(duration)))],
            *[round(value, 2) for value in np.arange(max(0, duration - 2), duration, 0.25)],
        }
    )
    frames: list[np.ndarray] = []
    used: list[float] = []
    for timestamp in times:
        if timestamp > duration:
            continue
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ok, frame = capture.read()
        if ok:
            frames.append(frame)
            used.append(timestamp)
    capture.release()
    return frames, used


def _storyboard(frames: list[np.ndarray], times: list[float], digest: str) -> str:
    output_dir = settings.data_root.expanduser().resolve() / "storyboards"
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = list(zip(frames, times, strict=False))[:12]
    tiles: list[np.ndarray] = []
    for frame, timestamp in selected:
        tile = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        cv2.rectangle(tile, (0, 150), (92, 180), (20, 27, 23), -1)
        cv2.putText(
            tile,
            f"{timestamp:05.2f}s",
            (8, 171),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        tiles.append(tile)
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[index : index + 4]) for index in range(0, len(tiles), 4)]
    contact_sheet = np.vstack(rows)
    destination = output_dir / f"{digest}.jpg"
    if not cv2.imwrite(str(destination), contact_sheet, [cv2.IMWRITE_JPEG_QUALITY, 88]):
        raise OSError("Could not write storyboard")
    return str(destination.relative_to(settings.data_root.expanduser().resolve()))


def _feature(value: float, confidence: float, evidence: str, ranges: list[list[float]]) -> dict[str, Any]:
    return {
        "value": round(max(0.0, min(1.0, value)), 4),
        "confidence": confidence,
        "evidence": evidence,
        "timestampRanges": ranges,
    }


def analyse(relative_path: str) -> VideoAnalysisResponse:
    path = safe_video_path(relative_path)
    metadata = probe(path)
    duration = metadata.duration_ms / 1000
    frames, times = _frames(path, duration)
    if len(frames) < 2:
        raise ValueError("Video yielded too few readable frames")
    gray = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]
    storyboard_path = _storyboard(frames, times, metadata.sha256)
    differences = [float(np.mean(cv2.absdiff(a, b))) / 255 for a, b in zip(gray, gray[1:], strict=False)]
    brightness = [float(np.mean(frame)) / 255 for frame in gray]
    motion = float(np.mean(differences))
    hook_motion = float(np.mean(differences[: min(4, len(differences))]))
    final_motion = float(np.mean(differences[-min(3, len(differences)) :]))
    dead_ranges = [
        [times[index], times[index + 1]] for index, value in enumerate(differences) if value < 0.012
    ]
    black_ranges = [
        [timestamp, timestamp] for timestamp, value in zip(times, brightness, strict=False) if value < 0.03
    ]
    action_density = sum(value > 0.035 for value in differences) / len(differences)
    escalation = max(0.0, min(1.0, final_motion / max(hook_motion, 0.01) / 2))
    hook_anomaly = max(0.0, min(1.0, hook_motion * 5))
    final_twist = max(0.0, min(1.0, final_motion * 5))
    loopability = max(0.0, 1 - float(np.mean(cv2.absdiff(gray[0], gray[-1]))) / 80)
    features = {
        "hookAnomaly": _feature(
            hook_anomaly, 0.62, "First-second frame-difference anomaly", [[0, min(1, duration)]]
        ),
        "hookMotion": _feature(
            min(1, hook_motion * 6), 0.9, "Measured first-second motion", [[0, min(1, duration)]]
        ),
        "hookVisualClarity": _feature(0.5, 0.25, "Requires semantic confirmation", [[0, min(1, duration)]]),
        "characterGoal": _feature(0.5, 0.2, "Local semantic model not configured", []),
        "physicalAction": _feature(min(1, motion * 7), 0.76, "Whole-video frame motion", [[0, duration]]),
        "actionDensity": _feature(
            action_density, 0.9, "Share of sampled intervals above motion threshold", [[0, duration]]
        ),
        "problemResistance": _feature(0.5, 0.2, "Requires semantic confirmation", []),
        "escalation": _feature(
            escalation, 0.55, "Final motion relative to opening motion", [[max(0, duration - 2), duration]]
        ),
        "fakeResolution": _feature(0.0, 0.15, "Not inferred without semantic evidence", []),
        "finalTwist": _feature(
            final_twist, 0.5, "Final-two-second motion change", [[max(0, duration - 2), duration]]
        ),
        "characterImpact": _feature(0.5, 0.2, "Requires character recognition", []),
        "loopability": _feature(
            loopability,
            0.72,
            "First/last sampled-frame similarity",
            [[0, 0.25], [max(0, duration - 0.25), duration]],
        ),
        "deadTime": _feature(
            sum(end - start for start, end in dead_ranges) / max(duration, 0.1),
            0.86,
            "Low-motion sampled intervals",
            dead_ranges,
        ),
        "dialogueDependency": _feature(0.5, 0.15, "Transcription not enabled", []),
        "ctaInterruption": _feature(0.0, 0.15, "CTA semantics not configured", []),
        "visualContinuity": _feature(
            1 - min(1, len(black_ranges) / max(1, len(times))),
            0.7,
            "Black-frame continuity proxy",
            black_ranges,
        ),
        "generationErrorScore": _feature(0.0, 0.18, "Requires VLM or human anatomy review", []),
    }
    for semantic_feature in (
        "mystery",
        "visualSearch",
        "surpriseReveal",
        "cuteEmotion",
        "characterRelationship",
        "worldCuriosity",
        "narrativeCuriosity",
        "spectacle",
        "transformation",
        "impossibleScale",
        "repetitionEscalation",
        "educationalDiscovery",
    ):
        features[semantic_feature] = _feature(
            0.5, 0.12, "Semantic model not configured; neutral prior only", []
        )
    action_dna = 100 * (
        0.15 * hook_anomaly
        + 0.20 * min(1, motion * 7)
        + 0.15 * escalation
        + 0.10 * final_twist
        + 0.05 * loopability
        + 0.35 * 0.5
    )
    classification = "GOOD" if action_dna >= 60 else "AVERAGE_FIXABLE" if action_dna >= 40 else "BAD"
    timeline = [
        {"kind": "DEAD_TIME", "start": start, "end": end, "confidence": 0.86} for start, end in dead_ranges
    ]
    timeline += [
        {"kind": "BLACK_FRAME", "start": start, "end": end, "confidence": 0.95} for start, end in black_ranges
    ]
    return VideoAnalysisResponse(
        metadata=metadata,
        analysisVersion=settings.analysis_version,
        primaryEngine="PHYSICAL_PROBLEM" if action_density >= 0.5 else "OTHER",
        secondaryEngines=["REPETITION_ESCALATION"] if escalation >= 0.6 else [],
        classification=classification,
        actionDnaScore=round(action_dna, 2),
        confidence=0.58,
        reason=(
            "Local motion evidence with conservative semantic priors; "
            "human/VLM confirmation remains required."
        ),
        storyboardPath=storyboard_path,
        timeline=timeline,
        features=features,
        evidence={"sampleTimes": times, "motionMean": motion, "blackFrameCount": len(black_ranges)},
    )
