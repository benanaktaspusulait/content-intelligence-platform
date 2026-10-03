"""Local character-reference similarity checks for rendered video frames."""

import json
import subprocess
from pathlib import Path

import cv2
import numpy as np


class CharacterVerifier:
    """Verifies sampled frames locally against a canonical reference image."""

    VALIDATOR_VERSION = "opencv-reference-similarity-v1"
    PASS_THRESHOLD = 0.55

    def __init__(self, llm_provider: str = "openai"):
        """
        Initialize character verifier.

        Args:
            llm_provider: LLM provider to use (default 'openai' for GPT-4V)
        """
        self.llm_provider = llm_provider

    def verify(
        self, video_path: Path, expected_character: str, reference_image_path: Path | None = None
    ) -> dict[str, object]:
        """
        Verify the first frame against a canonical reference image locally.

        Args:
            video_path: Path to video file
            expected_character: Expected character name (e.g., "Kiko", "Mimi")
            reference_image_path: Required canonical reference image

        Returns:
            Dict with keys:
                - character_identity_verified: bool
                - confidence: float (0.0-1.0)
                - character_identity_issues: str or None
                - reasoning: str
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if reference_image_path is None or not reference_image_path.exists():
            raise FileNotFoundError("A canonical character reference image is required")

        # Extract first frame
        first_frame_path = self._extract_first_frame(video_path)

        try:
            result = self._compare_images(reference_image_path, first_frame_path)
            passed = bool(result["passed"])

            return {
                "character_identity_verified": passed,
                "confidence": result["score"],
                "character_identity_issues": None if passed else "Local reference similarity below threshold",
                "reasoning": self._reasoning(expected_character, result),
                "validator_version": self.VALIDATOR_VERSION,
                "metrics": result,
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
        sampling the first, middle, and last frame and comparing each against
        the canonical reference without transmitting media to an external API.

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
        frame_metrics: dict[str, dict[str, float | bool]] = {}
        all_verified = True

        for frame_label, timestamp in timestamps.items():
            frame_path = self._extract_frame_at(video_path, timestamp, frame_label)
            try:
                result = self._compare_images(reference_image_path, frame_path)
                passed = bool(result["passed"])
                frame_issues[frame_label] = None if passed else "Local reference similarity below threshold"
                confidences.append(float(result["score"]))
                frame_metrics[frame_label] = result
                reasonings.append(f"{frame_label}: {self._reasoning(expected_character, result)}")

                if not passed:
                    all_verified = False
            finally:
                if frame_path.exists():
                    frame_path.unlink()

        return {
            "character_continuity_verified": all_verified,
            "confidence": min(confidences) if confidences else 0.0,
            "frame_issues": frame_issues,
            "reasoning": " | ".join(reasonings),
            "validator_version": self.VALIDATOR_VERSION,
            "frame_timestamps": timestamps,
            "frame_metrics": frame_metrics,
        }

    def _compare_images(self, reference_path: Path, candidate_path: Path) -> dict[str, float | bool]:
        reference = cv2.imread(str(reference_path), cv2.IMREAD_COLOR)
        candidate = cv2.imread(str(candidate_path), cv2.IMREAD_COLOR)
        if reference is None or candidate is None:
            raise RuntimeError("Reference or sampled frame could not be decoded")

        reference = cv2.resize(reference, (256, 256), interpolation=cv2.INTER_AREA)
        candidate = cv2.resize(candidate, (256, 256), interpolation=cv2.INTER_AREA)

        histogram_score = self._histogram_similarity(reference, candidate)
        hash_score = self._difference_hash_similarity(reference, candidate)
        edge_score = self._edge_similarity(reference, candidate)
        score = max(0.0, min(1.0, 0.5 * histogram_score + 0.3 * hash_score + 0.2 * edge_score))

        return {
            "passed": score >= self.PASS_THRESHOLD,
            "score": round(score, 4),
            "histogram_similarity": round(histogram_score, 4),
            "difference_hash_similarity": round(hash_score, 4),
            "edge_similarity": round(edge_score, 4),
            "threshold": self.PASS_THRESHOLD,
        }

    def _histogram_similarity(self, first: np.ndarray, second: np.ndarray) -> float:
        first_hsv = cv2.cvtColor(first, cv2.COLOR_BGR2HSV)
        second_hsv = cv2.cvtColor(second, cv2.COLOR_BGR2HSV)
        first_hist = cv2.calcHist([first_hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        second_hist = cv2.calcHist([second_hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(first_hist, first_hist)
        cv2.normalize(second_hist, second_hist)
        correlation = float(cv2.compareHist(first_hist, second_hist, cv2.HISTCMP_CORREL))
        return max(0.0, min(1.0, correlation))

    def _difference_hash_similarity(self, first: np.ndarray, second: np.ndarray) -> float:
        def difference_hash(image: np.ndarray) -> np.ndarray:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
            return resized[:, 1:] > resized[:, :-1]

        distance = int(np.count_nonzero(difference_hash(first) != difference_hash(second)))
        return 1.0 - distance / 64.0

    def _edge_similarity(self, first: np.ndarray, second: np.ndarray) -> float:
        first_edges = cv2.Canny(first, 80, 160)
        second_edges = cv2.Canny(second, 80, 160)
        first_density = float(np.count_nonzero(first_edges)) / first_edges.size
        second_density = float(np.count_nonzero(second_edges)) / second_edges.size
        return 1.0 - min(1.0, abs(first_density - second_density) / 0.25)

    def _reasoning(self, expected_character: str, result: dict[str, float | bool]) -> str:
        return (
            f"{expected_character} local reference similarity={result['score']} "
            f"(threshold={result['threshold']}, histogram={result['histogram_similarity']}, "
            f"dhash={result['difference_hash_similarity']}, edges={result['edge_similarity']})"
        )

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
