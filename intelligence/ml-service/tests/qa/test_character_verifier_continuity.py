"""Tests for CharacterVerifier.verify_continuity (multi-frame + reference image)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.qa.character_verifier import CharacterVerifier


@pytest.fixture
def mock_llm_all_pass() -> Mock:
    mock_llm = Mock()
    mock_llm.complete.return_value = json.dumps(
        {
            "character_verified": True,
            "confidence": 0.9,
            "issues": [],
            "reasoning": "Matches reference.",
        }
    )
    return mock_llm


@pytest.fixture
def verifier(mock_llm_all_pass: Mock) -> CharacterVerifier:
    with patch("app.qa.character_verifier.get_provider", return_value=mock_llm_all_pass):
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
    try:
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=320x240:d=1",
            "-vframes",
            "1",
            "-y",
            str(ref_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("FFmpeg not available")
    return ref_path


def test_verify_continuity_all_frames_pass(
    verifier: CharacterVerifier, mock_video: Path, reference_image: Path, mock_llm_all_pass: Mock
) -> None:
    result = verifier.verify_continuity(mock_video, "Kiko", reference_image)

    assert result["character_continuity_verified"] is True
    assert result["confidence"] == 0.9
    assert result["frame_issues"] == {"first": None, "middle": None, "last": None}
    # Called once per sampled frame (first, middle, last).
    assert mock_llm_all_pass.complete.call_count == 3


def test_verify_continuity_fails_if_any_frame_fails(
    verifier: CharacterVerifier, mock_video: Path, reference_image: Path, mock_llm_all_pass: Mock
) -> None:
    responses = [
        json.dumps({"character_verified": True, "confidence": 0.9, "issues": [], "reasoning": "ok"}),
        json.dumps(
            {
                "character_verified": False,
                "confidence": 0.3,
                "issues": ["wrong outfit color"],
                "reasoning": "Outfit drifted to a different color mid-video.",
            }
        ),
        json.dumps({"character_verified": True, "confidence": 0.9, "issues": [], "reasoning": "ok"}),
    ]
    mock_llm_all_pass.complete.side_effect = responses

    result = verifier.verify_continuity(mock_video, "Kiko", reference_image)
    frame_issues = result["frame_issues"]
    assert isinstance(frame_issues, dict)

    assert result["character_continuity_verified"] is False
    assert frame_issues["middle"] == "wrong outfit color"
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
