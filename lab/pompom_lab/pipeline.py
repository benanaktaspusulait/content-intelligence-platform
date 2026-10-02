from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

from .analyzers.base import VisionAnalyzer
from .analyzers.heuristic import LocalHeuristicAnalyzer
from .analyzers.local_vlm import LocalVLMAnalyzer
from .audio import AudioAnalyzer
from .config import Settings
from .database import Database
from .ffmpeg_tools import MediaToolError, probe
from .frame_analysis import analyse_frames
from .models import AnalysisResult
from .reports import artifacts, write_reports
from .scoring import score

LOGGER = logging.getLogger("pompom.pipeline")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


def discover(path: Path, data_dir: Path) -> Iterator[Path]:
    if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
        yield path.resolve()
        return
    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file() or candidate.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if data_dir.resolve() in candidate.resolve().parents:
            continue
        if "Pompom_Creative_Lab" in candidate.parts:
            continue
        yield candidate.resolve()


class Pipeline:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.audio = AudioAnalyzer()

    def analyzer(self) -> VisionAnalyzer:
        if self.settings.vision_provider == "local_vlm":
            return LocalVLMAnalyzer(self.settings.vision_base_url, self.settings.vision_model)
        return LocalHeuristicAnalyzer()

    def analyse_one(self, path: Path, force: bool = False) -> AnalysisResult:
        metadata = probe(path, self.settings.input_dir)
        video_id = metadata.content_hash[:16]
        if not force and self.database.is_current(video_id, self.settings.analysis_version, self.settings.rubric_version):
            detail = self.database.detail(video_id)
            if detail:
                raise AlreadyAnalysed(video_id)
        paths = artifacts(self.settings.data_dir, video_id)
        visual = analyse_frames(path, metadata.duration, paths.frames_dir, paths.storyboard, self.settings.max_analysis_width)
        frame_paths = sorted(paths.frames_dir.glob("*.jpg"))
        analyzer = self.analyzer()
        try:
            semantic = analyzer.analyse(path, metadata, visual, frame_paths)
        except RuntimeError as exc:
            LOGGER.warning("Semantic provider failed for %s: %s; falling back to local heuristics", path, exc)
            semantic = LocalHeuristicAnalyzer().analyse(path, metadata, visual, frame_paths)
            semantic["provider_error"] = str(exc)
        audio = self.audio.analyse(path, metadata)
        result = score(metadata, visual, semantic, audio)
        result.rubric_version = self.settings.rubric_version
        result.software_version = self.settings.analysis_version
        write_reports(result, paths)
        self.database.save(result, paths.root, self.settings.analysis_version)
        return result

    def analyse_batch(self, target: Path, force: bool = False, limit: int | None = None) -> tuple[int, int, int]:
        completed = skipped = failed = 0
        for index, path in enumerate(discover(target, self.settings.data_dir)):
            if limit is not None and index >= limit:
                break
            try:
                result = self.analyse_one(path, force=force)
                completed += 1
                LOGGER.info("[%s] %s -> %s (%.1f)", result.video_id, path.name, result.classification, result.creative_structure_match)
            except AlreadyAnalysed:
                skipped += 1
                LOGGER.info("Skipped current analysis: %s", path)
            except (MediaToolError, RuntimeError, OSError, ValueError) as exc:
                failed += 1
                LOGGER.exception("Analysis failed for %s: %s", path, exc)
        return completed, skipped, failed


class AlreadyAnalysed(RuntimeError):
    pass

