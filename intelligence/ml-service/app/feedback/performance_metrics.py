"""
Performance metrics data structures for video performance tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class PerformanceTier(Enum):
    """Performance tier classification"""

    EXCELLENT = "EXCELLENT"  # Top 10%
    GOOD = "GOOD"  # Top 25%
    ACCEPTABLE = "ACCEPTABLE"  # Top 50%
    WEAK = "WEAK"  # Bottom 50%
    POOR = "POOR"  # Bottom 25%


@dataclass
class PerformanceMetrics:
    """
    Video performance metrics collected from platform analytics.
    Supports YouTube, TikTok, Instagram Reels.
    """

    # Video identification
    video_id: str
    prompt_id: str | None
    validation_id: int | None

    # Metadata
    title: str
    platform: str  # youtube, tiktok, instagram
    published_at: datetime
    duration_seconds: int

    # View metrics
    views_24h: int = 0
    views_7d: int = 0
    views_30d: int = 0
    views_total: int = 0

    # Retention metrics (percentage)
    retention_avg_pct: float = 0.0  # Average watch percentage
    retention_30s_pct: float = 0.0  # Percentage who watched 30+ seconds

    # Engagement metrics
    likes: int = 0
    comments: int = 0
    shares: int = 0

    ctr_pct: float = 0.0  # Click-through rate (thumbnail → video)
    engagement_rate: float = 0.0  # (likes + comments + shares) / views

    # Performance classification
    performance_tier: PerformanceTier = PerformanceTier.ACCEPTABLE

    # Prediction comparison
    predicted_score: float | None = None
    predicted_status: str | None = None
    actual_performance_match: bool | None = None

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Calculate derived metrics"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

        # Calculate engagement rate
        if self.views_total > 0:
            self.engagement_rate = (self.likes + self.comments + self.shares) / self.views_total * 100

    def calculate_performance_tier(
        self, views_percentile: float, retention_percentile: float
    ) -> PerformanceTier:
        """
        Calculate performance tier based on percentiles.

        Args:
            views_percentile: Percentile rank of views (0-100)
            retention_percentile: Percentile rank of retention (0-100)

        Returns:
            PerformanceTier classification
        """
        # Composite score: 60% views, 40% retention
        composite_percentile = 0.6 * views_percentile + 0.4 * retention_percentile

        if composite_percentile >= 90:
            return PerformanceTier.EXCELLENT
        elif composite_percentile >= 75:
            return PerformanceTier.GOOD
        elif composite_percentile >= 50:
            return PerformanceTier.ACCEPTABLE
        elif composite_percentile >= 25:
            return PerformanceTier.WEAK
        else:
            return PerformanceTier.POOR

    def compare_with_prediction(self, predicted_score: float, predicted_status: str) -> bool:
        """
        Compare actual performance with quality prediction.

        Logic:
        - RENDER_READY (92+) should perform GOOD or EXCELLENT
        - NEEDS_REVISION (80-91) should perform ACCEPTABLE or better
        - BLOCKED (<80) should perform WEAK or POOR

        Returns:
            True if prediction matches reality, False if misprediction
        """
        self.predicted_score = predicted_score
        self.predicted_status = predicted_status

        # Match logic
        if predicted_status == "RENDER_READY":
            match = self.performance_tier in [PerformanceTier.EXCELLENT, PerformanceTier.GOOD]
        elif predicted_status == "NEEDS_REVISION":
            match = self.performance_tier in [
                PerformanceTier.EXCELLENT,
                PerformanceTier.GOOD,
                PerformanceTier.ACCEPTABLE,
            ]
        else:  # BLOCKED
            match = self.performance_tier in [PerformanceTier.WEAK, PerformanceTier.POOR]

        self.actual_performance_match = match
        return match

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "video_id": self.video_id,
            "prompt_id": self.prompt_id,
            "validation_id": self.validation_id,
            "title": self.title,
            "platform": self.platform,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "duration_seconds": self.duration_seconds,
            "views_24h": self.views_24h,
            "views_7d": self.views_7d,
            "views_30d": self.views_30d,
            "views_total": self.views_total,
            "retention_avg_pct": self.retention_avg_pct,
            "retention_30s_pct": self.retention_30s_pct,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "ctr_pct": self.ctr_pct,
            "engagement_rate": self.engagement_rate,
            "performance_tier": self.performance_tier.value,
            "predicted_score": self.predicted_score,
            "predicted_status": self.predicted_status,
            "actual_performance_match": self.actual_performance_match,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class PerformanceBenchmarks:
    """
    Benchmark thresholds for performance tier calculation.
    Updated periodically based on platform norms.
    """

    platform: str

    # View count percentiles (7-day views)
    views_p10: int  # Bottom 10%
    views_p25: int  # Bottom 25%
    views_p50: int  # Median
    views_p75: int  # Top 25%
    views_p90: int  # Top 10%

    # Retention percentiles
    retention_p10: float
    retention_p25: float
    retention_p50: float
    retention_p75: float
    retention_p90: float

    # Last updated
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def calculate_views_percentile(self, views: int) -> float:
        """Calculate percentile rank for view count"""
        if views >= self.views_p90:
            return 90 + (views - self.views_p90) / self.views_p90 * 10
        elif views >= self.views_p75:
            return 75 + (views - self.views_p75) / (self.views_p90 - self.views_p75) * 15
        elif views >= self.views_p50:
            return 50 + (views - self.views_p50) / (self.views_p75 - self.views_p50) * 25
        elif views >= self.views_p25:
            return 25 + (views - self.views_p25) / (self.views_p50 - self.views_p25) * 25
        elif views >= self.views_p10:
            return 10 + (views - self.views_p10) / (self.views_p25 - self.views_p10) * 15
        else:
            return views / self.views_p10 * 10

    def calculate_retention_percentile(self, retention: float) -> float:
        """Calculate percentile rank for retention percentage"""
        if retention >= self.retention_p90:
            return 90 + (retention - self.retention_p90) / (100 - self.retention_p90) * 10
        elif retention >= self.retention_p75:
            return 75 + (retention - self.retention_p75) / (self.retention_p90 - self.retention_p75) * 15
        elif retention >= self.retention_p50:
            return 50 + (retention - self.retention_p50) / (self.retention_p75 - self.retention_p50) * 25
        elif retention >= self.retention_p25:
            return 25 + (retention - self.retention_p25) / (self.retention_p50 - self.retention_p25) * 25
        elif retention >= self.retention_p10:
            return 10 + (retention - self.retention_p10) / (self.retention_p25 - self.retention_p10) * 15
        else:
            return retention / self.retention_p10 * 10


# Default benchmarks (updated monthly from actual data)
DEFAULT_BENCHMARKS = {
    "youtube": PerformanceBenchmarks(
        platform="youtube",
        views_p10=100,
        views_p25=250,
        views_p50=500,
        views_p75=1200,
        views_p90=3000,
        retention_p10=25.0,
        retention_p25=35.0,
        retention_p50=50.0,
        retention_p75=65.0,
        retention_p90=80.0,
    ),
    "tiktok": PerformanceBenchmarks(
        platform="tiktok",
        views_p10=500,
        views_p25=1500,
        views_p50=5000,
        views_p75=15000,
        views_p90=50000,
        retention_p10=30.0,
        retention_p25=45.0,
        retention_p50=60.0,
        retention_p75=75.0,
        retention_p90=85.0,
    ),
    "instagram": PerformanceBenchmarks(
        platform="instagram",
        views_p10=200,
        views_p25=600,
        views_p50=1500,
        views_p75=4000,
        views_p90=12000,
        retention_p10=28.0,
        retention_p25=40.0,
        retention_p50=55.0,
        retention_p75=70.0,
        retention_p90=82.0,
    ),
}
