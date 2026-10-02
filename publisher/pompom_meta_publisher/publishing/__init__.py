"""
publishing — Content agnostic social publishing layer.

The only thing this package knows about a post is `video_path`,
`caption`, and `content_id`, so any Pompom Hills content can use it.

    from pompom_meta_publisher.publishing import publish_to_meta

    report = publish_to_meta(
        video_path="output/final-reel.mp4",
        caption=caption_text,
        content_id="pompom-reel-001",
    )
"""
from .captions import extract_markdown_section, read_caption
from .config import MetaConfig, load_meta_config
from .errors import (
    MetaApiError,
    MetaAuthenticationError,
    MetaConfigurationError,
    MetaProcessingTimeout,
    MetaRateLimitError,
    MetaStorageError,
    MetaUploadError,
    PublishError,
)
from .ledger import PublicationRecord, PublishLedger
from .meta_publisher import (
    FACEBOOK,
    INSTAGRAM,
    PublishReport,
    PublishResult,
    publish_facebook_reel,
    publish_instagram_reel,
    publish_to_meta,
    verify_configuration,
    wait_until_media_ready,
)
from .storage import (
    NullStorage,
    PublicDirectoryStorage,
    S3CompatibleStorage,
    UrlTemplateStorage,
    VideoStorage,
    create_storage,
)

__all__ = [
    "FACEBOOK",
    "INSTAGRAM",
    "MetaApiError",
    "MetaAuthenticationError",
    "MetaConfig",
    "MetaConfigurationError",
    "MetaProcessingTimeout",
    "MetaRateLimitError",
    "MetaStorageError",
    "MetaUploadError",
    "NullStorage",
    "PublicDirectoryStorage",
    "PublicationRecord",
    "PublishError",
    "PublishLedger",
    "PublishReport",
    "PublishResult",
    "S3CompatibleStorage",
    "UrlTemplateStorage",
    "VideoStorage",
    "create_storage",
    "extract_markdown_section",
    "load_meta_config",
    "publish_facebook_reel",
    "publish_instagram_reel",
    "publish_to_meta",
    "read_caption",
    "verify_configuration",
    "wait_until_media_ready",
]
