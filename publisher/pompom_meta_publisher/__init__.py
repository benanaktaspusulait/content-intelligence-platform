"""
pompom_meta_publisher — Meta (Facebook + Instagram) publishing for Pompom Hills.

Content-agnostic social publishing module. Knows only about `video_path`,
`caption`, and `content_id`.

    from pompom_meta_publisher.publishing import publish_to_meta

    report = publish_to_meta(
        video_path="path/to/reel.mp4",
        caption="Watch Kiko discover something amazing! 🌟",
        content_id="pompom-reel-001",
    )
"""
__version__ = "0.1.0"
