"""Deterministic short-form retention assessment from supplied evidence.

This is intentionally separate from sampled visual-motion analysis. It does not inspect
platform performance and does not pretend to detect faces, text, or audio from pixels unless
those measurements are supplied by the caller.
"""

from typing import Any

from pydantic import BaseModel, Field


class StoryboardFrame(BaseModel):
    timestamp_seconds: float = Field(alias="timestampSeconds", ge=0)
    has_child_face: bool = Field(default=False, alias="hasChildFace")
    eye_contact: bool = Field(default=False, alias="eyeContact")
    looks_at_camera: bool = Field(default=False, alias="looksAtCamera")
    looks_at_other_character: bool = Field(default=False, alias="looksAtOtherCharacter")
    looks_away: bool = Field(default=False, alias="looksAway")
    text_overlay_area_ratio: float = Field(default=0.0, alias="textOverlayAreaRatio", ge=0, le=1)
    brightness: float | None = Field(default=None, ge=0, le=255)
    saturation: float | None = Field(default=None, ge=0, le=1)
    motion_density: float | None = Field(default=None, alias="motionDensity", ge=0, le=1)


class TranscriptSegment(BaseModel):
    start_seconds: float = Field(alias="startSeconds", ge=0)
    end_seconds: float = Field(alias="endSeconds", ge=0)
    text: str = ""


class SilenceGap(BaseModel):
    start_seconds: float = Field(alias="startSeconds", ge=0)
    end_seconds: float = Field(alias="endSeconds", ge=0)


class AudioAnalysis(BaseModel):
    silence_gaps: list[SilenceGap] = Field(default_factory=list, alias="silenceGaps")
    speech_clarity: float | None = Field(default=None, alias="speechClarity", ge=0, le=1)


class ExistingMetrics(BaseModel):
    opening_motion: float = Field(alias="opening_motion", ge=0, le=1)
    overall_motion: float = Field(alias="overall_motion", ge=0, le=1)
    motion_density: float = Field(alias="motion_density", ge=0, le=1)
    ending_motion: float = Field(alias="ending_motion", ge=0, le=1)
    first_last_similarity: float = Field(alias="first_last_similarity", ge=0, le=1)


class RetentionAssessmentRequest(BaseModel):
    storyboard_frames: list[StoryboardFrame] = Field(alias="storyboard_frames", min_length=1)
    transcript_with_timestamps: list[TranscriptSegment] = Field(
        default_factory=list, alias="transcript_with_timestamps"
    )
    audio_analysis: AudioAnalysis = Field(default_factory=AudioAnalysis, alias="audio_analysis")
    existing_metrics: ExistingMetrics = Field(alias="existing_metrics")


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return round(max(lower, min(upper, value)), 2)


def _motion_score(metrics: ExistingMetrics) -> float:
    score = 100 * (
        0.35 * metrics.overall_motion
        + 0.25 * metrics.opening_motion
        + 0.20 * metrics.motion_density
        + 0.10 * metrics.ending_motion
    )
    if metrics.motion_density >= 1.0:
        score -= 10
    return _clamp(score)


def _hook_face(frames: list[StoryboardFrame]) -> dict[str, Any]:
    faces = [frame for frame in frames if frame.has_child_face]
    first_face = min(faces, key=lambda frame: frame.timestamp_seconds, default=None)
    if first_face is None:
        return {"score": 0, "first_face_at": None, "reason": "No child face is present in the opening evidence."}
    first_face_at = f"{first_face.timestamp_seconds:.1f}s"
    if first_face.timestamp_seconds < 0.8 and first_face.eye_contact:
        return {"score": 100, "first_face_at": first_face_at, "reason": "Face and camera eye contact appear before 0.8s."}
    if first_face.timestamp_seconds <= 0.8:
        return {"score": 70, "first_face_at": first_face_at, "reason": "A child face appears immediately, but early camera eye contact is not evidenced."}
    if first_face.timestamp_seconds <= 1.5:
        return {"score": 50, "first_face_at": first_face_at, "reason": "A child face appears after the strongest opening-hook window."}
    return {"score": 0, "first_face_at": first_face_at, "reason": "The first child face appears after the 1.5s opening window."}


def _punchline(transcript: list[TranscriptSegment]) -> TranscriptSegment | None:
    keywords = ("nope", "again", "tomorrow", "ground", "where", "wrong", "but", "actually")
    candidates = [segment for segment in transcript if any(word in segment.text.lower() for word in keywords)]
    return candidates[-1] if candidates else (transcript[-1] if transcript else None)


def _stillness(frames: list[StoryboardFrame], transcript: list[TranscriptSegment]) -> dict[str, Any]:
    punchline = _punchline(transcript)
    if punchline is None:
        return {"score": 50, "punchline_at": None, "motion_at_punchline": None, "reason": "No timestamped punchline evidence was supplied."}
    center = (punchline.start_seconds + punchline.end_seconds) / 2
    nearby = [frame for frame in frames if abs(frame.timestamp_seconds - center) <= 0.5 and frame.motion_density is not None]
    motion = sum(frame.motion_density for frame in nearby) / len(nearby) if nearby else None
    if motion is None:
        return {"score": 50, "punchline_at": f"{center:.2f}s", "motion_at_punchline": None, "reason": "Punchline exists, but local motion evidence is unavailable."}
    score = 100 if 0.4 <= motion <= 0.6 else 0 if motion >= 0.9 else 50
    reason = "Motion drops into a readable punchline pause." if score == 100 else "Motion does not provide the requested punchline stillness."
    return {"score": score, "punchline_at": f"{center:.2f}s", "motion_at_punchline": round(motion, 4), "reason": reason}


