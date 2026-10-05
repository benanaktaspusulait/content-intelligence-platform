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

# Local temporal evidence is intentionally independent from the v3 score.
TEMPORAL_PROFILE_VERSION = "temporal-motion-profile-v2"
TEMPORAL_MIN_SEGMENTS = 4
TEMPORAL_MAX_SEGMENTS = 10
TEMPORAL_TARGET_SEGMENT_SECONDS = 1.5
TEMPORAL_CHANGE_MIN_ABSOLUTE = 0.18
TEMPORAL_CHANGE_MIN_RELATIVE = 0.30
TEMPORAL_CHANGE_MIN_DURATION_SECONDS = 0.50

# V4 parameters are versioned evidence configuration, not creative-quality rules.
V4_ANALYSIS_VERSION = "sampled-visual-motion-v4"
V5_ANALYSIS_VERSION = "sampled-visual-motion-v5"
V4_SAMPLE_INTERVAL_SECONDS = 0.25
V4_MEDIUM_NOVELTY_OFFSET_SECONDS = 1.25
V4_LOW_MOTION_ENTER_THRESHOLD = 0.12
V4_LOW_MOTION_EXIT_THRESHOLD = 0.20
V4_LOW_MOTION_MAX_MERGE_GAP_SECONDS = 0.35
V4_LOW_MOTION_MIN_DURATION_SECONDS = 0.75
V4_SMOOTHING_WINDOW = 3
V4_NOVELTY_SSIM_WINDOW = 64

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


@dataclass(frozen=True)
class V4SampledFrame:
    frame: np.ndarray
    requested_time: float
    actual_time: float | None
    timestamp_error: float | None


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


def _v4_target_times(duration: float) -> list[float]:
    if duration <= 0:
        return []
    count = int(math.floor(duration / V4_SAMPLE_INTERVAL_SECONDS))
    targets = [round(index * V4_SAMPLE_INTERVAL_SECONDS, 6) for index in range(count + 1)]
    if not targets or duration - targets[-1] > 1e-6:
        targets.append(round(duration, 6))
    return [min(duration, value) for value in targets]


def _sequential_frames(path: Path, duration: float) -> tuple[list[V4SampledFrame], dict[str, Any]]:
    """Decode once and select the nearest decoded frame for each uniform target."""
    targets = _v4_target_times(duration)
    capture = cv2.VideoCapture(str(path))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    samples: list[V4SampledFrame] = []
    failed: list[float] = []
    previous: tuple[np.ndarray, float] | None = None
    target_index = 0
    frame_index = 0
    while target_index < len(targets):
        ok, frame = capture.read()
        if not ok:
            failed.extend(targets[target_index:])
            break
        raw_timestamp = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000
        actual = raw_timestamp if math.isfinite(raw_timestamp) and raw_timestamp >= 0 else frame_index / max(fps, 1.0)
        current = (frame, actual)
        while target_index < len(targets) and targets[target_index] <= actual:
            requested = targets[target_index]
            candidate = current
            if previous is not None and abs(previous[1] - requested) <= abs(current[1] - requested):
                candidate = previous
            samples.append(V4SampledFrame(candidate[0], requested, candidate[1], abs(candidate[1] - requested)))
            target_index += 1
        previous = current
        frame_index += 1
    capture.release()
    actual_times = [sample.actual_time for sample in samples if sample.actual_time is not None]
    duplicate_count = sum(1 for first, second in zip(actual_times, actual_times[1:], strict=False) if abs(second - first) < 1e-6)
    return samples, {
        "requestedSamples": len(targets),
        "decodedSamples": len(samples),
        "failedSamples": len(failed),
        "failedRequestedTimes": failed,
        "duplicateSamples": duplicate_count,
        "duplicateTimestampRatio": duplicate_count / max(len(samples) - 1, 1),
        "timestampAccuracy": round(1.0 - min(1.0, float(np.mean([sample.timestamp_error or 0.0 for sample in samples])) / max(V4_SAMPLE_INTERVAL_SECONDS, 0.001)), 4) if samples else 0.0,
        "temporalCoverage": round((actual_times[-1] - actual_times[0]) / max(duration, 0.1), 4) if len(actual_times) > 1 else 0.0,
        "requestedTimes": targets,
    }


def _v4_intervals(samples: list[V4SampledFrame]) -> list[dict[str, Any]]:
    intervals: list[dict[str, Any]] = []
    for first, second in zip(samples, samples[1:], strict=False):
        t1 = first.actual_time if first.actual_time is not None else first.requested_time
        t2 = second.actual_time if second.actual_time is not None else second.requested_time
        delta_t = t2 - t1
        if delta_t < MIN_DELTA_T:
            continue
        first_gray = cv2.cvtColor(first.frame, cv2.COLOR_BGR2GRAY)
        second_gray = cv2.cvtColor(second.frame, cv2.COLOR_BGR2GRAY)
        raw_difference = float(np.mean(cv2.absdiff(first_gray, second_gray))) / 255
        change_rate = raw_difference / max(delta_t, MIN_DELTA_T)
        pre_clamp, normalized, saturated = normalize_motion_intensity(change_rate)
        intervals.append({
            "startTime": round(max(0.0, t1), 6),
            "endTime": round(max(t1, t2), 6),
            "deltaTSeconds": round(delta_t, 6),
            "rawPixelDifference": round(raw_difference, 6),
            "visualChangeRate": change_rate,
            "timeNormalizedChange": change_rate,
            "preClampNormalizedMotion": pre_clamp,
            "normalizedShortMotion": normalized,
            "normalizedMotionIntensity": normalized,
            "finalMotion": normalized,
            "wasClipped": saturated,
            "normalizationSaturated": saturated,
        })
    raw = [item["normalizedShortMotion"] for item in intervals]
    smoothed = [
        float(np.median(raw[max(0, index - 1): min(len(raw), index + 2)]))
        for index in range(len(raw))
    ]
    for item, value in zip(intervals, smoothed, strict=False):
        item["smoothedMotion"] = round(float(value), 6)
        item["normalizedMotionIntensity"] = float(value)
    return intervals


