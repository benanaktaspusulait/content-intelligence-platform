"""Tests for the local character-reference verifier."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest

from app.qa.character_verifier import CharacterVerifier


@pytest.fixture
def verifier() -> CharacterVerifier:
    return CharacterVerifier()


@pytest.fixture
def mock_video(tmp_path: Path) -> Path:
    video_path = tmp_path / "test_video.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1", "-y", str(video_path)],
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("FFmpeg not available")
    return video_path


def write_color_image(path: Path, bgr: tuple[int, int, int]) -> Path:
    assert cv2.imwrite(str(path), np.full((240, 320, 3), bgr, dtype=np.uint8))
    return path


def test_verify_success(verifier: CharacterVerifier, mock_video: Path, tmp_path: Path) -> None:
    reference = write_color_image(tmp_path / "kiko.png", (255, 0, 0))
    result = verifier.verify(mock_video, "Kiko", reference)
    assert result["character_identity_verified"] is True
    assert float(result["confidence"]) >= CharacterVerifier.PASS_THRESHOLD
    assert result["character_identity_issues"] is None
    assert result["validator_version"] == CharacterVerifier.VALIDATOR_VERSION


def test_verify_detects_reference_mismatch(
    verifier: CharacterVerifier, mock_video: Path, tmp_path: Path
) -> None:
    reference = write_color_image(tmp_path / "mimi.png", (0, 0, 255))
    result = verifier.verify(mock_video, "Mimi", reference)
    assert result["character_identity_verified"] is False
    assert result["character_identity_issues"] == "Local reference similarity below threshold"


def test_verify_nonexistent_file(verifier: CharacterVerifier, tmp_path: Path) -> None:
    reference = write_color_image(tmp_path / "kiko.png", (255, 0, 0))
    with pytest.raises(FileNotFoundError):
        verifier.verify(Path("/nonexistent/video.mp4"), "Kiko", reference)


def test_verify_requires_reference(verifier: CharacterVerifier, mock_video: Path) -> None:
    with pytest.raises(FileNotFoundError, match="reference"):
        verifier.verify(mock_video, "Kiko")


@patch("subprocess.run")
def test_extract_first_frame_ffmpeg_not_found(
    mock_run: Mock, verifier: CharacterVerifier, tmp_path: Path
) -> None:
    mock_run.side_effect = FileNotFoundError()
    video_path = tmp_path / "test.mp4"
    video_path.touch()
    with pytest.raises(RuntimeError, match="FFmpeg not found"):
        verifier._extract_first_frame(video_path)


@patch("subprocess.run")
def test_extract_first_frame_ffmpeg_error(
    mock_run: Mock, verifier: CharacterVerifier, tmp_path: Path
) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr=b"Invalid video")
    video_path = tmp_path / "test.mp4"
    video_path.touch()
    with pytest.raises(RuntimeError, match="Failed to extract frame"):
        verifier._extract_first_frame(video_path)
