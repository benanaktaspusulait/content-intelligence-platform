"""
Performance analyzer: compares predicted quality vs actual performance.
Identifies mispredictions and correlations for rule learning.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from .performance_metrics import PerformanceMetrics, PerformanceTier


@dataclass
class PerformanceInsights:
    """Analysis results comparing predictions with reality"""

    total_videos: int

    # Prediction accuracy
    correct_predictions: int
    false_positives: int  # Predicted GOOD, actually POOR
    false_negatives: int  # Predicted POOR, actually GOOD
    accuracy_rate: float

    # Correlations (Pearson r)
    correlation_score_views: float
    correlation_score_retention: float
    correlation_score_engagement: float

    # Performance by predicted status
    render_ready_performance: dict[str, int] = field(default_factory=dict)
    needs_revision_performance: dict[str, int] = field(default_factory=dict)
    blocked_performance: dict[str, int] = field(default_factory=dict)

    # Misprediction examples
    false_positive_examples: list[str] = field(default_factory=list)
    false_negative_examples: list[str] = field(default_factory=list)

    # Quality family insights (requires detailed validation data)
    # Placeholder for Phase 2 when we link to full validation reports
    top_correlated_families: list[str] = field(default_factory=list)

    def format_report(self) -> str:
        """Format insights as human-readable report"""
        lines = []

        lines.append("=" * 80)
        lines.append("PERFORMANCE ANALYSIS REPORT")
        lines.append("=" * 80)

        lines.append("\n📊 OVERVIEW")
        lines.append(f"  Total videos analyzed: {self.total_videos}")
        lines.append(f"  Prediction accuracy: {self.accuracy_rate:.1%}")
        lines.append(f"  Correct: {self.correct_predictions}")
        lines.append(f"  False positives: {self.false_positives}")
        lines.append(f"  False negatives: {self.false_negatives}")

        lines.append("\n📈 CORRELATIONS (Quality Score vs Performance)")
        lines.append(f"  Views: r = {self.correlation_score_views:.3f}")
        lines.append(f"  Retention: r = {self.correlation_score_retention:.3f}")
        lines.append(f"  Engagement: r = {self.correlation_score_engagement:.3f}")

        lines.append("\n✅ RENDER_READY Performance Distribution")
        for tier, count in sorted(self.render_ready_performance.items()):
            lines.append(f"  {tier}: {count} videos")

        lines.append("\n⚠️  NEEDS_REVISION Performance Distribution")
        for tier, count in sorted(self.needs_revision_performance.items()):
            lines.append(f"  {tier}: {count} videos")

        lines.append("\n❌ BLOCKED Performance Distribution")
        for tier, count in sorted(self.blocked_performance.items()):
            lines.append(f"  {tier}: {count} videos")

        if self.false_positive_examples:
            lines.append("\n🚨 FALSE POSITIVES (Predicted good, performed poor)")
            for example in self.false_positive_examples[:5]:
                lines.append(f"  - {example}")

        if self.false_negative_examples:
            lines.append("\n🤔 FALSE NEGATIVES (Predicted poor, performed good)")
            for example in self.false_negative_examples[:5]:
                lines.append(f"  - {example}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)


class PerformanceAnalyzer:
    """
    Analyzes correlation between quality predictions and actual performance.
    Identifies patterns for rule improvement.
    """

    def __init__(self) -> None:
        pass

    def analyze_performance_data(
        self, performance_data: list[PerformanceMetrics], min_samples: int = 10
    ) -> PerformanceInsights:
        """
        Analyze performance data to measure prediction accuracy.

        Args:
            performance_data: List of PerformanceMetrics
            min_samples: Minimum samples required for analysis

        Returns:
            PerformanceInsights with correlations and accuracy metrics
        """
        if len(performance_data) < min_samples:
            raise ValueError(
                f"Insufficient data: {len(performance_data)} samples (minimum {min_samples} required)"
            )

        # Filter data with predictions
        with_predictions = [
            p for p in performance_data if p.predicted_score is not None and p.predicted_status is not None
        ]

        if len(with_predictions) < min_samples:
            raise ValueError(
                f"Insufficient prediction data: {len(with_predictions)} samples "
                f"(minimum {min_samples} required)"
            )

        # Accuracy metrics
        correct = sum(1 for p in with_predictions if p.actual_performance_match)
        false_positives = 0
        false_negatives = 0

        false_pos_examples = []
        false_neg_examples = []

        for p in with_predictions:
            if p.predicted_status == "RENDER_READY" and p.performance_tier in [
                PerformanceTier.WEAK,
                PerformanceTier.POOR,
            ]:
                false_positives += 1
                false_pos_examples.append(
                    f"{p.video_id}: predicted {p.predicted_score:.0f}, got {p.performance_tier.value}"
                )
            elif p.predicted_status == "BLOCKED" and p.performance_tier in [
                PerformanceTier.EXCELLENT,
                PerformanceTier.GOOD,
            ]:
                false_negatives += 1
                false_neg_examples.append(
                    f"{p.video_id}: predicted {p.predicted_score:.0f}, got {p.performance_tier.value}"
                )

        accuracy_rate = correct / len(with_predictions) if with_predictions else 0.0

        # Correlations
        # ``with_predictions`` is already filtered to require a non-None
        # ``predicted_score`` above, so this is a plain float list at runtime;
        # the assertion lets mypy narrow the type without changing behavior.
        scores = [p.predicted_score for p in with_predictions if p.predicted_score is not None]
        views = [float(p.views_7d) for p in with_predictions]
        retentions = [p.retention_avg_pct for p in with_predictions]
        engagements = [p.engagement_rate for p in with_predictions]

        corr_views = self._pearson_correlation(scores, views)
        corr_retention = self._pearson_correlation(scores, retentions)
        corr_engagement = self._pearson_correlation(scores, engagements)

        # Performance distribution by predicted status
        render_ready_dist: defaultdict[str, int] = defaultdict(int)
        needs_revision_dist: defaultdict[str, int] = defaultdict(int)
        blocked_dist: defaultdict[str, int] = defaultdict(int)

        for p in with_predictions:
            tier = p.performance_tier.value
            if p.predicted_status == "RENDER_READY":
                render_ready_dist[tier] += 1
            elif p.predicted_status == "NEEDS_REVISION":
                needs_revision_dist[tier] += 1
            else:  # BLOCKED
                blocked_dist[tier] += 1

        return PerformanceInsights(
            total_videos=len(with_predictions),
            correct_predictions=correct,
            false_positives=false_positives,
            false_negatives=false_negatives,
            accuracy_rate=accuracy_rate,
            correlation_score_views=corr_views,
            correlation_score_retention=corr_retention,
            correlation_score_engagement=corr_engagement,
            render_ready_performance=dict(render_ready_dist),
            needs_revision_performance=dict(needs_revision_dist),
            blocked_performance=dict(blocked_dist),
            false_positive_examples=false_pos_examples,
            false_negative_examples=false_neg_examples,
        )

    def _pearson_correlation(self, x: list[float], y: list[float]) -> float:
        """
        Calculate Pearson correlation coefficient.

        Returns:
            Correlation r value (-1 to 1)
        """
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        try:
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y, strict=True))
            sum_x2 = sum(xi**2 for xi in x)
            sum_y2 = sum(yi**2 for yi in y)

            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2)) ** 0.5

            if denominator == 0:
                return 0.0

            return float(numerator / denominator)
        except Exception:
            return 0.0

    def identify_underperforming_rules(self, false_positives: list[PerformanceMetrics]) -> dict[str, int]:
        """
        Identify which rules failed to catch poor-performing videos.
        Phase 2: requires linking to full validation reports.

        Returns:
            Dict of rule_id → failure count
        """
        # Placeholder for Phase 2
        # Would analyze which rules passed on videos that performed poorly
        # Suggesting those rules need stricter thresholds
        return {}

    def identify_overly_strict_rules(self, false_negatives: list[PerformanceMetrics]) -> dict[str, int]:
        """
        Identify which rules blocked videos that would have performed well.
        Phase 2: requires human override testing.

        Returns:
            Dict of rule_id → false block count
        """
        # Placeholder for Phase 2
        # Would require testing BLOCKED prompts that humans override
        # and tracking their performance
        return {}
