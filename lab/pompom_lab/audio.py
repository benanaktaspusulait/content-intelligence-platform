from __future__ import annotations

from pathlib import Path

from .ffmpeg_tools import detect_silence
from .models import Evidence, VideoMetadata


class AudioAnalyzer:
    def analyse(self, path: Path, metadata: VideoMetadata) -> list[Evidence]:
        if not metadata.has_audio:
            return [Evidence(0, metadata.duration, "NO_AUDIO", "No audio stream is present.", confidence=1.0)]
        return [
            Evidence(start, end, "AUDIO_SILENCE", "Local FFmpeg silence detector found low audio energy.", end - start, 0.85)
            for start, end in detect_silence(path)
        ]
