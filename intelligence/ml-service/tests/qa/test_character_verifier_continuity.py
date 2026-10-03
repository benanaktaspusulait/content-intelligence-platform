"""Tests for local multi-frame character continuity verification."""

import subprocess
from pathlib import Path
from unittest.mock import patch

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
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x240:d=3",
            "-y",
            str(video_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("FFmpeg not available")
    return video_path


@pytest.fixture
def reference_image(tmp_path: Path) -> Path:
    ref_path = tmp_path / "kiko_reference.png"
    assert cv2.imwrite(str(ref_path), np.full((240, 320, 3), (255, 0, 0), dtype=np.uint8))
    return ref_path


def test_verify_continuity_all_frames_pass(
    verifier: CharacterVerifier, mock_video: Path, reference_image: Path
) -> None:
    result = verifier.verify_continuity(mock_video, "Kiko", reference_image)

    assert result["character_continuity_verified"] is True
    assert float(result["confidence"]) >= CharacterVerifier.PASS_THRESHOLD
    assert result["frame_issues"] == {"first": None, "middle": None, "last": None}
    assert result["validator_version"] == CharacterVerifier.VALIDATOR_VERSION


def test_verify_continuity_fails_if_any_frame_fails(
    verifier: CharacterVerifier, mock_video: Path, reference_image: Path
) -> None:
    passing = {
        "passed": True,
        "score": 0.9,
        "histogram_similarity": 0.9,
        "difference_hash_similarity": 0.9,
        "edge_similarity": 0.9,
        "threshold": CharacterVerifier.PASS_THRESHOLD,
    }
    failing = {**passing, "passed": False, "score": 0.2}
    with patch.object(verifier, "_compare_images", side_effect=[passing, failing, passing]):
        result = verifier.verify_continuity(mock_video, "Kiko", reference_image)
    frame_issues = result["frame_issues"]
    assert isinstance(frame_issues, dict)

    assert result["character_continuity_verified"] is False
    assert frame_issues["middle"] == "Local reference similarity below threshold"
    assert frame_issues["first"] is None
    assert frame_issues["last"] is None


def test_verify_continuity_nonexistent_video_raises(
    verifier: CharacterVerifier, reference_image: Path
) -> None:
    with pytest.raises(FileNotFoundError):
        verifier.verify_continuity(Path("/nonexistent/video.mp4"), "Kiko", reference_image)


def test_verify_continuity_nonexistent_reference_raises(
    verifier: CharacterVerifier, mock_video: Path
) -> None:
    with pytest.raises(FileNotFoundError):
        verifier.verify_continuity(mock_video, "Kiko", Path("/nonexistent/ref.png"))
