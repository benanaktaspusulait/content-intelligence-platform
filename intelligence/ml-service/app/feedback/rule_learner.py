"""
Rule learner: proposes rule adjustments based on performance feedback.
Phase 1: Simple threshold and weight adjustments.
Phase 2: Advanced pattern mining and new rule discovery.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .performance_analyzer import PerformanceAnalyzer
from .performance_metrics import PerformanceMetrics


class ChangeType(Enum):
    """Type of rule adjustment"""

    THRESHOLD_RELAX = "THRESHOLD_RELAX"  # Increase threshold (less strict)
    THRESHOLD_TIGHTEN = "THRESHOLD_TIGHTEN"  # Decrease threshold (more strict)
    WEIGHT_INCREASE = "WEIGHT_INCREASE"  # Increase family weight
    WEIGHT_DECREASE = "WEIGHT_DECREASE"  # Decrease family weight
    SEVERITY_DOWNGRADE = "SEVERITY_DOWNGRADE"  # CRITICAL → WARNING
    SEVERITY_UPGRADE = "SEVERITY_UPGRADE"  # WARNING → CRITICAL


@dataclass
class RuleAdjustment:
    """Proposed rule adjustment based on performance data"""

    rule_id: str
    change_type: ChangeType
    current_value: Any
    proposed_value: Any
    reason: str
    evidence_sample_size: int
    confidence: float  # 0.0-1.0
    requires_approval: bool


class RuleLearner:
    """
    Learns from performance data and proposes rule adjustments.

    Learning strategies:
    1. If high-scoring videos perform poorly → tighten thresholds
    2. If blocked videos perform well (from overrides) → relax thresholds
    3. If family correlates strongly with performance → increase weight
    4. If family shows weak correlation → decrease weight
    """

    def __init__(self, min_samples: int = 50, confidence_threshold: float = 0.7):
        """
        Args:
            min_samples: Minimum samples before proposing adjustment
            confidence_threshold: Minimum confidence to propose change
        """
        self.min_samples = min_samples
        self.confidence_threshold = confidence_threshold
        self.analyzer = PerformanceAnalyzer()

    def learn_from_performance(
        self, performance_data: list[PerformanceMetrics], ruleset_version: str = "1.0"
    ) -> list[RuleAdjustment]:
        """
        Analyze performance data and propose rule adjustments.

        Args:
            performance_data: List of PerformanceMetrics with predictions
            ruleset_version: Current ruleset version

        Returns:
            List of proposed RuleAdjustment objects
        """
        if len(performance_data) < self.min_samples:
            return []

        # Analyze performance
        insights = self.analyzer.analyze_performance_data(performance_data, min_samples=self.min_samples)

        adjustments = []

        # Strategy 1: Tighten rules if false positive rate high
        if insights.false_positives > insights.total_videos * 0.15:
            # More than 15% false positives → rules too lenient
            adjustments.append(
                RuleAdjustment(
                    rule_id="CONCEPT_006",
                    change_type=ChangeType.THRESHOLD_TIGHTEN,
                    current_value=4,
                    proposed_value=5,
                    reason=f"High false positive rate ({insights.false_positives}/{insights.total_videos}). "
                    f"Videos with 4 consequences still performing poorly.",
                    evidence_sample_size=insights.false_positives,
                    confidence=min(0.9, insights.false_positives / insights.total_videos * 3),
                    requires_approval=True,  # BLOCKER change requires approval
                )
            )

        # Strategy 2: Relax rules if false negative rate high
        if insights.false_negatives > insights.total_videos * 0.10:
            # More than 10% false negatives → rules too strict
            adjustments.append(
                RuleAdjustment(
                    rule_id="BEAT_004",
                    change_type=ChangeType.THRESHOLD_RELAX,
                    current_value=30,
                    proposed_value=35,
                    reason=f"High false negative rate ({insights.false_negatives}/{insights.total_videos}). "
                    f"Videos with 30-35% static state performing well.",
                    evidence_sample_size=insights.false_negatives,
                    confidence=min(0.85, insights.false_negatives / insights.total_videos * 5),
                    requires_approval=True,  # CRITICAL threshold change requires approval
                )
            )

        # Strategy 3: Adjust overall scoring if correlation weak
        if insights.correlation_score_views < 0.5:
            # Weak correlation between quality score and views
            adjustments.append(
                RuleAdjustment(
                    rule_id="SCORING_WEIGHTS",
                    change_type=ChangeType.WEIGHT_INCREASE,
                    current_value={"visual_novelty": 0.18, "hook_strength": 0.15},
                    proposed_value={"visual_novelty": 0.22, "hook_strength": 0.18},
                    reason=(
                        f"Quality score shows weak correlation with views "
                        f"(r={insights.correlation_score_views:.2f}). "
                        f"Increase weight on factors that drive initial engagement."
                    ),
                    evidence_sample_size=insights.total_videos,
                    confidence=0.6,
                    requires_approval=False,
                )
            )

        # Strategy 4: If retention correlation strong, increase motion/escalation weight
        if insights.correlation_score_retention > 0.65:
            adjustments.append(
                RuleAdjustment(
                    rule_id="SCORING_WEIGHTS",
                    change_type=ChangeType.WEIGHT_INCREASE,
                    current_value={"escalation": 0.12, "motion_quality": 0.10},
                    proposed_value={"escalation": 0.14, "motion_quality": 0.12},
                    reason=(
                        f"Strong correlation between quality and retention "
                        f"(r={insights.correlation_score_retention:.2f}). "
                        f"Escalation and motion drive watch-through."
                    ),
                    evidence_sample_size=insights.total_videos,
                    confidence=insights.correlation_score_retention,
                    requires_approval=False,
                )
            )

        # Filter by confidence threshold
        adjustments = [adj for adj in adjustments if adj.confidence >= self.confidence_threshold]

        return adjustments

    def format_adjustments(self, adjustments: list[RuleAdjustment]) -> str:
        """Format adjustments as human-readable report"""
        if not adjustments:
            return "No adjustments proposed. Current ruleset performing well."

        lines = []
        lines.append("=" * 80)
        lines.append("PROPOSED RULE ADJUSTMENTS")
        lines.append("=" * 80)

        lines.append(f"\nTotal proposals: {len(adjustments)}")

        requires_approval = [a for a in adjustments if a.requires_approval]
        auto_apply = [a for a in adjustments if not a.requires_approval]

        if requires_approval:
            lines.append(f"\n🔐 REQUIRES APPROVAL ({len(requires_approval)})")
            for adj in requires_approval:
                lines.append(f"\n  Rule: {adj.rule_id}")
                lines.append(f"  Change: {adj.change_type.value}")
                lines.append(f"  Current: {adj.current_value} → Proposed: {adj.proposed_value}")
                lines.append(f"  Confidence: {adj.confidence:.0%}")
                lines.append(f"  Evidence: {adj.evidence_sample_size} samples")
                lines.append(f"  Reason: {adj.reason}")

        if auto_apply:
            lines.append(f"\n✅ AUTO-APPLY ({len(auto_apply)})")
            for adj in auto_apply:
                lines.append(f"\n  Rule: {adj.rule_id}")
                lines.append(f"  Change: {adj.change_type.value}")
                lines.append(f"  Current: {adj.current_value} → Proposed: {adj.proposed_value}")
                lines.append(f"  Confidence: {adj.confidence:.0%}")
                lines.append(f"  Reason: {adj.reason}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)
