import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
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
__all__ = [
    "settings",
    "safe_video_path",
    "probe",
    "analyse",
    "MOTION_SCORE_WEIGHTS",
    "calculate_motion_heuristic_score",
    "normalize_motion_intensity",
]

SAMPLE_TIMES = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0)
MIN_DELTA_T = 0.10
MOTION_RATE_SCALE = 0.12
MOTION_RATE_THRESHOLD = 0.035
LOW_MOTION_RATE_THRESHOLD = 0.012
NEAR_BLACK_MEAN_THRESHOLD = 0.03
NEAR_BLACK_PIXEL_THRESHOLD = 0.05
NEAR_BLACK_PIXEL_RATIO = 0.98
LOW_BRIGHTNESS_MEAN_THRESHOLD = 0.15

# v3 preserves the v2 motion-component proportions after removing endpoint similarity.
MOTION_SCORE_WEIGHTS = {
    "overall": 0.35 / 0.90,
    "opening": 0.25 / 0.90,
    "density": 0.20 / 0.90,
    "ending": 0.10 / 0.90,
}


@dataclass(frozen=True)
class SampledFrame:
    frame: np.ndarray
    requested_time: float
    actual_time: float | None


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


def _requested_times(duration: float) -> list[float]:
    return sorted(
        {
            *SAMPLE_TIMES,
            *[float(second) for second in range(4, max(4, math.ceil(duration)))],
            *[round(value, 2) for value in np.arange(max(0, duration - 2), duration, 0.25)],
        }
    )


def _frames(path: Path, duration: float) -> tuple[list[SampledFrame], list[float]]:
    capture = cv2.VideoCapture(str(path))
    requested_times = [time for time in _requested_times(duration) if time <= duration]
    frames: list[SampledFrame] = []
    failed: list[float] = []
    for requested_time in requested_times:
        capture.set(cv2.CAP_PROP_POS_MSEC, requested_time * 1000)
        ok, frame = capture.read()
        if not ok:
            failed.append(requested_time)
            continue
        actual_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC))
        actual_time = actual_msec / 1000 if math.isfinite(actual_msec) and actual_msec >= 0 else None
        frames.append(SampledFrame(frame, requested_time, actual_time))
    capture.release()
    return frames, failed


