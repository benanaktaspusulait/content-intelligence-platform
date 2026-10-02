from __future__ import annotations

from typing import Any

import numpy as np

from .frame_analysis import VisualMetrics
from .models import AnalysisResult, Evidence, FixOperation, Issue, VideoMetadata


def clamp(value: float) -> float:
    return round(max(0.0, min(10.0, value)), 1)


def _segment_motion(metrics: VisualMetrics, start: float, end: float) -> float:
    values = [frame.motion for frame in metrics.frames if start <= frame.timestamp <= end]
    return float(np.mean(values)) if values else 0.0


def score(metadata: VideoMetadata, metrics: VisualMetrics, semantic: dict[str, Any], audio: list[Evidence]) -> AnalysisResult:
    duration = metadata.duration
    first_change = metrics.first_meaningful_change
    early_motion = _segment_motion(metrics, 0, min(0.8, duration))
    all_motion = np.array([frame.motion for frame in metrics.frames], dtype=float)
    baseline = max(0.3, float(np.median(all_motion)))
    hook = clamp(4.0 + 3.0 * min(1.0, early_motion / (baseline * 2)) - (3.0 if first_change and first_change > 0.8 else 0.0))
    if metrics.black_intervals and metrics.black_intervals[0].start <= 0.1:
        hook = min(hook, 2.0)
    action = clamp(2.0 + metrics.action_density * 7.5)
    motion_quarters = [_segment_motion(metrics, duration * i / 4, duration * (i + 1) / 4) for i in range(4)]
    escalation = clamp(4.0 + 1.5 * sum(b > a * 1.08 for a, b in zip(motion_quarters, motion_quarters[1:])) - 0.8 * sum(abs(b - a) < 0.08 for a, b in zip(motion_quarters, motion_quarters[1:])))
    final_motion = _segment_motion(metrics, max(0, duration - 2), duration)
    final_score = clamp(4.0 + 4.0 * min(1.0, final_motion / max(0.6, baseline * 2)))
    if any(item.end >= duration - 0.3 for item in metrics.dead_intervals + metrics.black_intervals):
        final_score = max(0.0, final_score - 3.0)
    loop = clamp(2.0 + metrics.final_to_first_similarity * 7.0 - (2.5 if metrics.black_intervals else 0.0))
    dead_total = sum(item.end - item.start for item in metrics.dead_intervals)
    dead_pct = dead_total / duration if duration else 1.0
    pacing = clamp(10.0 - dead_pct * 16.0)
    semantic_confidence = float(semantic.get("confidence", 0.3))
    semantic_available = semantic.get("provider") == "local_vlm"
    goal = clamp(float(semantic.get("goal_score", 5.0 if not semantic_available else 6.0)))
    problem = clamp(float(semantic.get("problem_readability_score", 5.0 if not semantic_available else 6.0)))
    resistance = clamp(float(semantic.get("resistance_score", 5.0 if not semantic_available else 6.0)))
    single_rule = clamp(float(semantic.get("single_rule_score", 5.0 if not semantic_available else 6.0)))
    fake_resolution = clamp(float(semantic.get("fake_resolution_score", 4.0)))
    scores = {
        "first_frame_hook": hook,
        "problem_readability": problem,
        "character_goal": goal,
        "physical_action": action,
        "problem_resistance": resistance,
        "escalation": escalation,
        "single_physical_rule": single_rule,
        "fake_resolution": fake_resolution,
        "final_twist": final_score,
        "loopability": loop,
        "pacing": pacing,
    }
    dna = round(hook * 1.5 + goal * 1.5 + action * 2.0 + resistance * 1.5 + escalation * 1.5 + final_score + loop * 0.5 + single_rule * 0.5, 1)

    issues: list[Issue] = []
    if first_change is not None and first_change > 0.8:
        issues.append(Issue("LATE_HOOK", "warning", 0, first_change, f"First measured meaningful visual change is at {first_change:.2f}s.", "The opening spends the highest-risk feed interval without a strong visual event.", f"Test opening from the existing action near {metrics.strongest_motion_time:.2f}s or trim the passive lead-in.", True))
    if metrics.black_intervals and metrics.black_intervals[0].start <= 0.1:
        interval = metrics.black_intervals[0]
        issues.append(Issue("BLACK_OPENING", "fatal", interval.start, interval.end, "Opening frames are almost entirely black.", "The visual hook is hidden.", "Trim to the first visible frame.", True))
    trailing_black = next((item for item in metrics.black_intervals if item.end >= duration - 0.3), None)
    if trailing_black:
        issues.append(Issue("BLACK_TAIL", "warning", trailing_black.start, trailing_black.end, "Near-black frames occur at the end.", "The punchline and loop are interrupted.", "End on the last visible action frame.", True))
    for interval in metrics.dead_intervals:
        if interval.end - interval.start >= 0.75:
            issues.append(Issue("DEAD_TIME", "warning", interval.start, interval.end, interval.detail, "Pacing pauses without a meaningful visual beat.", "Shorten this hold if dialogue and continuity permit.", interval.start < 1.2 or interval.end > duration - 1.2))
    if metadata.width < 1080 or metadata.height < 1920:
        issues.append(Issue("BELOW_HD_VERTICAL", "warning", 0, duration, f"Source is {metadata.width}x{metadata.height}.", "It is below the 1080x1920 delivery target.", "Create a separate HD delivery derivative; do not overwrite the source.", False))
    if metadata.aspect_ratio > 0.7:
        issues.append(Issue("NOT_VERTICAL", "warning", 0, duration, f"Aspect ratio is {metadata.aspect_ratio:.3f}.", "The frame is not standard 9:16 vertical.", "Human-review framing before publishing.", False))

    fatal = any(item.severity == "fatal" for item in issues)
    repairable = any(item.auto_fixable for item in issues)
    if fatal or dna < 38 or action < 3:
        classification = "AVERAGE/FIXABLE" if repairable and dna >= 28 else "BAD"
    elif dna >= 78 and semantic_confidence >= 0.65 and not issues:
        classification = "WINNER CANDIDATE"
    elif (dna >= 62 and hook >= 6 and final_score >= 5) or (dna >= 55 and action >= 7 and final_score >= 5 and not issues):
        classification = "GOOD"
    else:
        classification = "AVERAGE/FIXABLE"
    if classification == "WINNER CANDIDATE":
        reason = "Strong immediate structure, action escalation, and ending with adequate semantic confidence."
    elif classification == "GOOD":
        reason = "Measured structure is strong overall; only minor or reviewable issues remain."
    elif classification == "AVERAGE/FIXABLE":
        reason = "The footage has useful movement or structure, but specific timing/readability defects should be repaired before publishing."
    else:
        reason = "The current footage lacks enough measurable action structure, and editing alone may not rescue the concept."

    fix_plan: list[FixOperation] = []
    visible_start = max((item.end for item in metrics.black_intervals if item.start <= 0.1), default=0.0)
    if visible_start > 0:
        fix_plan.append(FixOperation("trim_start", start=visible_start, reason="Remove black opening."))
    elif first_change and 0.25 < first_change < 1.5:
        fix_plan.append(FixOperation("trim_start", start=max(0.0, first_change - 0.1), reason="Move first meaningful visual change into the opening 0.8 seconds."))
    if trailing_black:
        fix_plan.append(FixOperation("remove_black_tail", end=max(visible_start + 1.0, trailing_black.start), reason="End before black tail."))
    elif metrics.dead_intervals and metrics.dead_intervals[-1].end >= duration - 0.25:
        fix_plan.append(FixOperation("trim_end", end=metrics.dead_intervals[-1].start, reason="End on action before passive tail."))

    strengths = []
    weaknesses = []
    if hook >= 7:
        strengths.append(f"Opening motion/change is measurable inside the first 0.8s (hook {hook}/10).")
    if action >= 7:
        strengths.append(f"Visual action density is high ({metrics.action_density:.0%} of sampled intervals active).")
    if final_score >= 7:
        strengths.append("The final two seconds contain a comparatively strong visual beat.")
    if not strengths:
        strengths.append("The video remains technically readable enough for human creative review.")
    weaknesses.extend(f"{issue.evidence} {issue.consequence}" for issue in issues[:5])
    if not semantic_available:
        weaknesses.append("Character goal, causal physical rule, and anatomy continuity are not verified without a configured local VLM or human review.")

    timeline = [*metrics.motion_events, *metrics.scene_changes, *metrics.dead_intervals, *metrics.black_intervals]
    timeline.sort(key=lambda item: (item.start, item.kind))
    diagnosis = f"{classification}: first meaningful change at {first_change:.2f}s; action density {metrics.action_density:.0%}; dead time {dead_total:.2f}s." if first_change is not None else f"{classification}: no reliable meaningful-change onset was measured."
    return AnalysisResult(
        video_id=metadata.content_hash[:16], metadata=metadata, classification=classification,
        classification_reason=reason, diagnosis=diagnosis, creative_structure_match=dna,
        confidence=round(0.55 * 0.72 + semantic_confidence * 0.28, 2), scores=scores,
        timeline=timeline, issues=issues, strengths=strengths, weaknesses=weaknesses,
        physical_actions=metrics.motion_events, dead_time=metrics.dead_intervals,
        continuity_findings=[], text_findings=[], audio_findings=audio, fix_plan=fix_plan,
        semantic_notes=semantic, provider=str(semantic.get("provider", "local_heuristic")),
        model=str(semantic.get("model", "opencv+ffmpeg")),
    )
