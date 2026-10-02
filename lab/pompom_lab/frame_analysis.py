from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .models import Evidence


@dataclass(slots=True)
class FrameMetric:
    timestamp: float
    motion: float
    difference: float
    brightness: float
    entropy: float
    black_ratio: float


@dataclass(slots=True)
class VisualMetrics:
    frames: list[FrameMetric]
    dead_intervals: list[Evidence]
    motion_events: list[Evidence]
    scene_changes: list[Evidence]
    black_intervals: list[Evidence]
    strongest_motion_time: float
    first_meaningful_change: float | None
    final_to_first_similarity: float
    action_density: float


def sample_times(duration: float) -> list[float]:
    points = {0.0}
    t = 0.25
    while t <= min(3.0, duration):
        points.add(round(t, 3))
        t += 0.25
    t = 4.0
    while t < max(0.0, duration - 2.0):
        points.add(round(t, 3))
        t += 1.0
    t = max(0.0, duration - 2.0)
    while t < duration:
        points.add(round(t, 3))
        t += 0.25
    points.add(max(0.0, round(duration - 0.04, 3)))
    return sorted(p for p in points if 0 <= p <= duration)


def _read_frame(capture: cv2.VideoCapture, timestamp: float, max_width: int) -> np.ndarray | None:
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ok, frame = capture.read()
    if not ok or frame is None:
        return None
    if frame.shape[1] > max_width:
        scale = max_width / frame.shape[1]
        frame = cv2.resize(frame, (max_width, max(1, int(frame.shape[0] * scale))), interpolation=cv2.INTER_AREA)
    return frame


def _entropy(gray: np.ndarray) -> float:
    histogram = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    probabilities = histogram / max(1.0, histogram.sum())
    probabilities = probabilities[probabilities > 0]
    return float(-(probabilities * np.log2(probabilities)).sum())


def _intervals(flags: list[bool], times: list[float], kind: str, detail: str, minimum: float) -> list[Evidence]:
    intervals: list[Evidence] = []
    start: float | None = None
    for index, flagged in enumerate(flags):
        if flagged and start is None:
            start = times[index]
        if start is not None and (not flagged or index == len(flags) - 1):
            end = times[index] if not flagged else min(times[index] + 0.25, times[-1])
            if end - start >= minimum:
                intervals.append(Evidence(start, end, kind, detail, round(end - start, 3), 0.9))
            start = None
    return intervals


def analyse_frames(video: Path, duration: float, frames_dir: Path, storyboard: Path, max_width: int = 480) -> VisualMetrics:
    frames_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open {video}")
    times = sample_times(duration)
    metrics: list[FrameMetric] = []
    saved: list[tuple[float, Path]] = []
    previous_gray: np.ndarray | None = None
    first_gray: np.ndarray | None = None
    last_gray: np.ndarray | None = None

    for index, timestamp in enumerate(times):
        frame = _read_frame(capture, timestamp, max_width)
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if first_gray is None:
            first_gray = gray
        difference = 0.0
        motion = 0.0
        if previous_gray is not None and previous_gray.shape == gray.shape:
            difference = float(cv2.absdiff(previous_gray, gray).mean() / 255.0)
            flow = cv2.calcOpticalFlowFarneback(previous_gray, gray, None, 0.5, 2, 12, 2, 5, 1.1, 0)
            magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            motion = float(np.percentile(magnitude, 75))
        brightness = float(gray.mean() / 255.0)
        black_ratio = float(np.mean(gray < 12))
        metrics.append(FrameMetric(timestamp, motion, difference, brightness, _entropy(gray), black_ratio))
        out = frames_dir / f"frame_{index:03d}_{timestamp:07.3f}.jpg"
        cv2.imwrite(str(out), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        saved.append((timestamp, out))
        previous_gray = gray
        last_gray = gray
    capture.release()
    if not metrics:
        raise RuntimeError(f"No frames extracted from {video}")

    motions = np.array([m.motion for m in metrics], dtype=float)
    differences = np.array([m.difference for m in metrics], dtype=float)
    motion_threshold = max(0.55, float(np.percentile(motions, 35)))
    scene_threshold = max(0.16, float(np.percentile(differences, 92)))
    dead_flags = [m.motion < motion_threshold and m.difference < 0.035 for m in metrics]
    black_flags = [m.black_ratio > 0.92 or m.brightness < 0.035 for m in metrics]
    dead = _intervals(dead_flags, [m.timestamp for m in metrics], "DEAD_TIME", "Little meaningful visual change detected.", 0.65)
    black = _intervals(black_flags, [m.timestamp for m in metrics], "BLACK", "Frame is almost entirely black.", 0.15)
    actions = [
        Evidence(m.timestamp, min(duration, m.timestamp + 0.35), "ACTION", "High local motion/change peak.", round(m.motion, 3), 0.68)
        for m in metrics
        if m.motion >= max(1.0, float(np.percentile(motions, 70)))
    ]
    scenes = [
        Evidence(m.timestamp, m.timestamp, "SHOT_CHANGE", "Large whole-frame visual discontinuity.", round(m.difference, 3), 0.78)
        for m in metrics
        if m.difference >= scene_threshold
    ]
    meaningful = next((m.timestamp for m in metrics[1:] if m.motion >= motion_threshold or m.difference >= 0.055), None)
    strongest = metrics[int(np.argmax(motions))].timestamp
    similarity = 0.0
    if first_gray is not None and last_gray is not None and first_gray.shape == last_gray.shape:
        similarity = max(0.0, 1.0 - float(cv2.absdiff(first_gray, last_gray).mean() / 255.0))
    _storyboard(saved, storyboard)
    return VisualMetrics(
        metrics,
        dead,
        actions,
        scenes,
        black,
        strongest,
        meaningful,
        round(similarity, 4),
        round(sum(not flag for flag in dead_flags) / len(dead_flags), 4),
    )


def _storyboard(frames: list[tuple[float, Path]], output: Path) -> None:
    chosen = frames if len(frames) <= 20 else [frames[round(i * (len(frames) - 1) / 19)] for i in range(20)]
    thumbs: list[tuple[float, Image.Image]] = []
    for timestamp, path in chosen:
        image = Image.open(path).convert("RGB")
        image.thumbnail((220, 390))
        thumbs.append((timestamp, image.copy()))
    columns = 5
    cell_w, cell_h = 230, 430
    rows = math.ceil(len(thumbs) / columns)
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "#15191b")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, (timestamp, image) in enumerate(thumbs):
        x = (index % columns) * cell_w + (cell_w - image.width) // 2
        y = (index // columns) * cell_h + 10
        canvas.paste(image, (x, y))
        draw.text((x, y + image.height + 8), f"{timestamp:05.2f}s", fill="#ffffff", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=90)

