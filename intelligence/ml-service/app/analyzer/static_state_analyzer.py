"""
Static State Analyzer

Detects when a single visual state dominates too much of the video.
Core issue from FAIL_001: Kiko on mat for 42% of video.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class VisualStateMetrics:
    """Metrics about visual state distribution"""

    total_duration: float
    unique_state_count: int

    # State breakdown
    state_durations: dict[str, float]  # {state_id: total_duration}
    state_percentages: dict[str, float]  # {state_id: percentage}

    # Dominant state info
    dominant_state_id: str
    dominant_state_duration: float
    dominant_state_percentage: float

    # Timeline of states
    state_timeline: list[tuple[float, float, str]]  # (start, end, state_id)

    @property
    def passes_critical_threshold(self) -> bool:
        """Check if no state exceeds 35% (critical fail)"""
        return self.dominant_state_percentage <= 35.0

    @property
    def passes_standard_threshold(self) -> bool:
        """Check if no state exceeds 30% (standard threshold)"""
        return self.dominant_state_percentage <= 30.0

    @property
    def passes_recommended_threshold(self) -> bool:
        """Check if no state exceeds 25% (recommended)"""
        return self.dominant_state_percentage <= 25.0

    @property
    def has_good_distribution(self) -> bool:
        """Check if states are well-distributed (4+ states, none > 30%)"""
        return self.unique_state_count >= 4 and self.passes_standard_threshold


class StaticStateAnalyzer:
    """Analyzes visual state distribution in Video Plan IR"""

    def __init__(self) -> None:
        pass

    def analyze(self, video_plan_ir: dict[str, Any]) -> VisualStateMetrics:
        """
        Analyze visual state distribution.

        Key checks:
        1. Group consecutive beats by visualStateId
        2. Sum duration for each state
        3. Calculate percentage of total video
        4. Identify dominant state
        """
        beats = video_plan_ir.get("beats", [])
        total_duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)

        # Guard against a non-positive duration (defense in depth: the parser
        # should never emit 0, but a malformed IR must not cause a divide-by-zero).
        if not beats or total_duration <= 0:
            return self._empty_metrics(total_duration)

        # Group beats by visual state and sum durations
        state_durations = self._calculate_state_durations(beats)

        # Calculate percentages
        state_percentages = {
            state_id: (duration / total_duration) * 100 for state_id, duration in state_durations.items()
        }

        # Find dominant state
        if state_durations:
            dominant_state_id = max(state_durations.keys(), key=lambda k: state_durations[k])
            dominant_duration = state_durations[dominant_state_id]
            dominant_percentage = state_percentages[dominant_state_id]
        else:
            dominant_state_id = "none"
            dominant_duration = 0.0
            dominant_percentage = 0.0

        # Build timeline
        state_timeline = self._build_state_timeline(beats)

        return VisualStateMetrics(
            total_duration=total_duration,
            unique_state_count=len(state_durations),
            state_durations=state_durations,
            state_percentages=state_percentages,
            dominant_state_id=dominant_state_id,
            dominant_state_duration=dominant_duration,
            dominant_state_percentage=dominant_percentage,
            state_timeline=state_timeline,
        )

    def _empty_metrics(self, total_duration: float) -> VisualStateMetrics:
        """Return empty metrics"""
        return VisualStateMetrics(
            total_duration=total_duration,
            unique_state_count=0,
            state_durations={},
            state_percentages={},
            dominant_state_id="none",
            dominant_state_duration=0.0,
            dominant_state_percentage=0.0,
            state_timeline=[],
        )

    def _calculate_state_durations(self, beats: list[dict[str, Any]]) -> dict[str, float]:
        """
        Calculate total duration for each visual state.

        Important: Consecutive beats with the same visualStateId
        should be grouped together.
        """
        state_durations: defaultdict[str, float] = defaultdict(float)

        for beat in beats:
            state_id = beat.get("visualStateId", "unknown")
            duration = beat.get("duration", 0.0)
            state_durations[state_id] += duration

        return dict(state_durations)

    def _build_state_timeline(self, beats: list[dict[str, Any]]) -> list[tuple[float, float, str]]:
        """
        Build timeline showing when each state is active.

        Returns list of (start_time, end_time, state_id).
        """
        timeline = []

        for beat in beats:
            timeline.append((beat["startTime"], beat["endTime"], beat.get("visualStateId", "unknown")))

        return timeline

    def get_state_segments(self, video_plan_ir: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Get contiguous segments of the same visual state.

        Returns list of:
        {
            "stateId": "on_rough_mat",
            "startTime": 3.2,
            "endTime": 11.5,
            "duration": 8.3,
            "percentage": 55.3,
            "beatIds": ["beat_03", "beat_04", "beat_05", "beat_06"]
        }
        """
        beats = video_plan_ir.get("beats", [])
        total_duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)

        if not beats or total_duration <= 0:
            return []

        segments = []
        current_segment = None

        for beat in beats:
            state_id = beat.get("visualStateId", "unknown")

            if current_segment is None or current_segment["stateId"] != state_id:
                # Start new segment
                if current_segment is not None:
                    segments.append(current_segment)

                current_segment = {
                    "stateId": state_id,
                    "startTime": beat["startTime"],
                    "endTime": beat["endTime"],
                    "duration": beat["duration"],
                    "beatIds": [beat["id"]],
                }
            else:
                # Continue current segment
                current_segment["endTime"] = beat["endTime"]
                current_segment["duration"] += beat["duration"]
                current_segment["beatIds"].append(beat["id"])

        # Add final segment
        if current_segment is not None:
            segments.append(current_segment)

        # Calculate percentages
        for segment in segments:
            segment["percentage"] = (segment["duration"] / total_duration) * 100

        return segments

    def detect_static_dominance_issues(self, metrics: VisualStateMetrics) -> list[dict[str, Any]]:
        """
        Detect specific static state issues.

        Returns list of issues with severity and details.
        """
        issues = []

        # Check dominant state percentage
        if metrics.dominant_state_percentage > 35:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "rule": "BEAT_004",
                    "issue": "Static State Dominance",
                    "message": (
                        f"Visual state '{metrics.dominant_state_id}' occupies "
                        f"{metrics.dominant_state_percentage:.1f}% of video. Maximum: 30%."
                    ),
                    "state_id": metrics.dominant_state_id,
                    "percentage": metrics.dominant_state_percentage,
                    "threshold": 30.0,
                }
            )
        elif metrics.dominant_state_percentage > 30:
            issues.append(
                {
                    "severity": "CRITICAL",
                    "rule": "BEAT_004",
                    "issue": "Static State Dominance",
                    "message": (
                        f"Visual state '{metrics.dominant_state_id}' occupies "
                        f"{metrics.dominant_state_percentage:.1f}% of video. Maximum: 30%."
                    ),
                    "state_id": metrics.dominant_state_id,
                    "percentage": metrics.dominant_state_percentage,
                    "threshold": 30.0,
                }
            )
        elif metrics.dominant_state_percentage > 25:
            issues.append(
                {
                    "severity": "WARNING",
                    "rule": "BEAT_004",
                    "issue": "Static State Near Threshold",
                    "message": (
                        f"Visual state '{metrics.dominant_state_id}' occupies "
                        f"{metrics.dominant_state_percentage:.1f}% of video. Consider adding variation."
                    ),
                    "state_id": metrics.dominant_state_id,
                    "percentage": metrics.dominant_state_percentage,
                    "threshold": 25.0,
                }
            )

        # Check for insufficient state variety
        if metrics.unique_state_count < 4:
            issues.append(
                {
                    "severity": "WARNING",
                    "rule": "VISUAL_NOVELTY",
                    "issue": "Insufficient State Variety",
                    "message": (
                        f"Only {metrics.unique_state_count} unique visual states. "
                        "Recommend 4+ for engaging video."
                    ),
                    "state_count": metrics.unique_state_count,
                    "recommended": 4,
                }
            )

        return issues


def analyze_static_states(video_plan_ir: dict[str, Any]) -> VisualStateMetrics:
    """Convenience function to analyze static states"""
    analyzer = StaticStateAnalyzer()
    return analyzer.analyze(video_plan_ir)


def detect_static_state_issues(video_plan_ir: dict[str, Any]) -> list[dict[str, Any]]:
    """Convenience function to detect static state issues"""
    analyzer = StaticStateAnalyzer()
    metrics = analyzer.analyze(video_plan_ir)
    return analyzer.detect_static_dominance_issues(metrics)
