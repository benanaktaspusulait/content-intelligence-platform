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


def _motion_evidence(metrics: ExistingMetrics) -> dict[str, Any]:
    """Return supplied motion measurements without inventing a quality score."""
    return {
        "opening_motion": metrics.opening_motion,
        "overall_motion": metrics.overall_motion,
        "motion_density": metrics.motion_density,
        "ending_motion": metrics.ending_motion,
        "first_last_similarity": metrics.first_last_similarity,
    }


def _hook_face(frames: list[StoryboardFrame]) -> dict[str, Any]:
    faces = [frame for frame in frames if frame.has_child_face]
    first_face = min(faces, key=lambda frame: frame.timestamp_seconds, default=None)
    if first_face is None:
        return {"first_face_at": None, "has_child_face": False, "reason": "No child face is present in the supplied opening evidence."}
    first_face_at = f"{first_face.timestamp_seconds:.1f}s"
    return {
        "first_face_at": first_face_at,
        "has_child_face": True,
        "early_face_within_0_8s": first_face.timestamp_seconds <= 0.8,
        "early_eye_contact": first_face.timestamp_seconds <= 0.8 and first_face.eye_contact,
        "reason": "Supplied face timing and gaze evidence; camera gaze is optional and not a policy decision.",
    }


def _punchline(transcript: list[TranscriptSegment]) -> TranscriptSegment | None:
    keywords = ("nope", "again", "tomorrow", "ground", "where", "wrong", "but", "actually")
    candidates = [segment for segment in transcript if any(word in segment.text.lower() for word in keywords)]
    return candidates[-1] if candidates else (transcript[-1] if transcript else None)


def _stillness(frames: list[StoryboardFrame], transcript: list[TranscriptSegment]) -> dict[str, Any]:
    punchline = _punchline(transcript)
    if punchline is None:
        return {"punchline_at": None, "motion_at_punchline": None, "reason": "No timestamped punchline evidence was supplied."}
    center = (punchline.start_seconds + punchline.end_seconds) / 2
    nearby = [frame for frame in frames if abs(frame.timestamp_seconds - center) <= 0.5 and frame.motion_density is not None]
    motion = sum(frame.motion_density for frame in nearby) / len(nearby) if nearby else None
    if motion is None:
        return {"punchline_at": f"{center:.2f}s", "motion_at_punchline": None, "reason": "Punchline exists, but local motion evidence is unavailable."}
    return {
        "punchline_at": f"{center:.2f}s",
        "motion_at_punchline": round(motion, 4),
        "reason": "Local motion evidence is supplied for experiment analysis; no fixed stillness target is applied.",
    }


def _text_overlay(frames: list[StoryboardFrame]) -> dict[str, Any]:
    has_text = any(frame.timestamp_seconds <= 2.0 and frame.text_overlay_area_ratio > 0.15 for frame in frames)
    maximum = max((frame.text_overlay_area_ratio for frame in frames if frame.timestamp_seconds <= 2.0), default=0.0)
    return {
        "opening_text_present": maximum > 0,
        "opening_text_max_area_ratio": round(maximum, 4),
        "reason": "Text evidence is recorded for an experiment only; text is not required by production policy.",
    }


def _eye_line(frames: list[StoryboardFrame]) -> dict[str, Any]:
    total = len(frames)
    camera = sum(frame.looks_at_camera for frame in frames) / total
    other = sum(frame.looks_at_other_character for frame in frames) / total
    away = sum(frame.looks_away for frame in frames) / total
    return {"camera_ratio": round(camera, 4), "other_character_ratio": round(other, 4), "away_ratio": round(away, 4), "reason": "Ratios are descriptive evidence only; no target eye-line distribution is enforced."}


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
    return {"silence_gaps_over_0_4s_without_sampled_motion": traps, "reason": "Silence alone is not a production failure; planned visual progression is evaluated elsewhere."}


def _color(frames: list[StoryboardFrame]) -> dict[str, Any]:
    measured = [frame for frame in frames if frame.brightness is not None and frame.saturation is not None]
    if not measured:
        return {"avg_brightness": None, "avg_saturation": None, "reason": "No brightness or saturation measurements were supplied."}
    brightness = sum(frame.brightness for frame in measured) / len(measured)
    saturation = sum(frame.saturation for frame in measured) / len(measured)
    return {"avg_brightness": round(brightness, 2), "avg_saturation": round(saturation, 4), "reason": "Measurements are descriptive evidence; no universal kids-content brightness or saturation target is applied."}


def _loop_sequel(metrics: ExistingMetrics, transcript: list[TranscriptSegment]) -> dict[str, Any]:
    similarity = metrics.first_last_similarity
    text = " ".join(segment.text.lower() for segment in transcript)
    has_hook = any(token in text for token in ("again", "tomorrow", "part 2", "next time"))
    return {"first_last_visual_similarity": similarity, "sequel_words_observed": has_hook, "reason": "Similarity remains independent evidence; transcript words do not create a semantic loop score."}


def assess(request: RetentionAssessmentRequest) -> dict[str, Any]:
    motion = _motion_evidence(request.existing_metrics)
    hook = _hook_face(request.storyboard_frames)
    stillness = _stillness(request.storyboard_frames, request.transcript_with_timestamps)
    text = _text_overlay(request.storyboard_frames)
    eye_line = _eye_line(request.storyboard_frames)
    audio = _audio_silence(request.storyboard_frames, request.audio_analysis)
    color = _color(request.storyboard_frames)
    loop = _loop_sequel(request.existing_metrics, request.transcript_with_timestamps)
    return {
        "assessment_scope": "EXPERIMENT_ONLY",
        "policy_decision": "NOT_APPLICABLE",
        "motion_evidence": motion,
        "hook_face": hook,
        "stillness_punchline": stillness,
        "text_overlay": text,
        "eye_line": eye_line,
        "audio_silence": audio,
        "color_brightness": color,
        "loop_sequel": loop,
    }