def _gray_small(frame: np.ndarray) -> np.ndarray:
    return cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (V4_NOVELTY_SSIM_WINDOW, V4_NOVELTY_SSIM_WINDOW), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


def _structural_similarity(first: np.ndarray, second: np.ndarray) -> float:
    mean_first, mean_second = float(np.mean(first)), float(np.mean(second))
    variance_first, variance_second = float(np.var(first)), float(np.var(second))
    covariance = float(np.mean((first - mean_first) * (second - mean_second)))
    c1, c2 = 0.0001, 0.0009
    value = ((2 * mean_first * mean_second + c1) * (2 * covariance + c2)) / ((mean_first**2 + mean_second**2 + c1) * (variance_first + variance_second + c2))
    return max(0.0, min(1.0, value))


def _phash_distance(first: np.ndarray, second: np.ndarray) -> float:
    first_dct = cv2.dct(cv2.resize(first, (32, 32), interpolation=cv2.INTER_AREA))[:8, :8]
    second_dct = cv2.dct(cv2.resize(second, (32, 32), interpolation=cv2.INTER_AREA))[:8, :8]
    first_bits = first_dct > np.median(first_dct)
    second_bits = second_dct > np.median(second_dct)
    return float(np.mean(first_bits != second_bits))


def _v4_visual_novelty(samples: list[V4SampledFrame], duration: float) -> dict[str, Any]:
    points: list[dict[str, Any]] = []
    offset = V4_MEDIUM_NOVELTY_OFFSET_SECONDS
    for index, sample in enumerate(samples):
        target = sample.requested_time + offset
        match = next((candidate for candidate in samples[index + 1:] if candidate.requested_time >= target), None)
        if match is None:
            continue
        first_gray, second_gray = _gray_small(sample.frame), _gray_small(match.frame)
        similarity = _structural_similarity(first_gray, second_gray)
        phash = _phash_distance(first_gray, second_gray)
        points.append({
            "timestamp": round(sample.requested_time, 3),
            "comparisonOffset": round(match.requested_time - sample.requested_time, 3),
            "structuralSimilarity": round(similarity, 5),
            "perceptualHashDistance": round(phash, 5),
            "embeddingDistance": None,
            "embeddingStatus": "NOT_EVALUATED",
            "novelty": round((1.0 - similarity) * 0.8 + phash * 0.2, 5),
        })
    values = [item["novelty"] for item in points]
    average = float(np.mean(values)) if values else 0.0
    return {
        "version": "visual-novelty-v1",
        "mediumOffsetSeconds": offset,
        "points": points,
        "averageNovelty": round(average, 5),
        "status": "AVAILABLE" if points else "NOT_EVALUATED",
    }


