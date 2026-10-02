"""
tiktok — TikTok Content Posting API entegrasyonu.

TikTok'a video yayınlamak için TikTok for Developers API kullanır.

    from pompom_meta_publisher.tiktok import publish_to_tiktok
    
    report = publish_to_tiktok(
        video_path="output/reel.mp4",
        caption="Amazing content! #PompomHills",
        content_id="pompom-001",
    )
"""

from .tiktok_publisher import (
    publish_to_tiktok,
    publish_tiktok_video,
    TikTokPublishResult,
    TikTokPublishReport,
    verify_tiktok_configuration,
)

__all__ = [
    "publish_to_tiktok",
    "publish_tiktok_video",
    "TikTokPublishResult",
    "TikTokPublishReport",
    "verify_tiktok_configuration",
]
