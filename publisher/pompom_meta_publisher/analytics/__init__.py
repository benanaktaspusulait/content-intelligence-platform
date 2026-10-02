"""
analytics — Meta Insights ve analytics veri çekme modülü.

Yayınlanmış içerik performansını takip etmek için Meta Graph API'den
engagement metrics, reach, impressions gibi verileri çeker.

    from pompom_meta_publisher.analytics import get_post_insights
    
    insights = get_post_insights(media_id="123456789")
    print(f"Reach: {insights['reach']}")
    print(f"Engagement: {insights['engagement']}")
"""

from .meta_insights import (
    FacebookInsights,
    InstagramInsights,
    get_facebook_post_insights,
    get_instagram_reel_insights,
    get_page_insights,
    get_account_insights,
)

__all__ = [
    "FacebookInsights",
    "InstagramInsights",
    "get_facebook_post_insights",
    "get_instagram_reel_insights",
    "get_page_insights",
    "get_account_insights",
]