def _v4_recurrence(samples: list[V4SampledFrame], intervals: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    """Summarize multi-lag visual recurrence without exposing the full similarity matrix."""
    lags = (0.5, 0.75, 1.0, 1.5, 2.0, 2.25, 2.5, 3.0)
    lag_results: list[dict[str, Any]] = []
    for lag in lags:
        similarities: list[float] = []
        for index, sample in enumerate(samples):
            match = next((candidate for candidate in samples[index + 1:] if candidate.requested_time >= sample.requested_time + lag), None)
            if match is None:
                continue
            first_gray, second_gray = _gray_small(sample.frame), _gray_small(match.frame)
            structural = _structural_similarity(first_gray, second_gray)
            hash_similarity = 1.0 - _phash_distance(first_gray, second_gray)
            similarities.append(0.7 * structural + 0.3 * hash_similarity)
        if len(similarities) < 3:
            continue
        interval_seconds = np.median(np.diff([item["startTime"] for item in intervals])) if len(intervals) > 1 else 0.25
        shift = max(1, int(round(lag / max(float(interval_seconds), MIN_DELTA_T))))
        motion = [float(item.get("preClampNormalizedMotion", item.get("smoothedMotion", 0.0))) for item in intervals]
        autocorrelation = 0.0
        if len(motion) > shift * 2:
            left, right = np.asarray(motion[:-shift]), np.asarray(motion[shift:])
            if float(np.std(left)) > 1e-6 and float(np.std(right)) > 1e-6:
                autocorrelation = float(np.corrcoef(left, right)[0, 1])
                if not math.isfinite(autocorrelation):
                    autocorrelation = 0.0
        visual_recurrence = float(np.mean(similarities))
        strength = max(0.0, min(1.0, 0.65 * visual_recurrence + 0.35 * max(0.0, autocorrelation)))
        lag_results.append({
            "lagSeconds": lag,
            "visualSimilarity": round(visual_recurrence, 5),
            "motionAutocorrelation": round(autocorrelation, 5),
            "recurrenceStrength": round(strength, 5),
            "comparisonCount": len(similarities),
            "estimatedCycles": round(duration / lag, 2),
        })
    best = max(lag_results, key=lambda item: item["recurrenceStrength"], default=None)
    moving = float(np.std([item.get("preClampNormalizedMotion", item.get("smoothedMotion", 0.0)) for item in intervals])) if intervals else 0.0
    detected = bool(best and best["recurrenceStrength"] >= 0.72 and moving >= 0.025)
    return {
        "version": "multi-lag-recurrence-v1",
        "detected": detected,
        "startSeconds": 0.0 if detected else None,
        "endSeconds": round(duration, 3) if detected else None,
        "durationSeconds": round(duration, 3) if detected else 0.0,
        "recurrenceStrength": None if best is None else best["recurrenceStrength"],
        "dominantLagSeconds": None if best is None else best["lagSeconds"],
        "estimatedCycles": None if best is None else best["estimatedCycles"],
        "visualStateRecurrence": bool(best and best["visualSimilarity"] >= 0.78),
        "motionPatternRecurrence": bool(best and best["motionAutocorrelation"] >= 0.55),
        "evidenceQuality": "MULTI_LAG_SSIM_AND_MOTION_AUTOCORRELATION" if best else "INSUFFICIENT_COMPARISONS",
        "lags": lag_results,
    }


def _v4_low_motion_candidates(intervals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    for item in intervals:
        motion = float(item["smoothedMotion"])
        if active is None and motion <= V4_LOW_MOTION_ENTER_THRESHOLD:
            active = {"startSeconds": item["startTime"], "endSeconds": item["endTime"], "motions": [motion]}
        elif active is not None and motion <= V4_LOW_MOTION_EXIT_THRESHOLD:
            active["endSeconds"] = item["endTime"]
            active["motions"].append(motion)
        elif active is not None:
            spans.append(active)
            active = None
    if active is not None:
        spans.append(active)
    merged: list[dict[str, Any]] = []
    for span in spans:
        if merged and span["startSeconds"] - merged[-1]["endSeconds"] <= V4_LOW_MOTION_MAX_MERGE_GAP_SECONDS:
            merged[-1]["endSeconds"] = span["endSeconds"]
            merged[-1]["motions"].extend(span["motions"])
            merged[-1]["mergedGapCount"] += 1
        else:
            merged.append({**span, "mergedGapCount": 0})
    result: list[dict[str, Any]] = []
    for span in merged:
        duration = span["endSeconds"] - span["startSeconds"]
        if duration < V4_LOW_MOTION_MIN_DURATION_SECONDS:
            continue
        motions = span.pop("motions")
        result.append({
            **span,
            "durationSeconds": round(duration, 3),
            "averageMotion": round(float(np.mean(motions)), 5),
            "minimumMotion": round(float(np.min(motions)), 5),
            "entryThreshold": V4_LOW_MOTION_ENTER_THRESHOLD,
            "exitThreshold": V4_LOW_MOTION_EXIT_THRESHOLD,
            "evidenceQuality": "SMOOTHED_HYSTERESIS",
        })
    return result


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


def _temporal_profile(intervals: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    """Build local, duration-aware motion evidence without changing v3 scoring."""
    segment_count = max(
        TEMPORAL_MIN_SEGMENTS,
        min(TEMPORAL_MAX_SEGMENTS, math.ceil(duration / TEMPORAL_TARGET_SEGMENT_SECONDS)),
    )
    edges = np.linspace(0.0, duration, segment_count + 1).tolist()
    overall = _weighted_mean(intervals, "normalizedMotionIntensity")
    segments: list[dict[str, Any]] = []
    for index in range(segment_count):
        start, end = edges[index], edges[index + 1]
        local = []
        for item in intervals:
            overlap = max(0.0, min(end, item["endTime"]) - max(start, item["startTime"]))
            if overlap > 0:
                local.append({**item, "overlap": overlap})
        total = sum(item["overlap"] for item in local)
        values = [item["normalizedMotionIntensity"] for item in local]
        pre_clamp_values = [float(item.get("preClampNormalizedMotion", 0.0)) for item in local]
        clipped_values = [item for item in local if item.get("wasClipped", item.get("normalizationSaturated", False))]
        average = sum(item["normalizedMotionIntensity"] * item["overlap"] for item in local) / total if total else 0.0
        density = sum(item["overlap"] for item in local if item["visualChangeRate"] >= MOTION_RATE_THRESHOLD) / total if total else 0.0
        peak = max(values) if values else 0.0
        minimum = min(values) if values else 0.0
        variability = math.sqrt(
            sum(((item["normalizedMotionIntensity"] - average) ** 2) * item["overlap"] for item in local) / total
        ) if total else 0.0
        previous = segments[-1]["averageMotion"] if segments else None
        segments.append({
            "segmentIndex": index,
            "startSeconds": round(start, 3),
            "endSeconds": round(end, 3),
            "averageMotion": round(average, 4),
            "motionDensity": round(density, 4),
            "peakMotion": round(peak, 4),
            "minimumMotion": round(minimum, 4),
            "motionVariability": round(variability, 4),
            "coverage": round(min(1.0, total / max(end - start, MIN_DELTA_T)), 4),
            "validIntervalCount": len(local),
            "relativeToPrevious": None if previous is None else round(average - previous, 4),
            "relativeToOverall": round(average - overall, 4),
            "relativeToNext": None,
            "sampledIntervalCount": len(local),
            "clippedIntervalRatio": round(len(clipped_values) / max(len(local), 1), 4),
            "preClampMean": round(float(np.mean(pre_clamp_values)) if pre_clamp_values else 0.0, 4),
            "preClampP50": round(float(np.percentile(pre_clamp_values, 50)) if pre_clamp_values else 0.0, 4),
            "preClampP90": round(float(np.percentile(pre_clamp_values, 90)) if pre_clamp_values else 0.0, 4),
            "finalMean": round(average, 4),
        })

    for index, segment in enumerate(segments):
        segment["relativeToNext"] = (
            None if index == len(segments) - 1
            else round(segments[index + 1]["averageMotion"] - segment["averageMotion"], 4)
        )

    def change_runs(direction: str) -> list[dict[str, Any]]:
        marked: list[int] = []
        for index in range(1, len(segments) - 1):
            previous = segments[index - 1]["averageMotion"]
            current = segments[index]["averageMotion"]
            following = segments[index + 1]["averageMotion"]
            baseline = (previous + following) / 2
            magnitude = baseline - current if direction == "drop" else current - baseline
            relative = magnitude / max(abs(baseline), 0.05)
            if magnitude >= TEMPORAL_CHANGE_MIN_ABSOLUTE and relative >= TEMPORAL_CHANGE_MIN_RELATIVE:
                marked.append(index)

        runs: list[list[int]] = []
        for index in marked:
            if not runs or index != runs[-1][-1] + 1:
                runs.append([index])
            else:
                runs[-1].append(index)

        candidates: list[dict[str, Any]] = []
        for run in runs:
            first, last = run[0], run[-1]
            if first == 0 or last >= len(segments) - 1:
                continue
            before = segments[first - 1]["averageMotion"]
            after = segments[last + 1]["averageMotion"]
            duration_seconds = segments[last]["endSeconds"] - segments[first]["startSeconds"]
            during = sum(segments[index]["averageMotion"] for index in run) / len(run)
            baseline = (before + after) / 2
            magnitude = baseline - during if direction == "drop" else during - baseline
            relative = magnitude / max(abs(baseline), 0.05)
            if duration_seconds < TEMPORAL_CHANGE_MIN_DURATION_SECONDS or magnitude < TEMPORAL_CHANGE_MIN_ABSOLUTE or relative < TEMPORAL_CHANGE_MIN_RELATIVE:
                continue
            candidates.append({
                "startSeconds": segments[first]["startSeconds"],
                "endSeconds": segments[last]["endSeconds"],
                "durationSeconds": round(duration_seconds, 3),
                "beforeActivity": round(before, 4),
                "duringActivity": round(during, 4),
                "afterActivity": round(after, 4),
                "localBaseline": round(baseline, 4),
                "absoluteDrop" if direction == "drop" else "absoluteSpike": round(magnitude, 4),
                "relativeDrop" if direction == "drop" else "relativeSpike": round(relative, 4),
                "severityMagnitude": round(relative, 4),
                "classification": "UNMAPPED_DROP" if direction == "drop" else "UNMAPPED_SPIKE",
                "alignedBeatId": None,
                "alignedBeatType": None,
                "evidenceQuality": "LOCAL_TWO_SIDED_BASELINE",
            })
        return candidates

    drops = change_runs("drop")
    spikes = change_runs("spike")
    values = [item["averageMotion"] for item in segments]
    spread = max(values) - min(values) if values else 0.0
    variation = "UNKNOWN" if not values else "HIGHLY_VARIABLE" if spread >= 0.45 else "MODERATELY_VARIABLE" if spread >= 0.2 else "STEADY"
    return {
        "version": TEMPORAL_PROFILE_VERSION,
        "segments": segments,
        "activityDrops": drops,
        "activitySpikes": spikes,
        "variation": variation,
        "overallMotion": round(overall, 4),
        "status": "AVAILABLE" if segments else "NOT_EVALUATED",
    }


def _presentation_profile(samples: list[SampledFrame]) -> dict[str, Any]:
    luminance: list[float] = []
    saturation: list[float] = []
    for sample in samples:
        hsv = cv2.cvtColor(sample.frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(sample.frame, cv2.COLOR_BGR2GRAY) / 255
        luminance.append(float(np.mean(gray)))
        saturation.append(float(np.mean(hsv[:, :, 1]) / 255))
    return {
        "medianLuminance": round(float(np.median(luminance)), 4),
        "luminanceP10": round(float(np.percentile(luminance, 10)), 4),
        "luminanceP90": round(float(np.percentile(luminance, 90)), 4),
        "averageSaturation": round(float(np.mean(saturation)), 4),
        "exposureConsistency": round(max(0.0, 1.0 - float(np.std(luminance)) * 4), 4),
        "status": "AVAILABLE" if luminance else "NOT_EVALUATED",
    }


def _v4_motion_label(value: float) -> str:
    return "VERY_HIGH" if value >= 0.8 else "HIGH" if value >= 0.55 else "MODERATE" if value >= 0.3 else "LOW" if value >= 0.12 else "VERY_LOW"


def _v4_consistency_label(profile: dict[str, Any]) -> str:
    variation = profile.get("variation")
    return {"STEADY": "STEADY", "MODERATELY_VARIABLE": "UNEVEN", "HIGHLY_VARIABLE": "HIGHLY_UNEVEN"}.get(variation, "UNKNOWN")


def _v4_repetitive_motion(intervals: list[dict[str, Any]], novelty: dict[str, Any], recurrence: dict[str, Any]) -> dict[str, Any]:
    novelty_value = float(novelty.get("averageNovelty", 0.0))
    high_motion = [item for item in intervals if float(item.get("smoothedMotion", 0.0)) >= 0.55]
    repeated = bool(high_motion) and novelty_value <= 0.20 and bool(recurrence.get("detected"))
    return {
        "version": "repetitive-motion-evidence-v1",
        "status": "AVAILABLE" if intervals and novelty.get("status") == "AVAILABLE" else "NOT_EVALUATED",
        "averageShortMotion": round(float(np.mean([item["smoothedMotion"] for item in intervals])) if intervals else 0.0, 5),
        "averageVisualNovelty": novelty_value,
        "continuousMotion": len(high_motion) >= max(2, len(intervals) // 4),
        "lowStateNovelty": novelty_value <= 0.16,
        "repeatedPatternCandidate": repeated,
        "recurrence": recurrence,
        "classification": "HIGH" if repeated and novelty_value <= 0.08 else "MODERATE" if repeated else "LOW",
        "interpretation": "Movement continues while medium-range visual novelty remains low; this is evidence of possible repetition, not a performance claim." if repeated else "No prolonged high-motion/low-novelty pattern was established.",
    }


def _clipped_ratio(intervals: list[dict[str, Any]], start: float, end: float) -> float:
    local = [
        item for item in intervals
        if max(0.0, min(end, float(item.get("endTime", 0.0))) - max(start, float(item.get("startTime", 0.0)))) > 0
    ]
    clipped = sum(bool(item.get("wasClipped", item.get("normalizationSaturated", False))) for item in local)
    return clipped / max(len(local), 1)


def _v5_post_hold_trend(intervals: list[dict[str, Any]], start: float, end: float) -> dict[str, Any]:
    values = [float(item.get("smoothedMotion", item.get("normalizedMotionIntensity", 0.0)))
              for item in intervals if float(item.get("startTime", 0.0)) >= end
              and float(item.get("startTime", 0.0)) <= end + 2.5]
    if len(values) < 2:
        return {"trend": "UNKNOWN", "reboundMagnitude": 0.0, "sampleCount": len(values)}
    differences = np.diff(values)
    rising = int(np.sum(differences > 0.03))
    falling = int(np.sum(differences < -0.03))
    magnitude = max(0.0, values[-1] - values[0])
    if rising >= max(2, len(differences) // 2) and magnitude >= 0.12:
        trend = "RISING"
    elif falling >= max(2, len(differences) // 2):
        trend = "FALLING"
    elif magnitude < 0.06 and float(np.std(values)) < 0.08:
        trend = "FLAT"
    else:
        trend = "VARIABLE"
    return {"trend": trend, "reboundMagnitude": round(float(magnitude), 4), "sampleCount": len(values)}


def _v5_hold_events(profile: dict[str, Any], intervals: list[dict[str, Any]], duration: float,
                    timestamp_confidence: float) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    segments = profile.get("segments", [])
    for candidate in profile.get("activityDrops", []):
        start, end = float(candidate["startSeconds"]), float(candidate["endSeconds"])
        during = float(candidate.get("duringActivity", 0.0))
        before = float(candidate.get("beforeActivity", 0.0))
        after = float(candidate.get("afterActivity", 0.0))
        local = [item for item in segments if item["endSeconds"] > start and item["startSeconds"] < end]
        density_during = float(np.mean([item.get("motionDensity", 0.0) for item in local])) if local else 0.0
        before_segments = [item for item in segments if item["endSeconds"] <= start][-2:]
        after_segments = [item for item in segments if item["startSeconds"] >= end][:2]
        density_before = float(np.mean([item.get("motionDensity", 0.0) for item in before_segments])) if before_segments else 0.0
        density_after = float(np.mean([item.get("motionDensity", 0.0) for item in after_segments])) if after_segments else 0.0
        post = _v5_post_hold_trend(intervals, start, end)
        relative_drop = float(candidate.get("relativeDrop", 0.0))
        technical = bool(during <= 0.015 and post["trend"] == "FLAT")
        late_support = start >= duration * 0.50 and start <= duration * 0.85
        if technical:
            event_type = "TECHNICAL_FREEZE"
            emphasis = "UNKNOWN"
            reason = "Near-zero activity persists without a measurable post-event change; technical freeze suspicion requires review."
        elif late_support and post["trend"] == "RISING" and post["reboundMagnitude"] >= 0.12:
            event_type = "LIKELY_PURPOSEFUL_HOLD"
            emphasis = "STRONG" if post["reboundMagnitude"] >= 0.25 else "MODERATE"
            reason = "A late local activity trough is followed by sustained rising activity; no structured plan was available to confirm its purpose."
        else:
            event_type = "UNMAPPED_TROUGH"
            emphasis = "WEAK"
            reason = "A substantial local activity trough was detected without enough plan or semantic evidence to explain it."
        events.append({
            "eventType": event_type,
            "startSeconds": round(start, 3), "endSeconds": round(end, 3),
            "durationSeconds": round(end - start, 3),
            "activityBefore": round(before, 4), "activityDuring": round(during, 4), "activityAfter": round(after, 4),
            "densityBefore": round(density_before, 4), "densityDuring": round(density_during, 4), "densityAfter": round(density_after, 4),
            "relativeDrop": round(relative_drop, 4), "postEventTrend": post["trend"],
            "reboundMagnitude": post["reboundMagnitude"], "reboundSampleCount": post["sampleCount"],
            "alignedBeatId": None, "alignedBeatType": None, "alignedPayoff": False, "alignedReaction": False,
            "technicalFreezeSuspected": technical, "positionSupport": "LATE_WINDOW_SUPPORT" if late_support else "POSITION_NOT_DECISIVE",
            "holdEmphasis": emphasis, "evidenceConfidence": round(timestamp_confidence, 4),
            "reason": reason,
        })
    return events


def _v5_hook(profile: dict[str, Any], samples: list[V4SampledFrame]) -> dict[str, Any]:
    opening = float(profile.get("segments", [{}])[0].get("averageMotion", 0.0)) if profile.get("segments") else 0.0
    if opening >= 0.30:
        status, reason = "MODERATE", "The opening contains measurable visual activity, but semantic subject/object readability is not configured."
    elif opening >= 0.12:
        status, reason = "WEAK", "The opening begins with limited visual activity; semantic anomaly verification is unavailable."
    else:
        status, reason = "UNKNOWN", "Opening semantic evidence is unavailable because no character-aware vision provider is configured."
    return {"status": status, "windowSeconds": 1.5, "subjectPresence": None, "subjectPresenceStatus": "NOT_EVALUATED", "objectPresence": None, "objectPresenceStatus": "NOT_EVALUATED", "anomalyReadable": None, "anomalyReadableStatus": "NOT_EVALUATED", "expressionReadable": None, "expressionStatus": "NOT_EVALUATED", "directCameraGaze": None, "directCameraGazeStatus": "NOT_EVALUATED", "textOverlay": {"status": "NOT_EVALUATED", "reason": "OCR/text detection is not configured."}, "visualOpeningActivity": round(opening, 4), "reason": reason}


def _v5_action_novelty(profile: dict[str, Any], novelty: dict[str, Any], recurrence: dict[str, Any]) -> dict[str, Any]:
    segments = profile.get("segments", [])
    distinct = sum(1 for item in segments if float(item.get("relativeToPrevious") or 0.0) >= 0.10 or float(item.get("motionVariability", 0.0)) >= 0.12)
    observed = "STRONG" if distinct >= 3 else "MODERATE" if distinct >= 1 else "WEAK"
    return {"status": "PARTIAL", "plannedStrategyNovelty": {"status": "NOT_EVALUATED", "reason": "NO_STRUCTURED_PLAN"}, "observedVisualBeatNovelty": {"status": "AVAILABLE", "level": observed, "distinctBeatChanges": distinct, "reason": "Deterministic temporal and visual-state changes."}, "observedSemanticActionNovelty": {"status": "NOT_EVALUATED", "reason": "SEMANTIC_VISION_NOT_CONFIGURED"}, "combinedAssessment": observed if observed != "WEAK" else "WEAK", "repetitionContext": "ACCEPTABLE_IF_BEAT_CHANGES_PRESENT" if recurrence.get("detected") and distinct >= 2 else "REVIEW_CONTEXT_REQUIRED"}


def _v5_loop(similarity: float, recurrence: dict[str, Any]) -> dict[str, Any]:
    visual = "STRONG" if similarity >= 0.90 else "MODERATE" if similarity >= 0.75 else "WEAK"
    return {"status": "PARTIAL", "visualEvidence": visual, "visualEndpointSimilarity": round(similarity, 4), "semanticContinuity": None, "semanticContinuityStatus": "NOT_EVALUATED", "semanticContinuityReason": "SEMANTIC_VISION_NOT_CONFIGURED", "overall": visual, "reason": "Visual endpoint similarity is available; semantic loop continuity is not verified."}


def _analyse_v4(path: Path, metadata: VideoMetadata) -> VideoAnalysisResponse:
    duration = metadata.duration_ms / 1000
    samples, sampling = _sequential_frames(path, duration)
    if len(samples) < 2:
        raise ValueError("Video yielded too few sequential samples")
    intervals = _v4_intervals(samples)
    if not intervals:
        raise ValueError("Video yielded too few valid sequential frame pairs")
    v4_profile = _temporal_profile(intervals, duration)
    v4_profile["version"] = V4_ANALYSIS_VERSION
    v4_profile["motionPoints"] = [
        {
            "timestamp": round(item["startTime"], 3),
            "shortRangeMotion": round(item["normalizedShortMotion"], 5),
            "smoothedMotion": round(item["smoothedMotion"], 5),
        }
        for item in intervals
    ]
    low_candidates = _v4_low_motion_candidates(intervals)
    v4_profile["lowMotionCandidates"] = low_candidates
    v4_profile["troughs"] = [
        {**candidate, "depth": candidate.get("relativeDrop", 0.0), "sharpness": candidate.get("relativeDrop", 0.0), "confidence": sampling["timestampAccuracy"]}
        for candidate in v4_profile.get("activityDrops", [])
    ]
    v4_profile["spikes"] = [
        {**candidate, "confidence": sampling["timestampAccuracy"]}
        for candidate in v4_profile.get("activitySpikes", [])
    ]
    novelty = _v4_visual_novelty(samples, duration)
    recurrence = _v4_recurrence(samples, intervals, duration)
    repetition = _v4_repetitive_motion(intervals, novelty, recurrence)
    v4_profile["visualNovelty"] = novelty
    v4_profile["repetitiveMotion"] = repetition
    v4_profile["recurrence"] = recurrence
    clipped = [item for item in intervals if item.get("wasClipped")]
    pre_clamp = [float(item.get("preClampNormalizedMotion", 0.0)) for item in intervals]
    final_motion = [float(item.get("finalMotion", 0.0)) for item in intervals]
    v4_profile["saturationDiagnostics"] = {
        "overallClippedRatio": round(len(clipped) / max(len(intervals), 1), 5),
        "openingClippedRatio": round(_clipped_ratio(intervals, 0.0, duration * 0.25), 5),
        "middleClippedRatio": round(_clipped_ratio(intervals, duration * 0.25, duration * 0.75), 5),
        "endingClippedRatio": round(_clipped_ratio(intervals, duration * 0.75, duration), 5),
        "preClampMean": round(float(np.mean(pre_clamp)) if pre_clamp else 0.0, 5),
        "preClampP50": round(float(np.percentile(pre_clamp, 50)) if pre_clamp else 0.0, 5),
        "preClampP90": round(float(np.percentile(pre_clamp, 90)) if pre_clamp else 0.0, 5),
        "finalMean": round(float(np.mean(final_motion)) if final_motion else 0.0, 5),
        "warning": "MOTION_SCALE_SATURATION" if len(clipped) / max(len(intervals), 1) >= 0.60 else None,
    }
    v4_profile["dimensions"] = {
        "motionIntensity": _v4_motion_label(float(v4_profile["overallMotion"])),
        "temporalConsistency": _v4_consistency_label(v4_profile),
        "visualNovelty": "LOW" if novelty["averageNovelty"] < 0.16 else "MODERATE" if novelty["averageNovelty"] < 0.32 else "HIGH",
        "actionBeatNovelty": "NOT_EVALUATED",
        "planRenderFidelity": "NOT_EVALUATED",
    }
    actual_times = [sample.actual_time for sample in samples if sample.actual_time is not None]
    valid_pair_count = len(intervals)
    coverage = min(1.0, (actual_times[-1] - actual_times[0]) / max(duration, 0.1)) if len(actual_times) > 1 else 0.0
    sampling["validPairCount"] = valid_pair_count
    sampling["coverage"] = round(coverage, 4)
    sampling["decodeSuccessRatio"] = round(sampling["decodedSamples"] / max(sampling["requestedSamples"], 1), 4)
    sampling["sampleTimestamps"] = [
        {
            "requestedTimestamp": round(sample.requested_time, 6),
            "actualTimestamp": None if sample.actual_time is None else round(sample.actual_time, 6),
            "timestampError": None if sample.timestamp_error is None else round(sample.timestamp_error, 6),
        }
        for sample in samples
    ]
    measurement_confidence = round(max(0.0, min(1.0, 0.35 * sampling["decodeSuccessRatio"] + 0.35 * coverage + 0.20 * sampling["timestampAccuracy"] + 0.10 * (1 - sampling["duplicateTimestampRatio"]))), 4)
    overall = float(v4_profile["overallMotion"])
    density = float(np.mean([item["motionDensity"] for item in v4_profile["segments"]])) if v4_profile["segments"] else 0.0
    opening = float(v4_profile["segments"][0]["averageMotion"])
    ending = float(v4_profile["segments"][-1]["averageMotion"])
    score = calculate_motion_heuristic_score(overall, opening, density, ending)
    first = samples[0].frame
    last = samples[-1].frame
    first_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
    last_gray = cv2.cvtColor(last, cv2.COLOR_BGR2GRAY)
    first_last_similarity = max(0.0, min(1.0, 1 - float(np.mean(cv2.absdiff(first_gray, last_gray))) / 255))
    storyboard = _storyboard([SampledFrame(sample.frame, sample.requested_time, sample.actual_time) for sample in samples], metadata.sha256 + "-v4")
    timeline = [
        {"kind": "V4_LOW_MOTION_CANDIDATE", "start": item["startSeconds"], "end": item["endSeconds"], "confidence": measurement_confidence}
        for item in low_candidates
    ]
    return VideoAnalysisResponse(
        metadata=metadata,
        analysisVersion=V4_ANALYSIS_VERSION,
        analysisType="SAMPLED_VISUAL_MOTION_V4",
        primaryEngine="SAMPLED_VISUAL_MOTION_V4",
        secondaryEngines=["STRUCTURAL_NOVELTY", "PERCEPTUAL_HASH"],
        classification="HIGH_MOTION_EVIDENCE" if score >= 60 else "MODERATE_MOTION_EVIDENCE" if score >= 40 else "LOW_MOTION_EVIDENCE",
        motionHeuristicScore=score,
        measurementConfidence=measurement_confidence,
        measurementQuality={
            "decodeSuccessRatio": sampling["decodeSuccessRatio"],
            "timelineCoverage": sampling["coverage"],
            "duplicateTimestampRatio": sampling["duplicateTimestampRatio"],
            "timestampAccuracy": sampling["timestampAccuracy"],
            "validPairCount": valid_pair_count,
        },
        reason="V4 measures uniform sequential image-space motion, temporal structure, and deterministic visual novelty. It does not infer story meaning or platform performance.",
        storyboardPath=storyboard,
        timeline=timeline,
        features={
            "motionIntensity": {"label": _v4_motion_label(overall), "value": overall},
            "temporalConsistency": {"label": _v4_consistency_label(v4_profile), "variation": v4_profile["variation"]},
            "visualNovelty": novelty,
            "actionBeatNovelty": {"status": "NOT_EVALUATED", "reason": "Observed semantic action recognition is not configured."},
            "planRenderFidelity": {"status": "NOT_EVALUATED", "reason": "Plan alignment is completed by the render evidence layer when a production contract is available."},
            "repetitiveMotion": repetition,
        },
        sampling=sampling,
        motion={
            "openingMotionIntensity": round(opening, 4),
            "overallMotionIntensity": round(overall, 4),
            "motionIntervalDensity": round(density, 4),
            "endingMotionEvidence": round(ending, 4),
            "motionEscalationProxy": 0.0,
            "motionEscalationProxyStatus": "TECHNICAL_ONLY",
            "lowMotionCandidates": low_candidates,
            "changeRateUnit": "mean grayscale pixel change per second",
        },
        visualSimilarity={"firstLastVisualSimilarity": round(first_last_similarity, 4)},
        darkFrameCandidates=[],
        evidence={
            "sampleTimes": [sample.requested_time for sample in samples],
            "intervals": intervals,
            "temporalProfile": v4_profile,
            "visualNovelty": novelty,
            "repetitiveMotion": repetition,
            "presentation": _presentation_profile([SampledFrame(sample.frame, sample.requested_time, sample.actual_time) for sample in samples[::max(1, len(samples) // 12)]]),
            "dimensions": {
                "motionIntensity": _v4_motion_label(overall),
                "temporalConsistency": _v4_consistency_label(v4_profile),
                "visualNovelty": "LOW" if novelty["averageNovelty"] < 0.16 else "MODERATE" if novelty["averageNovelty"] < 0.32 else "HIGH",
                "actionBeatNovelty": "NOT_EVALUATED",
                "planRenderFidelity": "NOT_EVALUATED",
            },
        },
    )


def _analyse_v5(path: Path, metadata: VideoMetadata) -> VideoAnalysisResponse:
    """V5 keeps V4 measurements intact and adds contextual readiness evidence."""
    result = _analyse_v4(path, metadata)
    profile = result.evidence.get("temporalProfile", {})
    intervals = result.evidence.get("intervals", [])
    sampling = result.sampling or {}
    confidence = float(result.measurement_confidence or 0.0)
    similarity = float(result.visual_similarity.get("firstLastVisualSimilarity", 0.0))
    hold_events = _v5_hold_events(profile, intervals, metadata.duration_ms / 1000, confidence)
    hook = _v5_hook(profile, [])
    action_novelty = _v5_action_novelty(profile, result.evidence.get("visualNovelty", {}), result.evidence.get("recurrence", {}))
    loop = _v5_loop(similarity, result.evidence.get("recurrence", {}))
    strong_hold = any(item["eventType"] == "LIKELY_PURPOSEFUL_HOLD" and item["holdEmphasis"] == "STRONG" for item in hold_events)
    rebound = any(item["postEventTrend"] == "RISING" and item["reboundMagnitude"] >= 0.12 for item in hold_events)
    payoff_status = "MODERATE" if strong_hold and rebound else "WEAK" if hold_events else "UNKNOWN"
    payoff = {"status": payoff_status, "plannedAlignment": "NOT_EVALUATED", "plannedAlignmentReason": "NO_STRUCTURED_PLAN", "rebound": "STRONG" if rebound else "UNKNOWN", "stateChange": "NOT_EVALUATED", "reason": "Payoff evidence is based on temporal contrast only; plan and semantic consequence evidence are unavailable."}
    fidelity = {"status": "NOT_EVALUATED", "reason": "NO_STRUCTURED_PLAN", "provenance": "No render-time ProductionContract or exact VideoPlanIR was supplied to the ML analyzer."}
    repetition = result.evidence.get("repetitiveMotion", {})
    if repetition.get("classification") == "MODERATE" and action_novelty.get("combinedAssessment") in {"STRONG", "MODERATE"}:
        repetition["interpretation"] = "Some movement repeats, but the observed temporal evidence contains distinct beat changes; repeated mechanics remain context-dependent."
    temporal = dict(profile)
    temporal["version"] = V5_ANALYSIS_VERSION
    temporal["temporalActivityEvents"] = hold_events
    temporal["holdEvidenceStatus"] = "AVAILABLE" if hold_events else "NOT_EVALUATED"
    temporal["reboundEvidence"] = {"status": "AVAILABLE" if hold_events else "NOT_EVALUATED", "sustainedRisingActivity": rebound}
    temporal["hook"] = hook
    temporal["payoff"] = payoff
    temporal["loop"] = loop
    temporal["actionBeatNovelty"] = action_novelty
    temporal["planRenderFidelity"] = fidelity
    temporal["dimensions"] = {**temporal.get("dimensions", {}), "actionBeatNovelty": action_novelty["combinedAssessment"], "planRenderFidelity": "NOT_EVALUATED"}
    result.evidence["temporalProfile"] = temporal
    result.evidence["temporalActivityEvents"] = hold_events
    result.evidence["hook"] = hook
    result.evidence["payoff"] = payoff
    result.evidence["loop"] = loop
    result.evidence["actionBeatNovelty"] = action_novelty
    result.evidence["planRenderFidelity"] = fidelity
    result.features["hook"] = hook
    result.features["payoff"] = payoff
    result.features["loop"] = loop
    result.features["actionBeatNovelty"] = action_novelty
    result.features["planRenderFidelity"] = fidelity
    result.analysis_version = V5_ANALYSIS_VERSION
    result.analysis_type = "SAMPLED_VISUAL_MOTION_V5"
    result.primary_engine = "SAMPLED_VISUAL_MOTION_V5"
    result.reason = "V5 combines deterministic temporal evidence with contextual hold, rebound, hook, payoff, loop, recurrence, and provenance-aware readiness evidence. It does not infer platform performance or fabricate semantic actions."
    return result


def analyse(relative_path: str, analysis_version: str = "sampled-visual-motion-v3") -> VideoAnalysisResponse:
    path = safe_video_path(relative_path)
    metadata = probe(path)
    if analysis_version == V4_ANALYSIS_VERSION:
        return _analyse_v4(path, metadata)
    if analysis_version == V5_ANALYSIS_VERSION:
        return _analyse_v5(path, metadata)
    if analysis_version != "sampled-visual-motion-v3":
        raise ValueError(f"Unsupported video analysis version: {analysis_version}")
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
    temporal_profile = _temporal_profile(intervals, duration)
    presentation_profile = _presentation_profile(frames)
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
            "temporalProfile": temporal_profile,
            "presentation": presentation_profile,
        },
    )
