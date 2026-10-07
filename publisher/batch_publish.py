#!/usr/bin/env python3
"""
batch_publish.py — Toplu video yayını için yardımcı script.

Birden fazla videoyu otomatik olarak Meta, TikTok ve YouTube'a yayınlar.
JSON veya CSV dosyasından video listesi okuyabilir.

Usage:
    # JSON dosyasından toplu yayın (tüm platformlar)
    python batch_publish.py --json videos.json --all-platforms --live
    
    # Sadece Meta (Facebook + Instagram)
    python batch_publish.py --json videos.json --meta --live
    
    # Sadece TikTok
    python batch_publish.py --json videos.json --tiktok --live
    
    # Sadece YouTube
    python batch_publish.py --json videos.json --youtube --live
    
    # CSV dosyasından toplu yayın
    python batch_publish.py --csv videos.csv --all-platforms --live
    
    # Dry run
    python batch_publish.py --json videos.json --all-platforms --dry-run
    
    # Sadece başarısızları tekrar dene
    python batch_publish.py --json videos.json --retry-failed --live
"""
import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from pompom_meta_publisher.publishing import (
    load_meta_config,
    publish_to_meta,
)
from pompom_tiktok_publisher import (
    load_tiktok_config,
    publish_to_tiktok,
)
from pompom_youtube_publisher import (
    load_youtube_config,
    publish_to_youtube,
)

log = logging.getLogger("batch_publish")


