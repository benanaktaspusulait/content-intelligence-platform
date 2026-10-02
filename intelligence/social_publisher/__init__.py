"""
social_publisher — Content-agnostic social publishing for Pompom Hills.

Adapted from Daily Ayat project to work with Pompom Hills Reels.

The publisher only knows three things about a post: `video_path`,
`caption`, and `content_id`. It has no idea what the content is, which is
what makes it reusable.

    from social_publisher.publishing import publish_to_meta

    report = publish_to_meta(
        video_path=master,
        caption=caption,
        content_id="pompom-reel-001",
    )

`social_publisher.common` holds the shared infrastructure: dotenv loading,
typed environment readers, retry policy, generic HTTP client.
"""
__version__ = "0.1.0"