def _text_overlay(frames: list[StoryboardFrame]) -> dict[str, Any]:
    has_text = any(frame.timestamp_seconds <= 2.0 and frame.text_overlay_area_ratio > 0.15 for frame in frames)
    return {"score": 100 if has_text else 0, "reason": "A large opening text overlay is present." if has_text else "No text overlay larger than 15% is present in the first 2s."}


def _eye_line(frames: list[StoryboardFrame]) -> dict[str, Any]:
    total = len(frames)
    camera = sum(frame.looks_at_camera for frame in frames) / total
    other = sum(frame.looks_at_other_character for frame in frames) / total
    away = sum(frame.looks_away for frame in frames) / total
    distance = abs(camera - 0.2) + abs(other - 0.6) + abs(away - 0.2)
    return {"score": _clamp(100 * (1 - distance / 2)), "camera_ratio": round(camera, 4), "other_character_ratio": round(other, 4), "away_ratio": round(away, 4)}


def _audio_silence(frames: list[StoryboardFrame], audio: AudioAnalysis) -> dict[str, Any]:
    traps = 0
    for gap in audio.silence_gaps:
        if gap.end_seconds - gap.start_seconds <= 0.4:
            continue
        moving = any(
            frame.motion_density is not None and frame.motion_density > 0.035
            and gap.start_seconds <= frame.timestamp_seconds <= gap.end_seconds
            for frame in frames
        )
        if not moving:
            traps += 1
    return {"score": _clamp(100 - traps * 25), "traps": traps}


def _color(frames: list[StoryboardFrame]) -> dict[str, Any]:
    measured = [frame for frame in frames if frame.brightness is not None and frame.saturation is not None]
    if not measured:
        return {"score": 50, "avg_brightness": None, "avg_saturation": None, "reason": "No brightness or saturation measurements were supplied."}
    brightness = sum(frame.brightness for frame in measured) / len(measured)
    saturation = sum(frame.saturation for frame in measured) / len(measured)
    brightness_score = 100 if 110 <= brightness <= 180 else 40 if brightness < 90 else 70
    score = brightness_score if saturation > 0.5 else min(brightness_score, 50)
    return {"score": score, "avg_brightness": round(brightness, 2), "avg_saturation": round(saturation, 4), "reason": "Brightness and saturation are in the kids-content target range." if score == 100 else "Color measurements are outside the target range."}


def _loop_sequel(metrics: ExistingMetrics, transcript: list[TranscriptSegment]) -> dict[str, Any]:
    similarity = metrics.first_last_similarity
    base = 100 if 0.75 <= similarity <= 0.85 else _clamp(100 - abs(similarity - 0.8) * 250)
    text = " ".join(segment.text.lower() for segment in transcript)
    has_hook = any(token in text for token in ("again", "tomorrow", "part 2", "next time"))
    return {"score": _clamp(base + (20 if has_hook else 0)), "first_last_similarity": similarity, "has_sequel_hook": has_hook}


def assess(request: RetentionAssessmentRequest) -> dict[str, Any]:
    motion = _motion_score(request.existing_metrics)
    hook = _hook_face(request.storyboard_frames)
    stillness = _stillness(request.storyboard_frames, request.transcript_with_timestamps)
    text = _text_overlay(request.storyboard_frames)
    eye_line = _eye_line(request.storyboard_frames)
    audio = _audio_silence(request.storyboard_frames, request.audio_analysis)
    color = _color(request.storyboard_frames)
    loop = _loop_sequel(request.existing_metrics, request.transcript_with_timestamps)
    final = _clamp(
        motion * 0.20 + hook["score"] * 0.25 + stillness["score"] * 0.15 + text["score"] * 0.15
        + eye_line["score"] * 0.05 + audio["score"] * 0.10 + color["score"] * 0.05 + loop["score"] * 0.05
    )
    prediction = "15K+ lifetime, viral potential" if final >= 90 else "8-12K, target range" if final >= 80 else "3-6K lifetime, average" if final >= 60 else "<3K, below usual range"
    fixes = []
    if text["score"] == 0:
        fixes.append("Add big text in the first 2s")
    if stillness["score"] < 100:
        fixes.append("Drop motion during the punchline")
    if not fixes:
        fixes.append("Keep the opening face hook and punchline contrast")
    return {
        "motion_score": motion,
        "hook_face": hook,
        "stillness_punchline": stillness,
        "text_overlay": text,
        "eye_line": eye_line,
        "audio_silence": audio,
        "color_brightness": color,
        "loop_sequel": loop,
        "final_score": final,
        "prediction": prediction,
        "fix_1": fixes[0],
        "fix_2": fixes[1] if len(fixes) > 1 else "No second fix identified from supplied evidence",
    }
