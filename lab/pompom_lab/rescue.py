from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from .analyzers.rescue_vlm import RescueVLMAnalyzer
from .config import Settings
from .database import Database
from .ffmpeg_tools import MediaToolError, probe
from .frame_analysis import VisualMetrics, analyse_frames
from .models import RescueBeat, RescueEdit, RescueMoment, RescueResult
from .pipeline import AlreadyAnalysed, Pipeline, discover
from .reports import artifacts

LOGGER = logging.getLogger("pompom.rescue")
PROMPT_VERSION = "stock-creative-rescue-v1"
LABELS = {"A": "PRIME / PUBLISH AS-IS", "B": "STRONG BUT SMALL FIX", "C": "RESCUEABLE", "D": "LOW-VALUE TEST", "E": "DO NOT PUBLISH YET"}


class RescuePipeline:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.base_pipeline = Pipeline(settings, database)

    def analyse_one(self, path: Path, force: bool = False) -> RescueResult:
        metadata = probe(path, self.settings.input_dir)
        video_id = metadata.content_hash[:16]
        if not force and self.database.is_rescue_current(video_id, self.settings.analysis_version, PROMPT_VERSION):
            raise AlreadyAnalysed(video_id)
        try:
            self.base_pipeline.analyse_one(path, force=False)
        except AlreadyAnalysed:
            pass
        self.database.ensure_video(metadata, video_id)
        base_paths = artifacts(self.settings.data_dir, video_id)
        metrics = analyse_frames(path, metadata.duration, base_paths.frames_dir, base_paths.storyboard, self.settings.max_analysis_width)
        semantic = self._semantic(sorted(base_paths.frames_dir.glob("*.jpg")), metrics)
        base_detail = self.database.detail(video_id)
        if not base_detail:
            raise RuntimeError("Base analysis was not persisted")
        result = build_rescue(metadata.filename, video_id, metadata.duration, metrics, semantic, base_detail["analysis"], base_detail["performance"])
        output = self.settings.data_dir / "output" / "rescue" / video_id
        output.mkdir(parents=True, exist_ok=True)
        (output / "rescue_analysis.json").write_text(json.dumps(result.as_dict(), ensure_ascii=False, indent=2) + "\n")
        (output / "rescue_report.md").write_text(rescue_report(result))
        self.database.save_rescue(result, output, self.settings.analysis_version)
        return result

    def analyse_batch(self, target: Path, force: bool = False, limit: int | None = None) -> tuple[int, int, int]:
        completed = skipped = failed = 0
        for index, path in enumerate(discover(target, self.settings.data_dir)):
            if limit is not None and index >= limit:
                break
            try:
                result = self.analyse_one(path, force)
                completed += 1
                LOGGER.info("[%s] rescue %s -> %s %s", result.video_id, path.name, result.classification, result.classification_label)
            except AlreadyAnalysed:
                skipped += 1
            except (MediaToolError, RuntimeError, OSError, ValueError) as exc:
                failed += 1
                LOGGER.exception("Rescue analysis failed for %s: %s", path, exc)
        return completed, skipped, failed

    def _semantic(self, frames: list[Path], metrics: VisualMetrics) -> dict[str, Any]:
        if self.settings.vision_provider == "local_vlm":
            try:
                return RescueVLMAnalyzer(self.settings.vision_base_url, self.settings.vision_model).analyse(frames)
            except RuntimeError as exc:
                LOGGER.warning("Rescue VLM failed: %s; semantic fields remain unverified", exc)
                error = str(exc)
        else:
            error = None
        return {
            "provider": "local_heuristic", "model": "opencv+ffmpeg", "confidence": 0.38,
            "creative_engines": ["UNVERIFIED — HUMAN OR LOCAL VLM REVIEW REQUIRED"],
            "viewer_keeps_watching_because": "The creative reason cannot be inferred responsibly from motion alone.",
            "main_problem": "Creative engine and reveal logic need human or local-VLM review; timing evidence is available.",
            "do_not_change": [], "alternative_pattern": "A different mechanism may be present; preserve it until semantically reviewed.",
            "opening_assessment": "Current opening is compared using measured motion/change only; semantic scroll-stop value is unverified.",
            "final_three_seconds": "Final motion and dead-tail evidence are measured; narrative payoff is unverified.",
            "cta_assessment": "CTA meaning and context are not inferred by the heuristic provider.",
            "reveal_spoiled_by_cold_open": None, "new_footage_needed": False, "new_footage_prompt": None,
            "provider_error": error, "strongest_visual": {"timestamp": metrics.strongest_motion_time, "description": "Strongest measured movement/change peak."},
        }


