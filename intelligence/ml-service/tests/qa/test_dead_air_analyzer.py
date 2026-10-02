"""Tests for dead air analyzer."""

from pathlib import Path

import pytest

from app.qa.dead_air_analyzer import DeadAirAnalyzer


class TestDeadAirAnalyzer:
    """Test DeadAirAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> DeadAirAnalyzer:
        """Create analyzer instance."""
        return DeadAirAnalyzer(silence_threshold_db=-50, min_silence_duration=2.0)

    @pytest.fixture
    def mock_video_with_silence(self, tmp_path: Path) -> Path:
        """Create a mock video file with silence using FFmpeg."""
        # Create a 10-second video with 3 seconds of silence in the middle
        # Requires FFmpeg to be installed
        video_path = tmp_path / "test_video_with_silence.mp4"

        # Generate test video: 3s audio, 3s silence, 4s audio
        import subprocess

        try:
            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=3",  # 3s tone
                "-f",
                "lavfi",
                "-i",
                "anullsrc=duration=3",  # 3s silence
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=4",  # 4s tone
                "-filter_complex",
                "[0:a][1:a][2:a]concat=n=3:v=0:a=1",
                "-t",
                "10",
                "-y",
                str(video_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("FFmpeg not available or test video creation failed")

        return video_path

    @pytest.fixture
    def mock_video_no_silence(self, tmp_path: Path) -> Path:
        """Create a mock video file without silence."""
        video_path = tmp_path / "test_video_no_silence.mp4"

        import subprocess

        try:
            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=5",
                "-t",
                "5",
                "-y",
                str(video_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("FFmpeg not available")

        return video_path

    def test_analyze_video_with_silence(
        self, analyzer: DeadAirAnalyzer, mock_video_with_silence: Path
    ) -> None:
        """Test analyzing video with dead air."""
        result = analyzer.analyze(mock_video_with_silence)

        segment_count = result["segment_count"]
        duration_ms = result["total_dead_air_duration_ms"]
        assert isinstance(segment_count, int)
        assert isinstance(duration_ms, int)
        assert result["has_dead_air"] is True
        assert segment_count > 0
        assert duration_ms > 0
        assert isinstance(result["dead_air_segments"], list)

        # Check segment structure
        segments = result["dead_air_segments"]
        assert isinstance(segments, list)
        if segments:
            segment = segments[0]
            assert isinstance(segment, dict)
            assert "start_ms" in segment
            assert "end_ms" in segment
            assert "duration" in segment
            assert segment["end_ms"] > segment["start_ms"]

    def test_analyze_video_no_silence(self, analyzer: DeadAirAnalyzer, mock_video_no_silence: Path) -> None:
        """Test analyzing video without dead air."""
        result = analyzer.analyze(mock_video_no_silence)

        assert result["has_dead_air"] is False
        assert result["segment_count"] == 0
        assert result["total_dead_air_duration_ms"] == 0
        assert result["dead_air_segments"] == []

    def test_analyze_nonexistent_file(self, analyzer: DeadAirAnalyzer) -> None:
        """Test analyzing non-existent file raises error."""
        fake_path = Path("/nonexistent/video.mp4")

        with pytest.raises(FileNotFoundError):
            analyzer.analyze(fake_path)

    def test_custom_thresholds(self) -> None:
        """Test analyzer with custom thresholds."""
        # More sensitive threshold (higher dB)
        sensitive_analyzer = DeadAirAnalyzer(silence_threshold_db=-30, min_silence_duration=1.0)

        assert sensitive_analyzer.silence_threshold_db == -30
        assert sensitive_analyzer.min_silence_duration == 1.0

    def test_parse_ffmpeg_output(self, analyzer: DeadAirAnalyzer) -> None:
        """Test FFmpeg output parsing."""
        # Mock FFmpeg stderr output
        stderr = """
[silencedetect @ 0x7f8] silence_start: 2.5
[silencedetect @ 0x7f8] silence_end: 5.2 | silence_duration: 2.7
[silencedetect @ 0x7f8] silence_start: 8.1
[silencedetect @ 0x7f8] silence_end: 10.5 | silence_duration: 2.4
"""

        segments = analyzer._parse_ffmpeg_output(stderr)

        assert len(segments) == 2

        # First segment
        assert segments[0]["start_ms"] == 2500
        assert segments[0]["end_ms"] == 5200
        assert segments[0]["duration"] == pytest.approx(2.7, abs=0.1)

        # Second segment
        assert segments[1]["start_ms"] == 8100
        assert segments[1]["end_ms"] == 10500
        assert segments[1]["duration"] == pytest.approx(2.4, abs=0.1)
