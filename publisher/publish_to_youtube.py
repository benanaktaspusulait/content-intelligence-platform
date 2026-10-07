#!/usr/bin/env python3
"""
publish_to_youtube.py — YouTube Shorts Publishing CLI

Upload videos to YouTube as Shorts.

Usage:
    python publish_to_youtube.py video.mp4 "Title" --description "Description"
    python publish_to_youtube.py video.mp4 "Title" -d "Desc" --tags "tag1,tag2,tag3"
    python publish_to_youtube.py video.mp4 "Title" --content-id "my-video-001"
    python publish_to_youtube.py video.mp4 "Title" --force  # Re-upload even if exists
    
    # Dry-run (test without uploading)
    YOUTUBE_DRY_RUN=true python publish_to_youtube.py video.mp4 "Title"
"""
import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pompom_youtube_publisher import (
    load_youtube_config,
    publish_to_youtube,
    verify_youtube_configuration,
)
from pompom_publisher_common import PublishLedger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("youtube_cli")


def main():
    parser = argparse.ArgumentParser(
        description="Upload videos to YouTube as Shorts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "video",
        type=Path,
        help="Path to video file (MP4, vertical 9:16, ≤60s)",
    )
    parser.add_argument(
        "title",
        type=str,
        help="Video title (max 100 chars)",
    )
    parser.add_argument(
        "-d", "--description",
        type=str,
        default="",
        help="Video description (auto-adds #Shorts)",
    )
    parser.add_argument(
        "-t", "--tags",
        type=str,
        default="",
        help="Comma-separated tags (e.g., 'kids,animation,shorts')",
    )
    parser.add_argument(
        "--content-id",
        type=str,
        default="",
        help="Unique content ID for duplicate detection (default: video filename)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-upload even if already published",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify configuration and exit (no upload)",
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_youtube_config()
    
    # Verify mode
    if args.verify:
        log.info("Verifying YouTube configuration...")
        report = verify_youtube_configuration(config)
        
        print("\n" + "=" * 60)
        print("YouTube Configuration Status")
        print("=" * 60)
        for key, value in report.items():
            print(f"{key:20s}: {value}")
        print("=" * 60)
        
        if report.get("configured") and report.get("api_reachable"):
            log.info("✅ YouTube configuration is valid and API is reachable")
            return 0
        else:
            log.error("❌ YouTube configuration has issues")
            return 1
    
    # Validate inputs
    video_path = args.video
    if not video_path.exists():
        log.error("Video file not found: %s", video_path)
        return 1
    
    title = args.title
    description = args.description
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else []
    content_id = args.content_id or video_path.stem
    
    # Publish
    log.info("Publishing to YouTube...")
    log.info("  Video: %s", video_path)
    log.info("  Title: %s", title)
    log.info("  Description: %s", description[:50] + "..." if len(description) > 50 else description)
    log.info("  Tags: %s", ", ".join(tags) if tags else "(none)")
    log.info("  Content ID: %s", content_id)
    log.info("  Force: %s", args.force)
    
    ledger = PublishLedger(config.ledger_path)
    
    report = publish_to_youtube(
        video_path=video_path,
        title=title,
        description=description,
        content_id=content_id,
        tags=tags,
        config=config,
        ledger=ledger,
        force=args.force,
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("YouTube Shorts Publishing Report")
    print("=" * 60)
    print(f"Content ID   : {report.content_id}")
    print(f"Video        : {report.video_path.name}")
    print(f"Status       : {report.result.status if report.result else 'N/A'}")
    if report.result and report.result.video_id:
        print(f"Video ID     : {report.result.video_id}")
    if report.result and report.result.share_url:
        print(f"URL          : {report.result.share_url}")
    if report.result and report.result.detail:
        print(f"Detail       : {report.result.detail}")
    print("=" * 60)
    
    if report.ok:
        log.info("✅ YouTube publishing successful!")
        return 0
    else:
        log.error("❌ YouTube publishing failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