def build_rescue(filename: str, video_id: str, duration: float, metrics: VisualMetrics, semantic: dict[str, Any], base: dict[str, Any], performance: list[dict[str, Any]]) -> RescueResult:
    hook = float(base["scores"]["first_frame_hook"])
    ending = float(base["scores"]["final_twist"])
    confidence = float(semantic.get("confidence", 0.38))
    engines = [str(item) for item in semantic.get("creative_engines", [])] or ["OTHER / UNVERIFIED"]
    observed = [int(item.get("reach") or item.get("views") or 0) for item in performance]
    observed_max = max(observed, default=0)
    fatal = any(issue["severity"] == "fatal" for issue in base.get("issues", []))
    strongest = metrics.strongest_motion_time
    cold_open_possible = strongest >= 1.0 and not bool(semantic.get("reveal_spoiled_by_cold_open"))
    edits: list[RescueEdit] = []
    first_change = metrics.first_meaningful_change
    if first_change is not None and first_change > 0.8:
        edits.append(RescueEdit("minimal", "start_later", start=max(0.0, first_change - 0.08), reason="Remove setup before the first meaningful visual change."))
    trailing = next((item for item in metrics.black_intervals + metrics.dead_intervals if item.end >= duration - 0.25), None)
    if trailing:
        edits.append(RescueEdit("minimal", "trim_end", end=trailing.start, reason="End before black/static/dead tail."))
    if cold_open_possible:
        teaser_start = max(0.0, strongest - 0.18)
        teaser_end = min(duration, teaser_start + 0.5)
        edits.append(RescueEdit("cold_open", "flash_forward_cold_open", source_start=teaser_start, source_end=teaser_end,
                                reason="A/B test a 0.50s teaser from the strongest measured later event, then hard-cut to the original opening.",
                                semantic_risk=semantic.get("provider") != "local_vlm"))
    if fatal:
        classification, reason, publishing = "E", "A fatal technical/generation issue blocks responsible publication.", "HOLD"
    elif observed_max >= 20_000:
        classification, reason, publishing = "A", f"Observed platform performance ({observed_max:,}) outranks speculative structural assumptions; preserve this cut.", "PRIME SLOT"
    elif semantic.get("provider") == "local_vlm" and hook >= 7 and ending >= 7 and not edits:
        classification, reason, publishing = "A", "Its own identified creative engine is clear, the opening is immediate, and the ending is strong.", "PRIME SLOT"
    elif hook >= 6 and ending >= 5:
        classification, reason, publishing = "B", "The cut is already strong; only a controlled small-fix or A/B experiment is justified.", "NORMAL SLOT"
    elif cold_open_possible or edits:
        classification, reason, publishing = "C", "The footage contains a stronger available moment or removable setup, so edit order may be wasting the idea.", "FIX THEN PRIME"
    else:
        classification, reason, publishing = "D", "No reliable edit-only improvement or verified creative engine is established yet.", "LOW-VALUE / NIGHT TEST"
    if classification == "A":
        edits = []

    moments = _moments(metrics, semantic, duration)
    beats = _beats(metrics, duration, semantic)
    do_not_change = list(semantic.get("do_not_change") or [])
    if metrics.action_density >= 0.7:
        do_not_change.append(f"Preserve the existing high visual-change density ({metrics.action_density:.0%}).")
    if metrics.final_to_first_similarity >= 0.75:
        do_not_change.append("Preserve the visually compatible end-to-start loop potential.")
    optional = "No aggressive experiment is justified from local evidence."
    if cold_open_possible:
        optional = f"A/B test a {teaser_end - teaser_start:.2f}s cold open from {teaser_start:.2f}-{teaser_end:.2f}s against the original/minimal cut; do not replace the original until real platform data is compared."
    main_problem = str(semantic.get("main_problem") or "No semantic diagnosis available.")
    if first_change and first_change > 0.8:
        main_problem += f" The first meaningful measured change arrives at {first_change:.2f}s."
    note = f"Highest imported observed reach/views: {observed_max:,}." if observed_max else None
    new_prompt = semantic.get("new_footage_prompt")
    new_needed = bool(semantic.get("new_footage_needed", False) and semantic.get("provider") == "local_vlm" and new_prompt)
    return RescueResult(
        video_id, filename, classification, LABELS[classification], reason, engines,
        str(semantic.get("viewer_keeps_watching_because") or "Unverified."), hook, ending, moments,
        main_problem, list(dict.fromkeys(do_not_change)), edits, optional,
        str(semantic.get("alternative_pattern") or "No alternative mechanism verified."),
        str(semantic.get("opening_assessment") or "Opening comparison is unverified."),
        str(semantic.get("final_three_seconds") or "Final three seconds require review."),
        str(semantic.get("cta_assessment") or "CTA context requires review."),
        new_needed, str(new_prompt) if new_needed else None, publishing,
        round(0.55 * confidence + 0.45 * float(base.get("confidence", 0.5)), 2), beats,
        str(semantic.get("provider", "local_heuristic")), str(semantic.get("model", "opencv+ffmpeg")),
        performance_override=observed_max >= 20_000, observed_performance_note=note,
    )


