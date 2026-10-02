from __future__ import annotations

from pathlib import Path
from typing import Any

from .database import Database
from .ffmpeg_tools import render_candidate


ALLOWED_OPERATIONS = {"trim_start", "trim_end", "remove_black_tail"}


def validate_plan(operations: list[dict[str, Any]], duration: float) -> tuple[float, float]:
    start, end = 0.0, duration
    for operation in operations:
        kind = operation.get("operation")
        if kind not in ALLOWED_OPERATIONS:
            raise ValueError(f"Unsupported or unsafe operation: {kind}")
        if kind == "trim_start":
            start = max(start, float(operation.get("start") or 0.0))
        elif kind in {"trim_end", "remove_black_tail"}:
            end = min(end, float(operation.get("end") or duration))
    if start < 0 or end > duration + 0.01 or end - start < 1.0:
        raise ValueError(f"Invalid candidate interval {start:.3f}-{end:.3f} for {duration:.3f}s source")
    return start, end


def create_candidate(database: Database, data_dir: Path, video_id: str) -> Path:
    detail = database.detail(video_id)
    if not detail:
        raise KeyError(f"Unknown video ID: {video_id}")
    analysis = detail["analysis"]
    operations = analysis.get("fix_plan") or []
    if not operations:
        raise ValueError("No safe automatic fix plan is available")
    start, end = validate_plan(operations, float(detail["duration"]))
    source = Path(detail["path"])
    output = data_dir / "output" / "edited_candidates" / video_id / f"{source.stem}_candidate.mp4"
    render_candidate(source, output, start, end)
    return output
