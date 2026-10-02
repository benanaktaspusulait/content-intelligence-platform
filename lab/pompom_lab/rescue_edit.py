from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .database import Database
from .ffmpeg_tools import render_candidate, render_cold_open_candidate


def create_rescue_candidate(database: Database, data_dir: Path, video_id: str, variant: str) -> Path:
    if variant not in {"minimal", "cold_open"}:
        raise ValueError("Variant must be minimal or cold_open")
    detail = database.detail(video_id)
    if not detail or not detail.get("rescue"):
        raise KeyError(f"No Stock Creative Rescue analysis for {video_id}")
    source = Path(detail["path"])
    edits: list[dict[str, Any]] = [item for item in detail["rescue"]["fix_first"] if item["variant"] == variant]
    if not edits:
        raise ValueError(f"No justified {variant} edit exists for this video")
    output_dir = data_dir / "output" / "rescue_candidates" / video_id
    output = output_dir / f"{source.stem}_{variant}.mp4"
    if variant == "minimal":
        start, end = 0.0, float(detail["duration"])
        for edit in edits:
            if edit["operation"] == "start_later" and edit.get("start") is not None:
                start = max(start, float(edit["start"]))
            if edit["operation"] == "trim_end" and edit.get("end") is not None:
                end = min(end, float(edit["end"]))
        if end - start < 1.0:
            raise ValueError("Minimal edit would leave less than one second")
        render_candidate(source, output, start, end)
    else:
        edit = next(item for item in edits if item["operation"] == "flash_forward_cold_open")
        render_cold_open_candidate(source, output, float(edit["source_start"]), float(edit["source_end"]), bool(detail["has_audio"]))
    return output


def comparison(original: dict[str, Any], candidate: dict[str, Any], variant: str) -> dict[str, Any]:
    return {
        "variant": variant,
        "original_video_id": original["id"],
        "candidate_video_id": candidate["id"],
        "rescue_classification": [original.get("rescue_classification"), candidate.get("rescue_classification")],
        "hook_score": [original["rescue"]["hook_score"], candidate["rescue"]["hook_score"]],
        "ending_score": [original["rescue"]["ending_score"], candidate["rescue"]["ending_score"]],
        "duration": [original["duration"], candidate["duration"]],
        "trade_off": "A higher metric does not prove a better story. Compare continuity, reveal preservation, and observed platform performance.",
    }
