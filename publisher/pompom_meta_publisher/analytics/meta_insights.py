"""
meta_insights.py — Facebook ve Instagram analytics/insights çekme.

Meta Graph API'den post/reel performans metriklerini çeker:
- Reach (erişim)
- Impressions (gösterim)
- Engagement (etkileşim)
- Views (izlenme)
- Likes, comments, shares
- Video watch time
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..publishing.config import MetaConfig, load_meta_config
from ..publishing.http_client import get_json
from ..publishing.errors import PublishError

log = logging.getLogger("pompom_meta.analytics")


@dataclass
class FacebookInsights:
    """Facebook Post/Reel insights."""
    post_id: str
    reach: int = 0
    impressions: int = 0
    engagement: int = 0
    video_views: int = 0
    video_view_time: int = 0  # milliseconds
    likes: int = 0
    comments: int = 0
    shares: int = 0
    permalink: str = ""
    created_time: str = ""
    raw_data: dict = field(default_factory=dict)


@dataclass
class InstagramInsights:
    """Instagram Reel insights."""
    media_id: str
    reach: int = 0
    impressions: int = 0
    engagement: int = 0
    plays: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    permalink: str = ""
    timestamp: str = ""
    raw_data: dict = field(default_factory=dict)


def get_facebook_post_insights(
    post_id: str,
    *,
    config: MetaConfig | None = None
) -> FacebookInsights:
    """
    Facebook Post/Reel için insights çek.
    
    Args:
        post_id: Facebook post ID (örn: "123456789012345_98765")
        config: Meta configuration (optional)
    
    Returns:
        FacebookInsights object
    """
    cfg = config or load_meta_config()
    token = cfg.facebook_token()
    
    log.info("Fetching Facebook insights for post: %s", post_id)
    
    # Post basic data
    post_data = get_json(
        f"{cfg.graph_base}/{post_id}",
        {
            "fields": "id,permalink_url,created_time,message",
            "access_token": token,
        },
        timeout=cfg.request_timeout,
        retry=cfg.retry_policy,
    )
    
    # Post insights/metrics
    insights_data = get_json(
        f"{cfg.graph_base}/{post_id}/insights",
        {
            "metric": "post_impressions,post_engaged_users,post_video_views,post_video_view_time",
            "access_token": token,
        },
        timeout=cfg.request_timeout,
        retry=cfg.retry_policy,
    )
    
    # Reactions/engagement
    reactions = get_json(
        f"{cfg.graph_base}/{post_id}",
        {
            "fields": "reactions.summary(true),comments.summary(true),shares",
            "access_token": token,
        },
        timeout=cfg.request_timeout,
        retry=cfg.retry_policy,
    )
    
    # Parse insights
    metrics = {}
    for item in insights_data.get("data", []):
        name = item.get("name")
        values = item.get("values", [])
        if values:
            metrics[name] = values[0].get("value", 0)
    
    return FacebookInsights(
        post_id=post_id,
        impressions=metrics.get("post_impressions", 0),
        engagement=metrics.get("post_engaged_users", 0),
        video_views=metrics.get("post_video_views", 0),
        video_view_time=metrics.get("post_video_view_time", 0),
        likes=reactions.get("reactions", {}).get("summary", {}).get("total_count", 0),
        comments=reactions.get("comments", {}).get("summary", {}).get("total_count", 0),
        shares=reactions.get("shares", {}).get("count", 0),
        permalink=post_data.get("permalink_url", ""),
        created_time=post_data.get("created_time", ""),
        raw_data={
            "post": post_data,
            "insights": insights_data,
            "reactions": reactions,
        }
    )


def get_instagram_reel_insights(
    media_id: str,
    *,
    config: MetaConfig | None = None
) -> InstagramInsights:
    """
    Instagram Reel için insights çek.
    
    Args:
        media_id: Instagram media ID (örn: "18012345678901234")
        config: Meta configuration (optional)
    
    Returns:
        InstagramInsights object
    """
    cfg = config or load_meta_config()
    token = cfg.instagram_token()
    
    log.info("Fetching Instagram insights for media: %s", media_id)
    
    # Media basic data
    media_data = get_json(
        f"{cfg.graph_base}/{media_id}",
        {
            "fields": "id,permalink,timestamp,like_count,comments_count,media_type",
            "access_token": token,
        },
        timeout=cfg.request_timeout,
        retry=cfg.retry_policy,
    )
    
    # Reel insights
    # Note: Insights mevcut olmayabilir (24-48 saat delay)
    try:
        insights_data = get_json(
            f"{cfg.graph_base}/{media_id}/insights",
            {
                "metric": "reach,impressions,plays,likes,comments,shares,saves,total_interactions",
                "access_token": token,
            },
            timeout=cfg.request_timeout,
            retry=cfg.retry_policy,
        )
        
        # Parse metrics
        metrics = {}
        for item in insights_data.get("data", []):
            name = item.get("name")
            values = item.get("values", [])
            if values:
                metrics[name] = values[0].get("value", 0)
    except PublishError as e:
        log.warning("Could not fetch insights (may not be available yet): %s", e)
        metrics = {}
    
    return InstagramInsights(
        media_id=media_id,
        reach=metrics.get("reach", 0),
        impressions=metrics.get("impressions", 0),
        plays=metrics.get("plays", 0),
        likes=media_data.get("like_count", 0),
        comments=media_data.get("comments_count", 0),
        shares=metrics.get("shares", 0),
        saves=metrics.get("saves", 0),
        engagement=metrics.get("total_interactions", 0),
        permalink=media_data.get("permalink", ""),
        timestamp=media_data.get("timestamp", ""),
        raw_data={
            "media": media_data,
            "insights": metrics,
        }
    )


def get_page_insights(
    page_id: str | None = None,
    *,
    period: str = "day",
    metrics: list[str] | None = None,
    config: MetaConfig | None = None
) -> dict[str, Any]:
    """
    Facebook Page genel insights çek.
    
    Args:
        page_id: Facebook Page ID (optional, config'den alır)
        period: "day", "week", "days_28", "month", "lifetime"
        metrics: İstenen metrikler listesi
        config: Meta configuration
    
    Returns:
        Metrics dictionary
    """
    cfg = config or load_meta_config()
    page_id = page_id or cfg.page_id
    token = cfg.facebook_token()
    
    if not metrics:
        metrics = [
            "page_impressions",
            "page_engaged_users",
            "page_video_views",
            "page_posts_impressions",
        ]
    
    log.info("Fetching Page insights for: %s", page_id)
    
    data = get_json(
        f"{cfg.graph_base}/{page_id}/insights",
        {
            "metric": ",".join(metrics),
            "period": period,
            "access_token": token,
        },
        timeout=cfg.request_timeout,
        retry=cfg.retry_policy,
    )
    
    result = {}
    for item in data.get("data", []):
        name = item.get("name")
        values = item.get("values", [])
        if values:
            result[name] = values[0].get("value", 0)
    
    return result


def get_account_insights(
    account_id: str | None = None,
    *,
    period: str = "day",
    metrics: list[str] | None = None,
    config: MetaConfig | None = None
) -> dict[str, Any]:
    """
    Instagram Account genel insights çek.
    
    Args:
        account_id: Instagram Account ID (optional, config'den alır)
        period: "day", "week", "days_28", "lifetime"
        metrics: İstenen metrikler listesi
        config: Meta configuration
    
    Returns:
        Metrics dictionary
    """
    cfg = config or load_meta_config()
    account_id = account_id or cfg.instagram_account_id
    token = cfg.instagram_token()
    
    if not metrics:
        metrics = [
            "impressions",
            "reach",
            "profile_views",
        ]
    
    log.info("Fetching Account insights for: %s", account_id)
    
    data = get_json(
        f"{cfg.graph_base}/{account_id}/insights",
        {
            "metric": ",".join(metrics),
            "period": period,
            "access_token": token,
        },
        timeout=cfg.request_timeout,
        retry=cfg.retry_policy,
    )
    
    result = {}
    for item in data.get("data", []):
        name = item.get("name")
        values = item.get("values", [])
        if values:
            result[name] = values[-1].get("value", 0)  # Son değeri al
    
    return result
