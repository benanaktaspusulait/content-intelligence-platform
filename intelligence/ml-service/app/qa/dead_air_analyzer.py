"""Dead air (silence) detection using FFmpeg."""

import re
import subprocess
from pathlib import Path


class DeadAirAnalyzer:
    """Detects silent segments (dead air) in video files using FFmpeg."""

    def __init__(self, silence_threshold_db: int = -50, min_silence_duration: float = 2.0):
        """
        Initialize dead air analyzer.

        Args:
            silence_threshold_db: Audio threshold in dB (default -50dB)
            min_silence_duration: Minimum silence duration in seconds (default 2.0s)
        """
        self.silence_threshold_db = silence_threshold_db
        self.min_silence_duration = min_silence_duration

    def analyze(self, video_path: Path) -> dict[str, object]:
        """
        Analyze video for dead air segments.

        Args:
            video_path: Path to video file

        Returns:
            Dict with keys:
                - has_dead_air: bool
                - dead_air_segments: List[Dict] with start_ms, end_ms, duration
                - total_dead_air_duration_ms: int
                - segment_count: int
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        segments = self._detect_silence(video_path)

        has_dead_air = len(segments) > 0
        total_dead_air_duration = sum(seg["duration"] for seg in segments)

        return {
            "has_dead_air": has_dead_air,
            "dead_air_segments": segments,
            "total_dead_air_duration_ms": int(total_dead_air_duration * 1000),
            "segment_count": len(segments),
        }

    def _detect_silence(self, video_path: Path) -> list[dict[str, float]]:
        """
        Use FFmpeg silencedetect filter to find silence segments.

        Args:
            video_path: Path to video file

        Returns:
            List of silence segments with start_ms, end_ms, duration
        """
        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-af",
            f"silencedetect=noise={self.silence_threshold_db}dB:d={self.min_silence_duration}",
            "-f",
            "null",
            "-",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit (FFmpeg returns 1 for null output)
            )
        except FileNotFoundError as e:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.") from e

        # Parse FFmpeg stderr output for silence segments
        segments = self._parse_ffmpeg_output(result.stderr)

        return segments

    def _parse_ffmpeg_output(self, stderr: str) -> list[dict[str, float]]:
        """
        Parse FFmpeg stderr for silence start/end markers.

        Example FFmpeg output:
        [silencedetect @ 0x...] silence_start: 2.5
        [silencedetect @ 0x...] silence_end: 5.2 | silence_duration: 2.7

        Args:
            stderr: FFmpeg stderr output

        Returns:
            List of silence segments
        """
        segments = []
        lines = stderr.split("\n")

        silence_start = None

        for line in lines:
            # Match silence_start
            start_match = re.search(r"silence_start:\s*([\d.]+)", line)
            if start_match:
                silence_start = float(start_match.group(1))

            # Match silence_end
            end_match = re.search(r"silence_end:\s*([\d.]+)", line)
            if end_match and silence_start is not None:
                silence_end = float(end_match.group(1))
                duration = silence_end - silence_start

                segments.append(
                    {
                        "start_ms": int(silence_start * 1000),
                        "end_ms": int(silence_end * 1000),
                        "duration": duration,
                    }
                )

                silence_start = None

        return segments
