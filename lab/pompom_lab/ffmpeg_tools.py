from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .models import VideoMetadata


class MediaToolError(RuntimeError):
    pass


def require_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise MediaToolError(f"Missing required media tools: {', '.join(missing)}")


def run(command: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise MediaToolError(stderr.strip() or str(exc)) from exc


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fraction(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    if "/" not in value:
        return float(value)
    numerator, denominator = value.split("/", 1)
    return float(numerator) / float(denominator or 1)


def probe(path: Path, input_root: Path) -> VideoMetadata:
    require_tools()
    completed = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate",
            "-of",
            "json",
            str(path),
        ]
    )
    try:
        payload: dict[str, Any] = json.loads(completed.stdout)
        video = next(s for s in payload["streams"] if s.get("codec_type") == "video")
    except (json.JSONDecodeError, KeyError, StopIteration) as exc:
        raise MediaToolError(f"No readable video stream in {path}") from exc
    audio = next((s for s in payload["streams"] if s.get("codec_type") == "audio"), None)
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    relative = path.resolve().relative_to(input_root.resolve())
    series = relative.parts[0] if len(relative.parts) > 1 else "Unsorted"
    return VideoMetadata(
        path=str(path.resolve()),
        filename=path.name,
        series=series,
        duration=float(payload.get("format", {}).get("duration") or 0.0),
        fps=_fraction(video.get("r_frame_rate")),
        width=width,
        height=height,
        aspect_ratio=round(width / height, 4) if height else 0.0,
        codec=str(video.get("codec_name") or "unknown"),
        has_audio=audio is not None,
        audio_codec=str(audio.get("codec_name")) if audio else None,
        size_bytes=path.stat().st_size,
        content_hash=file_hash(path),
    )


def detect_silence(path: Path, noise: str = "-38dB", minimum: float = 0.45) -> list[tuple[float, float]]:
    completed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", f"silencedetect=n={noise}:d={minimum}", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    starts: list[float] = []
    intervals: list[tuple[float, float]] = []
    for line in completed.stderr.splitlines():
        if "silence_start:" in line:
            starts.append(float(line.rsplit("silence_start:", 1)[1].strip()))
        elif "silence_end:" in line and starts:
            end = float(line.split("silence_end:", 1)[1].split("|", 1)[0].strip())
            intervals.append((starts.pop(0), end))
    return intervals


def render_candidate(source: Path, output: Path, start: float, end: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-to",
            f"{end:.3f}",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        timeout=600,
    )


def render_cold_open_candidate(source: Path, output: Path, teaser_start: float, teaser_end: float, has_audio: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if teaser_end - teaser_start < 0.15 or teaser_end - teaser_start > 0.8:
        raise ValueError("Cold-open teaser must be between 0.15 and 0.80 seconds")
    if has_audio:
        graph = (
            f"[0:v]trim=start={teaser_start:.3f}:end={teaser_end:.3f},setpts=PTS-STARTPTS[v0];"
            f"[0:a]atrim=start={teaser_start:.3f}:end={teaser_end:.3f},asetpts=PTS-STARTPTS[a0];"
            "[0:v]trim=start=0,setpts=PTS-STARTPTS[v1];[0:a]atrim=start=0,asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]"
        )
        mapping = ["-map", "[v]", "-map", "[a]"]
    else:
        graph = (
            f"[0:v]trim=start={teaser_start:.3f}:end={teaser_end:.3f},setpts=PTS-STARTPTS[v0];"
            "[0:v]trim=start=0,setpts=PTS-STARTPTS[v1];[v0][v1]concat=n=2:v=1:a=0[v]"
        )
        mapping = ["-map", "[v]"]
    run([
        "ffmpeg", "-y", "-i", str(source), "-filter_complex", graph, *mapping,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(output),
    ], timeout=900)
