#!/usr/bin/env python3
"""
publish_to_tiktok.py — TikTok'a video yayınla.

TikTok Content Posting API kullanarak video yayınlar.

Usage:
    # Configuration check
    python publish_to_tiktok.py --check
    
    # Dry run
    python publish_to_tiktok.py \
        --video output/reel.mp4 \
        --caption "Amazing content! #PompomHills" \
        --content-id pompom-001 \
        --dry-run
    
    # Live publish
    python publish_to_tiktok.py \
        --video output/reel.mp4 \
        --caption "Amazing content! #PompomHills #KidsLearning" \
        --content-id pompom-001 \
        --live
    
    # Caption from file
    python publish_to_tiktok.py \
        --video output/reel.mp4 \
        --caption-file metadata/tiktok-caption.txt \
        --content-id pompom-001 \
        --live
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from pompom_tiktok_publisher import (
    load_tiktok_config,
    publish_to_tiktok,
    verify_tiktok_configuration,
)
from pompom_publisher_common import PublishError, PublishLedger, read_caption

log = logging.getLogger("publish_to_tiktok")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Publish Pompom Hills videos to TikTok")
    parser.add_argument("--video", type=str,
                        help="Path of the finished video")
    parser.add_argument("--caption", type=str,
                        help="Caption text")
    parser.add_argument("--caption-file", type=str,
                        help="Caption source file (.txt or .md)")
    parser.add_argument("--caption-section", type=str, default="TikTok Caption",
                        help="Markdown section for caption")
    parser.add_argument("--content-id", type=str,
                        help="Unique content identifier")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run mode")
    parser.add_argument("--live", action="store_true",
                        help="Live publishing mode")
    parser.add_argument("--force", action="store_true",
                        help="Force re-publish")
    parser.add_argument("--check", action="store_true",
                        help="Verify configuration")
    parser.add_argument("--history", action="store_true",
                        help="Show publication history")
    parser.add_argument("--quiet", action="store_true",
                        help="Reduce logging")
    return parser.parse_args()


def print_history(ledger_path: Path) -> None:
    """Print TikTok publication history."""
    records = PublishLedger(ledger_path).history(limit=100)
    tiktok_records = [r for r in records if r.platform == "tiktok"]
    
    if not tiktok_records:
        print("\nNo TikTok publications yet.\n")
        return
    
    print(f"\n{'─' * 96}")
    print(f"  {'content_id':<25} {'status':<18} {'video_id':<22} published_at")
    print(f"{'─' * 96}")
    for record in tiktok_records:
        print(f"  {record.content_id:<25} {record.status:<18} "
              f"{str(record.media_id or '-'):<22} {record.published_at}")
    print(f"{'─' * 96}\n")


def main() -> int:
    args = parse_args()
    
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    
    if args.dry_run and args.live:
        raise SystemExit("Cannot use both --dry-run and --live")
    
    config = load_tiktok_config()
    
    if args.dry_run:
        config.dry_run = True
    if args.live:
        config.dry_run = False
    
    # History
    if args.history:
        print_history(config.ledger_path)
        return 0
    
    # Configuration check
    if args.check:
        report = verify_tiktok_configuration(config)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    
    # Publishing
    if not args.video:
        raise SystemExit("--video is required (use --help)")
    
    video_path = Path(args.video)
    if not video_path.exists():
        raise SystemExit(f"Video not found: {video_path}")
    
    # Caption
    caption = ""
    if args.caption:
        caption = args.caption
    elif args.caption_file:
        caption = read_caption(args.caption_file, args.caption_section)
    
    if not caption.strip():
        raise SystemExit("Caption required: use --caption or --caption-file")
    
    # Content ID
    content_id = args.content_id or video_path.stem
    log.info("Content ID: %s", content_id)
    
    # Warnings
    if config.dry_run:
        log.warning("🧪 DRY RUN - No actual upload will occur")
    
    if not config.enable_tiktok:
        raise SystemExit("TikTok not enabled. Set TIKTOK_ENABLE=true in .env")
    
    # Publish
    try:
        report = publish_to_tiktok(
            video_path=video_path,
            caption=caption,
            content_id=content_id,
            config=config,
            force=args.force,
        )
    except PublishError as exc:
        log.error("Publishing failed: %s", exc)
        return 2
    
    # Result
    print(f"\n{'─' * 70}")
    print(f"  Content    : {report.content_id}")
    print(f"  Video      : {report.video_path}")
    
    if report.result:
        result = report.result
        line = f"  TikTok     : {result.status}"
        if result.video_id:
            line += f"  (id={result.video_id})"
        print(line)
        
        if result.share_url:
            print(f"              {result.share_url}")
        if result.detail and result.status not in ("SUCCESS",):
            print(f"              {result.detail}")
    
    print(f"{'─' * 70}\n")
    
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
