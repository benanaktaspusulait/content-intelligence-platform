"""Tests for character verifier."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.qa.character_verifier import CharacterVerifier

MockLLMProvider = Mock


class TestCharacterVerifier:
    """Test CharacterVerifier class."""

    @pytest.fixture
    def mock_llm_provider(self) -> MockLLMProvider:
        """Create mock LLM provider."""
        mock_llm = Mock()
        mock_llm.complete.return_value = json.dumps(
            {
                "character_verified": True,
                "confidence": 0.95,
                "issues": [],
                "reasoning": "Character Kiko is clearly visible and matches expected design",
            }
        )
        return mock_llm

    @pytest.fixture
    def verifier(self, mock_llm_provider: MockLLMProvider) -> CharacterVerifier:
        """Create verifier instance with mocked LLM."""
        with patch("app.qa.character_verifier.get_provider", return_value=mock_llm_provider):
            return CharacterVerifier()

    @pytest.fixture
    def mock_video(self, tmp_path: Path) -> Path:
        """Create a mock video file."""
        video_path = tmp_path / "test_video.mp4"

        # Create minimal valid video using FFmpeg
        import subprocess

        try:
            cmd = ["ffmpeg", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1", "-y", str(video_path)]
            subprocess.run(cmd, capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("FFmpeg not available")

        return video_path

    def test_verify_success(
        self, verifier: CharacterVerifier, mock_video: Path, mock_llm_provider: MockLLMProvider
    ) -> None:
        """Test successful character verification."""
        result = verifier.verify(mock_video, "Kiko")

        assert result["character_identity_verified"] is True
        assert result["confidence"] == 0.95
        assert result["character_identity_issues"] is None
        assert result["reasoning"] == "Character Kiko is clearly visible and matches expected design"

        # Verify LLM was called
        mock_llm_provider.complete.assert_called_once()
        call_args = mock_llm_provider.complete.call_args
        prompt_arg = call_args[0][0]
        assert isinstance(prompt_arg, str)
        assert "Kiko" in prompt_arg  # Prompt contains character name
        assert call_args[1]["image"]  # Image data provided

    def test_verify_with_issues(
        self, verifier: CharacterVerifier, mock_video: Path, mock_llm_provider: MockLLMProvider
    ) -> None:
        """Test verification with issues found."""
        mock_llm_provider.complete.return_value = json.dumps(
            {
                "character_verified": False,
                "confidence": 0.6,
                "issues": ["wrong hair color", "proportions incorrect"],
                "reasoning": "Character appearance doesn't match Mimi's design",
            }
        )

        result = verifier.verify(mock_video, "Mimi")

        assert result["character_identity_verified"] is False
        assert result["confidence"] == 0.6
        assert result["character_identity_issues"] == "wrong hair color, proportions incorrect"
        reasoning = result["reasoning"]
        assert isinstance(reasoning, str)
        assert "doesn't match" in reasoning

    def test_verify_nonexistent_file(self, verifier: CharacterVerifier) -> None:
        """Test verifying non-existent file raises error."""
        fake_path = Path("/nonexistent/video.mp4")

        with pytest.raises(FileNotFoundError):
            verifier.verify(fake_path, "Kiko")

    def test_parse_llm_response_valid(self, verifier: CharacterVerifier) -> None:
        """Test parsing valid LLM response."""
        response = json.dumps(
            {"character_verified": True, "confidence": 0.85, "issues": [], "reasoning": "All good"}
        )

        result = verifier._parse_llm_response(response)

        assert result["character_verified"] is True
        assert result["confidence"] == 0.85
        assert result["issues"] == []
        assert result["reasoning"] == "All good"

    def test_parse_llm_response_with_markdown(self, verifier: CharacterVerifier) -> None:
        """Test parsing LLM response wrapped in markdown code block."""
        response = """Here's the analysis:

```json
{
  "character_verified": false,
  "confidence": 0.4,
  "issues": ["unclear identity"],
  "reasoning": "Cannot confidently identify character"
}
```
"""

        result = verifier._parse_llm_response(response)

        assert result["character_verified"] is False
        assert result["confidence"] == 0.4

    def test_parse_llm_response_invalid_json(self, verifier: CharacterVerifier) -> None:
        """Test parsing invalid JSON raises error."""
        with pytest.raises(ValueError, match="Failed to parse"):
            verifier._parse_llm_response("not valid json")

    def test_parse_llm_response_missing_field(self, verifier: CharacterVerifier) -> None:
        """Test parsing response with missing required field."""
        response = json.dumps(
            {
                "character_verified": True,
                "confidence": 0.9,
                # Missing: issues, reasoning
            }
        )

        with pytest.raises(ValueError, match="Missing required field"):
            verifier._parse_llm_response(response)

    def test_parse_llm_response_clamps_confidence(self, verifier: CharacterVerifier) -> None:
        """Test confidence is clamped to [0, 1]."""
        # Test upper bound
        response = json.dumps(
            {"character_verified": True, "confidence": 1.5, "issues": [], "reasoning": "Test"}
        )

        result = verifier._parse_llm_response(response)
        assert result["confidence"] == 1.0

        # Test lower bound
        response = json.dumps(
            {"character_verified": False, "confidence": -0.5, "issues": [], "reasoning": "Test"}
        )

        result = verifier._parse_llm_response(response)
        assert result["confidence"] == 0.0

    def test_build_verification_prompt(self, verifier: CharacterVerifier) -> None:
        """Test prompt building."""
        prompt = verifier._build_verification_prompt("Kiko")

        assert "Kiko" in prompt
        assert "character_verified" in prompt
        assert "confidence" in prompt
        assert "JSON" in prompt

    @patch("subprocess.run")
    def test_extract_first_frame_ffmpeg_not_found(
        self, mock_run: Mock, verifier: CharacterVerifier, tmp_path: Path
    ) -> None:
        """Test FFmpeg not found error."""
        mock_run.side_effect = FileNotFoundError()

        video_path = tmp_path / "test.mp4"
        video_path.touch()

        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            verifier._extract_first_frame(video_path)

    @patch("subprocess.run")
    def test_extract_first_frame_ffmpeg_error(
        self, mock_run: Mock, verifier: CharacterVerifier, tmp_path: Path
    ) -> None:
        """Test FFmpeg execution error."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr=b"Invalid video format")

        video_path = tmp_path / "test.mp4"
        video_path.touch()

        with pytest.raises(RuntimeError, match="Failed to extract frame"):
            verifier._extract_first_frame(video_path)
