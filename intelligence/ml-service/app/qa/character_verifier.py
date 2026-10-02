"""Character identity verification using vision LLM."""

import base64
import json
import subprocess
from pathlib import Path

from app.llm import get_provider


class CharacterVerifier:
    """Verifies character identity in video using vision LLM."""

    def __init__(self, llm_provider: str = "openai"):
        """
        Initialize character verifier.

        Args:
            llm_provider: LLM provider to use (default 'openai' for GPT-4V)
        """
        self.llm = get_provider(llm_provider)

    def verify(
        self, video_path: Path, expected_character: str, reference_image_path: Path | None = None
    ) -> dict[str, object]:
        """
        Verify character identity using vision LLM.

        Args:
            video_path: Path to video file
            expected_character: Expected character name (e.g., "Kiko", "Mimi")
            reference_image_path: Optional reference image (not used in current implementation)

        Returns:
            Dict with keys:
                - character_identity_verified: bool
                - confidence: float (0.0-1.0)
                - character_identity_issues: str or None
                - reasoning: str
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Extract first frame
        first_frame_path = self._extract_first_frame(video_path)

        try:
            # Encode image to base64
            with open(first_frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Build verification prompt
            prompt = self._build_verification_prompt(expected_character)

            # Call vision LLM
            response = self.llm.complete(prompt, image=image_data)

            # Parse JSON response
            result = self._parse_llm_response(response)

            issues = result["issues"]
            issue_list = [str(issue) for issue in issues] if isinstance(issues, list) else []

            return {
                "character_identity_verified": result["character_verified"],
                "confidence": result["confidence"],
                "character_identity_issues": ", ".join(issue_list) if issue_list else None,
                "reasoning": result["reasoning"],
            }

        finally:
            # Cleanup temp frame
            if first_frame_path.exists():
                first_frame_path.unlink()

    def verify_continuity(
        self, video_path: Path, expected_character: str, reference_image_path: Path
    ) -> dict[str, object]:
        """
        Verify character identity remains consistent across the video by
        sampling the first, middle, and last frame and judging each against
        the expected character identity.

        Note: LLMProvider.complete() currently supports a single image per
        call, so the reference image itself is not attached to the vision
        call — reference_image_path is validated to exist (fail fast if the
        canonical reference is missing) and reserved for a future multi-image
        upgrade of LLMProvider. Today's comparison relies on the same
        single-frame-against-expected-name judgment as verify(), applied
        three times across the video's duration instead of once.

        Args:
            video_path: Path to the rendered video file
            expected_character: Expected character name (e.g. "Kiko")
            reference_image_path: Path to the character's canonical reference
                image (e.g. the IR's characters.characterRefs[0] value)

        Returns:
            Dict with keys:
                - character_continuity_verified: bool (True only if all 3 frames pass)
                - confidence: float (minimum confidence across the 3 frames)
                - frame_issues: dict with "first"/"middle"/"last" keys, each
                  either None or a comma-joined issues string
                - reasoning: str (combined reasoning across all 3 frames)
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not reference_image_path.exists():
            raise FileNotFoundError(f"Reference image not found: {reference_image_path}")

        duration = self._get_video_duration(video_path)
        timestamps = {"first": 0.0, "middle": duration / 2, "last": max(duration - 0.1, 0.0)}

        frame_issues: dict[str, str | None] = {}
        confidences: list[float] = []
        reasonings: list[str] = []
        all_verified = True

        for frame_label, timestamp in timestamps.items():
            frame_path = self._extract_frame_at(video_path, timestamp, frame_label)
            try:
                with open(frame_path, "rb") as f:
                    frame_image_data = base64.b64encode(f.read()).decode("utf-8")

                prompt = self._build_continuity_prompt(expected_character)
                response = self.llm.complete(prompt, image=frame_image_data)
                result = self._parse_llm_response(response)

                issues = result["issues"]
                issue_list = [str(issue) for issue in issues] if isinstance(issues, list) else []
                frame_issues[frame_label] = ", ".join(issue_list) if issue_list else None

                confidence_value = result["confidence"]
                assert isinstance(confidence_value, (int, float))
                confidences.append(float(confidence_value))
                reasonings.append(f"{frame_label}: {result['reasoning']}")

                if not result["character_verified"]:
                    all_verified = False
            finally:
                if frame_path.exists():
                    frame_path.unlink()

        return {
            "character_continuity_verified": all_verified,
            "confidence": min(confidences) if confidences else 0.0,
            "frame_issues": frame_issues,
            "reasoning": " | ".join(reasonings),
        }

    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)
        except FileNotFoundError as e:
            raise RuntimeError("FFprobe not found. Please install FFmpeg (includes ffprobe).") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to read video duration: {e.stderr}") from e
        return float(result.stdout.strip())

    def _extract_frame_at(self, video_path: Path, timestamp: float, label: str) -> Path:
        """Extract a single frame at `timestamp` seconds into the video."""
        output_path = video_path.parent / f"{video_path.stem}_{label}_frame.png"

        cmd = [
            "ffmpeg",
            "-ss",
            str(timestamp),
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-f",
            "image2",
            "-y",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except FileNotFoundError as e:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract frame: {e.stderr.decode()}") from e

        return output_path

    def _build_continuity_prompt(self, expected_character: str) -> str:
        """Build a verification prompt for a single sampled frame, checked
        against the expected character's established design."""
        return f"""You are verifying character identity consistency in a children's video \
frame, as part of a multi-frame continuity check across the whole video.

Expected character: {expected_character}

Analyze the image and determine:
1. Is {expected_character} clearly visible and identifiable in the image?
2. Are there any visual inconsistencies with {expected_character}'s established design \
(wrong colors, proportions, outfit, or features)?
3. Does the character look consistent with how {expected_character} should appear \
throughout the video (no mid-video design drift)?

Respond in strict JSON format:
{{
  "character_verified": true or false,
  "confidence": 0.0 to 1.0,
  "issues": ["list of any specific issues found, or empty list if none"],
  "reasoning": "brief explanation of your decision"
}}

Important:
- Set character_verified to true only if you're confident this is {expected_character} \
with no visible design drift
- Include specific issues in the issues array (e.g., "outfit color changed")
- Confidence should reflect how certain you are of your verification"""

    def _extract_first_frame(self, video_path: Path) -> Path:
        """
        Extract first frame from video using FFmpeg.

        Args:
            video_path: Path to video file

        Returns:
            Path to extracted frame (PNG)
        """
        output_path = video_path.parent / f"{video_path.stem}_first_frame.png"

        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-f",
            "image2",
            "-y",  # Overwrite output
            str(output_path),
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except FileNotFoundError as e:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg.") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract frame: {e.stderr.decode()}") from e

        return output_path

    def _build_verification_prompt(self, expected_character: str) -> str:
        """
        Build verification prompt for vision LLM.

        Args:
            expected_character: Expected character name

        Returns:
            Prompt string
        """
        return f"""You are verifying character identity in a children's video frame.

Expected character: {expected_character}

Analyze the image and determine:
1. Is {expected_character} clearly visible and identifiable in the image?
2. Is {expected_character} the main focus of the frame?
3. Are there any visual inconsistencies with {expected_character}'s appearance \
(wrong colors, proportions, style, or features)?
4. Does the character match the expected design?

Respond in strict JSON format:
{{
  "character_verified": true or false,
  "confidence": 0.0 to 1.0,
  "issues": ["list of any specific issues found, or empty list if none"],
  "reasoning": "brief explanation of your decision"
}}

Important:
- Set character_verified to true only if you're confident this is {expected_character}
- Include specific issues in the issues array (e.g., "wrong hair color", "proportions incorrect")
- Confidence should reflect how certain you are of your verification"""

    def _parse_llm_response(self, response: str) -> dict[str, object]:
        """
        Parse LLM JSON response.

        Args:
            response: LLM response string

        Returns:
            Parsed dict with character_verified, confidence, issues, reasoning
        """
        try:
            # Try to parse as JSON
            result = json.loads(response)

            # Validate required fields
            required_fields = ["character_verified", "confidence", "issues", "reasoning"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")

            # Validate types
            if not isinstance(result["character_verified"], bool):
                raise ValueError("character_verified must be boolean")

            if not isinstance(result["confidence"], (int, float)):
                raise ValueError("confidence must be number")

            if not isinstance(result["issues"], list):
                raise ValueError("issues must be list")

            if not isinstance(result["reasoning"], str):
                raise ValueError("reasoning must be string")

            # Clamp confidence to [0, 1]
            result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))

            parsed: dict[str, object] = result
            return parsed

        except json.JSONDecodeError as e:
            # Fallback: try to extract JSON from markdown code block
            import re

            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
            if json_match:
                try:
                    return self._parse_llm_response(json_match.group(1))
                except Exception:
                    pass

            raise ValueError(f"Failed to parse LLM response as JSON: {e}") from e