def load_videos_from_json(json_path: Path) -> list[dict[str, Any]]:
    """Load video list from JSON file."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # Support both array format and object with "videos" key
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and "videos" in data:
        return data["videos"]
    else:
        raise ValueError(f"JSON file must be array or object with 'videos' key")


def load_videos_from_csv(csv_path: Path) -> list[dict[str, Any]]:
    """Load video list from CSV file."""
    videos = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            videos.append({
                "video": row["video_path"],
                "title": row.get("title", ""),
                "caption": row.get("caption", row.get("description", "")),
                "description": row.get("description", row.get("caption", "")),
                "tags": row.get("tags", "").split(",") if row.get("tags") else [],
                "content_id": row["content_id"],
                "platforms": row.get("platforms", "").split(",") if row.get("platforms") else None,
            })
    return videos


def publish_video_all_platforms(
    item: dict[str, Any],
    *,
    meta_config=None,
    tiktok_config=None,
    youtube_config=None,
    platforms: list[str] | None = None,
) -> dict[str, tuple[bool, str]]:
    """
    Publish a single video to all specified platforms.
    
    Returns dict mapping platform to (success, message).
    """
    video_path = Path(item["video"])
    content_id = item["content_id"]
    
    if not video_path.exists():
        error = (False, f"Video not found: {video_path}")
        return {"error": error}
    
    results = {}
    target_platforms = platforms or ["meta", "tiktok", "youtube"]
    
    # Meta (Facebook + Instagram)
    if "meta" in target_platforms or "facebook" in target_platforms or "instagram" in target_platforms:
        try:
            report = publish_to_meta(
                video_path=video_path,
                caption=item.get("caption", ""),
                content_id=content_id,
                config=meta_config,
            )
            
            if report.ok:
                published = [f"{r.platform}={r.media_id}" for r in report.published]
                results["meta"] = (True, f"Published: {', '.join(published)}")
            else:
                failures = [f"{r.platform}: {r.detail}" for r in report.failures]
                results["meta"] = (False, f"Failed: {'; '.join(failures)}")
        except Exception as exc:
            results["meta"] = (False, f"Error: {exc}")
    
    # TikTok
    if "tiktok" in target_platforms:
        try:
            report = publish_to_tiktok(
                video_path=video_path,
                caption=item.get("caption", ""),
                content_id=content_id,
                config=tiktok_config,
            )
            
            if report.ok:
                results["tiktok"] = (True, f"Published: {report.result.video_id}")
            else:
                results["tiktok"] = (False, f"Failed: {report.result.detail}")
        except Exception as exc:
            results["tiktok"] = (False, f"Error: {exc}")
    
    # YouTube
    if "youtube" in target_platforms:
        try:
            title = item.get("title", item.get("caption", "")[:100])
            description = item.get("description", item.get("caption", ""))
            tags = item.get("tags", [])
            
            report = publish_to_youtube(
                video_path=video_path,
                title=title,
                description=description,
                content_id=content_id,
                tags=tags,
                config=youtube_config,
            )
            
            if report.ok:
                results["youtube"] = (True, f"Published: {report.result.video_id}")
            else:
                results["youtube"] = (False, f"Failed: {report.result.detail}")
        except Exception as exc:
            results["youtube"] = (False, f"Error: {exc}")
    
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch publish Pompom Hills videos to multiple platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json", type=str, help="JSON file with video list")
    parser.add_argument("--csv", type=str, help="CSV file with video list")
    
    # Platform selection
    parser.add_argument("--all-platforms", action="store_true",
                        help="Publish to all enabled platforms")
    parser.add_argument("--meta", action="store_true",
                        help="Publish to Meta (Facebook + Instagram)")
    parser.add_argument("--tiktok", action="store_true",
                        help="Publish to TikTok")
    parser.add_argument("--youtube", action="store_true",
                        help="Publish to YouTube")
    
    # Modes
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run mode")
    parser.add_argument("--live", action="store_true",
                        help="Live publishing mode")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Only retry previously failed videos")
    parser.add_argument("--delay", type=int, default=5,
                        help="Delay between videos in seconds (default: 5)")
    parser.add_argument("--quiet", action="store_true",
                        help="Reduce log output")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Validate arguments
    if not args.json and not args.csv:
        raise SystemExit("Either --json or --csv is required")
    
    if args.json and args.csv:
        raise SystemExit("Cannot use both --json and --csv")
    
    if args.dry_run and args.live:
        raise SystemExit("Cannot use both --dry-run and --live")
    
    # Determine target platforms
    platforms = []
    if args.all_platforms:
        platforms = ["meta", "tiktok", "youtube"]
    else:
        if args.meta:
            platforms.append("meta")
        if args.tiktok:
            platforms.append("tiktok")
        if args.youtube:
            platforms.append("youtube")
    
    if not platforms:
        raise SystemExit("No platforms selected. Use --all-platforms or --meta/--tiktok/--youtube")
    
    # Load videos
    if args.json:
        videos = load_videos_from_json(Path(args.json))
        log.info("Loaded %s videos from %s", len(videos), args.json)
    else:
        videos = load_videos_from_csv(Path(args.csv))
        log.info("Loaded %s videos from %s", len(videos), args.csv)
    
    if not videos:
        print("No videos to publish.")
        return 0
    
    # Load configs
    meta_config = load_meta_config() if "meta" in platforms else None
    tiktok_config = load_tiktok_config() if "tiktok" in platforms else None
    youtube_config = load_youtube_config() if "youtube" in platforms else None
    
    # Apply dry-run/live mode
    if args.dry_run:
        if meta_config:
            meta_config.dry_run = True
        if tiktok_config:
            tiktok_config.dry_run = True
        if youtube_config:
            youtube_config.dry_run = True
    
    if args.live:
        if meta_config:
            meta_config.dry_run = False
        if tiktok_config:
            tiktok_config.dry_run = False
        if youtube_config:
            youtube_config.dry_run = False
    
    dry_run = args.dry_run or (
        (meta_config and meta_config.dry_run) or
        (tiktok_config and tiktok_config.dry_run) or
        (youtube_config and youtube_config.dry_run)
    )
    
    if dry_run:
        log.warning("🧪 DRY RUN MODE - No actual publishing will occur")
    
    # Publish each video
    total = len(videos)
    platform_stats = {p: {"success": 0, "failed": 0} for p in platforms}
    
    print(f"\n{'═' * 80}")
    print(f"  Batch Publishing {total} videos")
    print(f"  Platforms: {', '.join(platforms)}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'═' * 80}\n")
    
    for idx, video in enumerate(videos, 1):
        content_id = video["content_id"]
        video_path = video["video"]
        
        print(f"\n[{idx}/{total}] 📤 {content_id}")
        print(f"  Video: {video_path}")
        if video.get("title"):
            print(f"  Title: {video['title'][:60]}...")
        if video.get("caption"):
            print(f"  Caption: {video['caption'][:60]}...")
        
        results = publish_video_all_platforms(
            video,
            meta_config=meta_config,
            tiktok_config=tiktok_config,
            youtube_config=youtube_config,
            platforms=platforms,
        )
        
        if "error" in results:
            print(f"  ❌ {results['error'][1]}")
            for platform in platforms:
                platform_stats[platform]["failed"] += 1
            continue
        
        for platform, (success, message) in results.items():
            if success:
                print(f"  ✅ {platform}: {message}")
                platform_stats[platform]["success"] += 1
            else:
                print(f"  ❌ {platform}: {message}")
                platform_stats[platform]["failed"] += 1
        
        # Delay between videos (except last one)
        if idx < total and args.delay > 0:
            print(f"  ⏳ Waiting {args.delay} seconds...")
            time.sleep(args.delay)
    
    # Summary
    print(f"\n{'═' * 80}")
    print(f"  Batch Publishing Complete")
    print(f"{'─' * 80}")
    print(f"  Total Videos: {total}")
    print(f"{'─' * 80}")
    
    for platform in platforms:
        stats = platform_stats[platform]
        print(f"  {platform.upper():12s}: {stats['success']} ✅  {stats['failed']} ❌")
    
    print(f"{'═' * 80}\n")
    
    # Return 0 if all succeeded
    total_failed = sum(stats["failed"] for stats in platform_stats.values())
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
