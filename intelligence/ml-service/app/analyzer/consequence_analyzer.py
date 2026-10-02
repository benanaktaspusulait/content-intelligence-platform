"""
Consequence Counter and Analyzer

Analyzes Video Plan IR to count and evaluate consequences.
Key metrics:
- Total distinct consequences
- Consequence distribution across timeline
- Novelty gaps (time between new consequences)
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ConsequenceMetrics:
    """Metrics about consequences in a video"""

    total_beats: int
    distinct_consequence_count: int
    repeat_count: int
    continuation_count: int
    escalation_count: int

    # Timeline analysis
    longest_novelty_gap_seconds: float
    longest_gap_start_time: float
    longest_gap_end_time: float

    # Distribution
    novelty_distribution: list[tuple[float, bool]]  # (timestamp, is_new)

    # Percentage metrics
    distinct_percentage: float  # % of beats that are truly new

    @property
    def passes_minimum_threshold(self) -> bool:
        """Check if meets minimum 4 distinct consequences"""
        return self.distinct_consequence_count >= 4

    @property
    def passes_recommended_threshold(self) -> bool:
        """Check if meets recommended 5+ distinct consequences"""
        return self.distinct_consequence_count >= 5


class ConsequenceAnalyzer:
    """Analyzes consequences in Video Plan IR"""

    def __init__(self) -> None:
        pass

    def analyze(self, video_plan_ir: dict[str, Any]) -> ConsequenceMetrics:
        """
        Analyze consequence distribution in video plan.

        Returns ConsequenceMetrics with all relevant data.
        """
        beats = video_plan_ir.get("beats", [])

        if not beats:
            return self._empty_metrics()

        # Count consequence types
        distinct_count = sum(1 for beat in beats if beat.get("isNewConsequence", False))
        repeat_count = sum(1 for beat in beats if beat.get("consequenceType") == "repeat")
        continuation_count = sum(1 for beat in beats if beat.get("consequenceType") == "continuation")
        escalation_count = sum(1 for beat in beats if beat.get("consequenceType") == "escalation")

        # Analyze timeline gaps
        gap_info = self._find_longest_novelty_gap(beats)

        # Build novelty distribution
        novelty_dist = [(beat["startTime"], beat.get("isNewConsequence", False)) for beat in beats]

        # Calculate percentages
        distinct_percentage = (distinct_count / len(beats)) * 100 if beats else 0.0

        return ConsequenceMetrics(
            total_beats=len(beats),
            distinct_consequence_count=distinct_count,
            repeat_count=repeat_count,
            continuation_count=continuation_count,
            escalation_count=escalation_count,
            longest_novelty_gap_seconds=gap_info["gap_duration"],
            longest_gap_start_time=gap_info["gap_start"],
            longest_gap_end_time=gap_info["gap_end"],
            novelty_distribution=novelty_dist,
            distinct_percentage=distinct_percentage,
        )

    def _empty_metrics(self) -> ConsequenceMetrics:
        """Return empty metrics for videos with no beats"""
        return ConsequenceMetrics(
            total_beats=0,
            distinct_consequence_count=0,
            repeat_count=0,
            continuation_count=0,
            escalation_count=0,
            longest_novelty_gap_seconds=0.0,
            longest_gap_start_time=0.0,
            longest_gap_end_time=0.0,
            novelty_distribution=[],
            distinct_percentage=0.0,
        )

    def _find_longest_novelty_gap(self, beats: list[dict[str, Any]]) -> dict[str, float]:
        """
        Find the longest time gap between new consequences.

        Returns dict with gap_duration, gap_start, gap_end.
        """
        if not beats:
            return {"gap_duration": 0.0, "gap_start": 0.0, "gap_end": 0.0}

        # Find all timestamps where new consequences appear
        new_consequence_times = [beat["startTime"] for beat in beats if beat.get("isNewConsequence", False)]

        if len(new_consequence_times) <= 1:
            # Only one or zero new consequences - gap is entire video or none
            if new_consequence_times:
                total_duration = beats[-1]["endTime"]
                return {
                    "gap_duration": total_duration - new_consequence_times[0],
                    "gap_start": new_consequence_times[0],
                    "gap_end": total_duration,
                }
            else:
                return {"gap_duration": 0.0, "gap_start": 0.0, "gap_end": 0.0}

        # Find longest gap between consecutive new consequences
        max_gap = 0.0
        max_gap_start = 0.0
        max_gap_end = 0.0

        for i in range(len(new_consequence_times) - 1):
            gap = new_consequence_times[i + 1] - new_consequence_times[i]
            if gap > max_gap:
                max_gap = gap
                max_gap_start = new_consequence_times[i]
                max_gap_end = new_consequence_times[i + 1]

        return {"gap_duration": max_gap, "gap_start": max_gap_start, "gap_end": max_gap_end}

    def get_consequence_timeline(self, video_plan_ir: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Return a timeline view of consequences for visualization.

        Returns list of:
        {
            "time": 2.5,
            "type": "new" | "repeat" | "continuation",
            "action": "slides on floor",
            "isNew": true
        }
        """
        beats = video_plan_ir.get("beats", [])

        timeline = []
        for beat in beats:
            timeline.append(
                {
                    "time": beat["startTime"],
                    "type": beat.get("consequenceType", "unknown"),
                    "action": beat.get("action", ""),
                    "isNew": beat.get("isNewConsequence", False),
                    "intensity": beat.get("intensity", 5),
                }
            )

        return timeline


def analyze_consequences(video_plan_ir: dict[str, Any]) -> ConsequenceMetrics:
    """Convenience function to analyze consequences"""
    analyzer = ConsequenceAnalyzer()
    return analyzer.analyze(video_plan_ir)
