"""
Feedback collector for recording video performance data.
Phase 1: In-memory storage with export capability.
Phase 2: PostgreSQL integration.
"""

from datetime import datetime
from typing import Any

from .performance_metrics import DEFAULT_BENCHMARKS, PerformanceMetrics, PerformanceTier


class FeedbackCollector:
    """
    Collects and stores video performance feedback.
    Links validation predictions with actual performance.
    """

    def __init__(self) -> None:
        """Initialize collector with in-memory storage"""
        self.performance_data: list[PerformanceMetrics] = []

    def record_performance(
        self,
        video_id: str,
        title: str,
        platform: str,
        published_at: datetime,
        duration_seconds: int,
        metrics: dict[str, Any],
        prompt_id: str | None = None,
        validation_id: int | None = None,
        predicted_score: float | None = None,
        predicted_status: str | None = None,
    ) -> PerformanceMetrics:
        """
        Record performance metrics for a rendered video.

        Args:
            video_id: Unique video identifier
            title: Video title
            platform: youtube, tiktok, or instagram
            published_at: Publication timestamp
            duration_seconds: Video duration
            metrics: Dict with views, retention, engagement data
            prompt_id: Original prompt ID (optional)
            validation_id: Quality validation ID (optional)
            predicted_score: Quality score prediction (optional)
            predicted_status: Status prediction (optional)

        Returns:
            PerformanceMetrics object
        """
        # Create metrics object
        perf = PerformanceMetrics(
            video_id=video_id,
            prompt_id=prompt_id,
            validation_id=validation_id,
            title=title,
            platform=platform,
            published_at=published_at,
            duration_seconds=duration_seconds,
            views_24h=metrics.get("views_24h", 0),
            views_7d=metrics.get("views_7d", 0),
            views_30d=metrics.get("views_30d", 0),
            views_total=metrics.get("views_total", 0),
            retention_avg_pct=metrics.get("retention_avg_pct", 0.0),
            retention_30s_pct=metrics.get("retention_30s_pct", 0.0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            ctr_pct=metrics.get("ctr_pct", 0.0),
        )

        # Calculate performance tier
        benchmarks = DEFAULT_BENCHMARKS.get(platform)
        if benchmarks:
            views_pct = benchmarks.calculate_views_percentile(perf.views_7d)
            retention_pct = benchmarks.calculate_retention_percentile(perf.retention_avg_pct)
            perf.performance_tier = perf.calculate_performance_tier(views_pct, retention_pct)

        # Compare with prediction
        if predicted_score and predicted_status:
            perf.compare_with_prediction(predicted_score, predicted_status)

        # Store
        self.performance_data.append(perf)

        return perf

    def get_by_video_id(self, video_id: str) -> PerformanceMetrics | None:
        """Retrieve performance data by video ID"""
        for perf in self.performance_data:
            if perf.video_id == video_id:
                return perf
        return None

    def get_by_prompt_id(self, prompt_id: str) -> list[PerformanceMetrics]:
        """Retrieve all performance data for a prompt ID"""
        return [p for p in self.performance_data if p.prompt_id == prompt_id]

    def get_recent(self, limit: int = 100) -> list[PerformanceMetrics]:
        """Get most recent performance records"""
        # ``created_at`` is populated by ``PerformanceMetrics.__post_init__``
        # for every instance actually constructed, so the ``datetime.min``
        # fallback below is unreachable in practice; it only satisfies the
        # type checker's inability to see that invariant.
        sorted_data = sorted(
            self.performance_data,
            key=lambda p: p.created_at or datetime.min,
            reverse=True,
        )
        return sorted_data[:limit]

    def export_to_dict(self) -> list[dict[str, Any]]:
        """Export all data as list of dicts"""
        return [p.to_dict() for p in self.performance_data]

    def import_from_dict(self, data: list[dict[str, Any]]) -> None:
        """Import data from list of dicts"""
        for item in data:
            perf = PerformanceMetrics(
                video_id=item["video_id"],
                prompt_id=item.get("prompt_id"),
                validation_id=item.get("validation_id"),
                title=item["title"],
                platform=item["platform"],
                published_at=datetime.fromisoformat(item["published_at"]),
                duration_seconds=item["duration_seconds"],
                views_24h=item.get("views_24h", 0),
                views_7d=item.get("views_7d", 0),
                views_30d=item.get("views_30d", 0),
                views_total=item.get("views_total", 0),
                retention_avg_pct=item.get("retention_avg_pct", 0.0),
                retention_30s_pct=item.get("retention_30s_pct", 0.0),
                likes=item.get("likes", 0),
                comments=item.get("comments", 0),
                shares=item.get("shares", 0),
                ctr_pct=item.get("ctr_pct", 0.0),
                engagement_rate=item.get("engagement_rate", 0.0),
                performance_tier=PerformanceTier(item.get("performance_tier", "ACCEPTABLE")),
                predicted_score=item.get("predicted_score"),
                predicted_status=item.get("predicted_status"),
                actual_performance_match=item.get("actual_performance_match"),
            )
            self.performance_data.append(perf)

    def clear(self) -> None:
        """Clear all stored data"""
        self.performance_data = []