def _storyboard(frames: list[SampledFrame], digest: str) -> str:
    output_dir = settings.data_root.expanduser().resolve() / "storyboards"
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = frames[:12]
    tiles: list[np.ndarray] = []
    for sample in selected:
        tile = cv2.resize(sample.frame, (320, 180), interpolation=cv2.INTER_AREA)
        cv2.rectangle(tile, (0, 150), (92, 180), (20, 27, 23), -1)
        cv2.putText(
            tile,
            f"{sample.requested_time:05.2f}s",
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


def normalize_motion_intensity(change_rate: float) -> tuple[float, float, bool]:
    """Return the pre-clamp value, bounded intensity, and saturation flag."""
    pre_clamp = max(0.0, change_rate) / MOTION_RATE_SCALE
    clipped = max(0.0, min(1.0, pre_clamp))
    return pre_clamp, clipped, pre_clamp >= 1.0


def calculate_motion_heuristic_score(
    overall: float,
    opening: float,
    density: float,
    ending: float,
) -> float:
    value = 100 * (
        MOTION_SCORE_WEIGHTS["overall"] * overall
        + MOTION_SCORE_WEIGHTS["opening"] * opening
        + MOTION_SCORE_WEIGHTS["density"] * density
        + MOTION_SCORE_WEIGHTS["ending"] * ending
    )
    return round(max(0.0, min(100.0, value)), 2)


def _intervals(samples: list[SampledFrame]) -> list[dict[str, Any]]:
    intervals: list[dict[str, Any]] = []
    for first, second in zip(samples, samples[1:], strict=False):
        t1 = first.actual_time if first.actual_time is not None else first.requested_time
        t2 = second.actual_time if second.actual_time is not None else second.requested_time
        delta_t = t2 - t1
        if delta_t < MIN_DELTA_T:
            continue
        raw_difference = float(np.mean(cv2.absdiff(
            cv2.cvtColor(first.frame, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(second.frame, cv2.COLOR_BGR2GRAY),
        ))) / 255
        visual_change_rate = raw_difference / max(delta_t, MIN_DELTA_T)
        pre_clamp, clipped, saturated = normalize_motion_intensity(visual_change_rate)
        intervals.append({
            "startTime": max(0.0, t1),
            "endTime": max(t1, t2),
            "deltaTSeconds": delta_t,
            "rawFrameDifference": raw_difference,
            "visualChangeRate": visual_change_rate,
            "normalizedMotionIntensityPreClamp": pre_clamp,
            "normalizedMotionIntensity": clipped,
            "normalizationSaturated": saturated,
        })
    return intervals


def _weighted_mean(intervals: list[dict[str, float]], key: str) -> float:
    total_time = sum(item["deltaTSeconds"] for item in intervals)
    if not intervals or total_time <= 0:
        return 0.0
    return sum(item[key] * item["deltaTSeconds"] for item in intervals) / total_time


def _interval_ranges(intervals: list[dict[str, float]], predicate: Any) -> list[dict[str, float]]:
    return [
        {
            "startTime": round(item["startTime"], 3),
            "endTime": round(item["endTime"], 3),
            "duration": round(item["deltaTSeconds"], 3),
            "visualChangeRate": round(item["visualChangeRate"], 5),
        }
        for item in intervals
        if predicate(item)
    ]


def _dark_candidates(samples: list[SampledFrame]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for sample in samples:
        gray = cv2.cvtColor(sample.frame, cv2.COLOR_BGR2GRAY) / 255
        mean_luminance = float(np.mean(gray))
        p99_luminance = float(np.percentile(gray, 99))
        near_black_ratio = float(np.mean(gray <= NEAR_BLACK_PIXEL_THRESHOLD))
        if near_black_ratio >= NEAR_BLACK_PIXEL_RATIO and mean_luminance <= NEAR_BLACK_MEAN_THRESHOLD:
            kind = "NEAR_BLACK_FRAME"
        elif mean_luminance <= LOW_BRIGHTNESS_MEAN_THRESHOLD:
            kind = "DARK_FRAME_CANDIDATE"
        else:
            continue
        candidates.append({
            "requestedTime": round(sample.requested_time, 3),
            "actualTime": None if sample.actual_time is None else round(sample.actual_time, 3),
            "kind": kind,
            "meanLuminance": round(mean_luminance, 5),
            "p99Luminance": round(p99_luminance, 5),
            "nearBlackPixelRatio": round(near_black_ratio, 5),
        })
    return candidates


def analyse(relative_path: str) -> VideoAnalysisResponse:
    path = safe_video_path(relative_path)
    metadata = probe(path)
    duration = metadata.duration_ms / 1000
    frames, failed_times = _frames(path, duration)
    if len(frames) < 2:
        raise ValueError("Video yielded too few readable frames")
    intervals = _intervals(frames)
    if not intervals:
        raise ValueError("Video yielded too few valid frame pairs")
    times = [sample.requested_time for sample in frames]
    storyboard_path = _storyboard(frames, metadata.sha256)
    overall_rate = _weighted_mean(intervals, "visualChangeRate")
    opening = [item for item in intervals if item["startTime"] < min(1.0, duration)]
    ending = [item for item in intervals if item["endTime"] > max(0.0, duration - 2.0)]
    opening_rate = _weighted_mean(opening, "visualChangeRate")
    ending_rate = _weighted_mean(ending, "visualChangeRate")
    total_interval_time = sum(item["deltaTSeconds"] for item in intervals)
    motion_interval_density = sum(
        item["deltaTSeconds"] for item in intervals if item["visualChangeRate"] >= MOTION_RATE_THRESHOLD
    ) / max(total_interval_time, MIN_DELTA_T)
    _, opening_intensity, _ = normalize_motion_intensity(opening_rate)
    _, overall_intensity, _ = normalize_motion_intensity(overall_rate)
    _, ending_evidence, _ = normalize_motion_intensity(ending_rate)
    if opening_rate < MIN_DELTA_T:
        escalation_proxy = 0.0
    else:
        escalation_proxy = max(0.0, min(1.0, (ending_rate - opening_rate) / max(opening_rate, MOTION_RATE_SCALE)))
    first_gray = cv2.cvtColor(frames[0].frame, cv2.COLOR_BGR2GRAY)
    last_gray = cv2.cvtColor(frames[-1].frame, cv2.COLOR_BGR2GRAY)
    first_last_similarity = max(0.0, min(1.0, 1 - float(np.mean(cv2.absdiff(first_gray, last_gray))) / 255))
    low_motion_intervals = _interval_ranges(intervals, lambda item: item["visualChangeRate"] < LOW_MOTION_RATE_THRESHOLD)
    dark_candidates = _dark_candidates(frames)
    requested_count = len([time for time in _requested_times(duration) if time <= duration])
    decoded_count = len(frames)
    valid_pair_count = len(intervals)
    decode_success_ratio = decoded_count / max(requested_count, 1)
    temporal_coverage = min(1.0, total_interval_time / max(duration, 0.1))
    measurement_confidence = round(
        max(0.0, min(1.0, 0.35 * decode_success_ratio + 0.35 * temporal_coverage + 0.30 * min(1.0, valid_pair_count / 8))),
        4,
    )
    motion_heuristic_score = calculate_motion_heuristic_score(
        overall_intensity,
        opening_intensity,
        motion_interval_density,
        ending_evidence,
    )
    classification = (
        "HIGH_MOTION_EVIDENCE" if motion_heuristic_score >= 60
        else "MODERATE_MOTION_EVIDENCE" if motion_heuristic_score >= 40
        else "LOW_MOTION_EVIDENCE"
    )
    sampling = {
        "requestedSamples": requested_count,
        "decodedSamples": decoded_count,
        "validFramePairs": valid_pair_count,
        "failedDecodeSamples": len(failed_times),
        "requestedTimes": times,
        "failedRequestedTimes": failed_times,
        "temporalCoverage": round(temporal_coverage, 4),
    }
    motion = {
        "openingMotionIntensity": round(opening_intensity, 4),
        "overallMotionIntensity": round(overall_intensity, 4),
        "motionIntervalDensity": round(motion_interval_density, 4),
        "motionEscalationProxy": round(escalation_proxy, 4),
        "endingMotionEvidence": round(ending_evidence, 4),
        "lowMotionIntervals": low_motion_intervals,
        "changeRateUnit": "mean grayscale pixel change per second",
    }
    visual_similarity = {"firstLastVisualSimilarity": round(first_last_similarity, 4)}
    measurement_quality = {
        "decodeSuccessRatio": round(decode_success_ratio, 4),
        "validFramePairCount": valid_pair_count,
        "failedDecodeSamples": len(failed_times),
        "temporalCoverage": round(temporal_coverage, 4),
        "minimumDeltaTSeconds": MIN_DELTA_T,
    }
    features = {
        "openingMotionEvidence": _feature(opening_intensity, measurement_confidence, "Time-normalized sampled visual change in the opening", [[0, min(1, duration)]]),
        "openingMotionIntensity": _feature(opening_intensity, measurement_confidence, "Time-normalized sampled visual change in the opening", [[0, min(1, duration)]]),
        "overallMotionIntensity": _feature(overall_intensity, measurement_confidence, "Duration-weighted time-normalized sampled visual change", [[0, duration]]),
        "motionIntervalDensity": _feature(motion_interval_density, measurement_confidence, "Duration share of intervals above visual-change threshold", [[0, duration]]),
        "motionEscalationProxy": _feature(escalation_proxy, measurement_confidence, "Bounded ending-versus-opening visual-change proxy; not narrative escalation", [[max(0, duration - 2), duration]]),
        "endingMotionEvidence": _feature(ending_evidence, measurement_confidence, "Time-normalized sampled visual change near the ending", [[max(0, duration - 2), duration]]),
        "lowMotionDurationEstimate": _feature(sum(item["duration"] for item in low_motion_intervals) / max(duration, 0.1), measurement_confidence, "Duration share of low visual-change intervals", [[item["startTime"], item["endTime"]] for item in low_motion_intervals]),
        "firstLastVisualSimilarity": _feature(first_last_similarity, measurement_confidence, "Pixel similarity between first and last decoded samples; not semantic loopability", [[0, 0.25], [max(0, duration - 0.25), duration]]),
    }
    timeline = [
        {"kind": "LOW_MOTION_INTERVAL", **item, "confidence": measurement_confidence} for item in low_motion_intervals
    ]
    timeline += [
        {"kind": candidate["kind"], "start": candidate["requestedTime"], "end": candidate["requestedTime"], "confidence": measurement_confidence}
        for candidate in dark_candidates
    ]
    return VideoAnalysisResponse(
        metadata=metadata,
        analysisVersion=settings.analysis_version,
        analysisType="SAMPLED_VISUAL_MOTION",
        primaryEngine="SAMPLED_VISUAL_MOTION",
        secondaryEngines=["MOTION_ESCALATION_PROXY"] if escalation_proxy >= 0.6 else [],
        classification=classification,
        motionHeuristicScore=motion_heuristic_score,
        measurementConfidence=measurement_confidence,
        measurementQuality=measurement_quality,
        reason="Sampled visual-change evidence only. This analyzer does not evaluate story, character intent, dialogue, humor, causality, or platform performance.",
        storyboardPath=storyboard_path,
        timeline=timeline,
        features=features,
        sampling=sampling,
        motion=motion,
        visualSimilarity=visual_similarity,
        darkFrameCandidates=dark_candidates,
        evidence={
            "sampleTimes": times,
            "intervals": intervals,
            "darkFrameCount": len(dark_candidates),
            "motionScoreWeights": MOTION_SCORE_WEIGHTS,
            "motionNormalizationReference": MOTION_RATE_SCALE,
            "saturatedIntervalCount": sum(1 for item in intervals if item["normalizationSaturated"]),
        },
    )