def _moments(metrics: VisualMetrics, semantic: dict[str, Any], duration: float) -> list[RescueMoment]:
    result = [RescueMoment("strongest_movement", metrics.strongest_motion_time, "Strongest measured movement/change peak.", 0.72)]
    mapping = {"strongest_visual": "strongest_visual", "biggest_surprise": "biggest_surprise", "funniest_reaction": "funniest_reaction", "clearest_anomaly": "clearest_anomaly", "emotional_frame": "emotional_frame", "strongest_final": "strongest_final"}
    for key, kind in mapping.items():
        value = semantic.get(key)
        if not isinstance(value, dict):
            continue
        timestamp = value.get("timestamp")
        try:
            parsed = max(0.0, min(duration, float(timestamp))) if timestamp is not None else None
        except (TypeError, ValueError):
            parsed = None
        result.append(RescueMoment(kind, parsed, str(value.get("description") or "No description."), float(semantic.get("confidence", 0.4))))
    return result


def _beats(metrics: VisualMetrics, duration: float, semantic: dict[str, Any]) -> list[RescueBeat]:
    semantic_beats = semantic.get("beats")
    if semantic.get("provider") == "local_vlm" and isinstance(semantic_beats, list):
        parsed: list[RescueBeat] = []
        for item in semantic_beats:
            if not isinstance(item, dict):
                continue
            try:
                start = max(0.0, min(duration, float(item["start"])))
                end = max(start, min(duration, float(item["end"])))
            except (KeyError, TypeError, ValueError):
                continue
            parsed.append(RescueBeat(start, end, str(item.get("what_changes") or "Unclear change."),
                                     str(item.get("retention_reason") or "Retention reason unverified."), bool(item.get("risk"))))
        if parsed:
            return parsed
    beats = []
    start = 0.0
    while start < duration:
        end = min(duration, start + 1.5)
        frames = [frame for frame in metrics.frames if start <= frame.timestamp < end]
        motion = float(np.mean([frame.motion for frame in frames])) if frames else 0.0
        difference = float(np.mean([frame.difference for frame in frames])) if frames else 0.0
        level = "High" if motion >= 1.2 or difference >= .08 else "Moderate" if motion >= .55 or difference >= .035 else "Low"
        risk = level == "Low"
        reason = "Semantic retention reason requires review; visual evidence shows " + level.lower() + " change."
        if semantic.get("provider") == "local_vlm":
            reason = "Visual change is measured; use the semantic storyboard assessment to confirm why the beat retains attention."
        beats.append(RescueBeat(round(start, 2), round(end, 2), f"{level} measured visual change.", reason, risk))
        start = end
    return beats


def rescue_report(result: RescueResult) -> str:
    moments = "\n".join(f"- **{item.kind}:** {item.timestamp if item.timestamp is not None else 'unverified'}s - {item.description}" for item in result.best_moments)
    fixes = "\n".join(f"{index}. **{item.variant} / {item.operation}:** {item.reason}" for index, item in enumerate(result.fix_first, 1)) or "No edit should be made only for the sake of editing."
    beats = "\n".join(f"- `{item.start:.2f}-{item.end:.2f}s` {item.what_changes} {item.retention_reason}{' **RETENTION RISK**' if item.risk else ''}" for item in result.beats)
    return f"""# Stock Creative Rescue - {result.filename}

## Classification
**{result.classification} — {result.classification_label}**

{result.classification_reason}

## Creative Engine
{', '.join(result.creative_engine)}

**The viewer keeps watching because:** {result.core_viewer_question}

## Hook and Ending
- Current hook: **{result.hook_score}/10**
- Ending: **{result.ending_score}/10**

## Best Moments
{moments}

## Main Problem
{result.main_problem}

## Current Opening vs Best Available Moment
{result.opening_comparison}

## Final Three Seconds
{result.final_three_seconds}

## CTA Assessment
{result.cta_assessment}

## Do Not Change
{chr(10).join('- ' + item for item in result.do_not_change) or '- Nothing semantically verified yet.'}

## Fix First
{fixes}

## Beat Map
{beats}

## Alternative Winning Pattern
{result.alternative_pattern}

## Optional Experiment
{result.optional_experiment}

## New Footage Needed
**{'YES' if result.new_footage_needed else 'NO'}**

{result.new_footage_prompt or 'Prefer existing footage.'}

## Publishing Use
**{result.publishing_use}**

Confidence: {result.confidence:.0%}

{result.observed_performance_note or ''}

Observed performance is stored separately and outranks speculative structural assumptions. This report does not predict views.
"""
