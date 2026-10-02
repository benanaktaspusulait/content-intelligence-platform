#!/usr/bin/env python3
"""
publish_pompom_reel.py — Publish a Pompom Hills Reel to Facebook and Instagram.

Publishing is a separate, explicit step because production QA requires a
human review before anything reaches an audience.

Usage:
    # configuration self check, no publishing
    python publish_pompom_reel.py --check

    # dry run: prepare and log endpoints and payloads only
    python publish_pompom_reel.py \
        --video output/final-reel.mp4 \
        --caption "Watch Kiko discover something amazing! 🌟" \
        --content-id kiko-discovery-001 \
        --dry-run

    # publish to both Facebook and Instagram
    python publish_pompom_reel.py \
        --video output/final-reel.mp4 \
        --caption "Watch Kiko discover something amazing! 🌟" \
        --content-id kiko-discovery-001 \
        --live

    # publish to Facebook only
    python publish_pompom_reel.py \
        --video output/final-reel.mp4 \
        --caption "Watch Kiko discover something amazing! 🌟" \
        --content-id kiko-discovery-001 \
        --platform facebook \
        --live

    # read caption from a file
    python publish_pompom_reel.py \
        --video output/final-reel.mp4 \
        --caption-file metadata/caption.txt \
        --content-id kiko-discovery-001 \
        --live

    # read caption from a markdown section
    python publish_pompom_reel.py \
        --video output/final-reel.mp4 \
        --caption-file metadata/social.md \
        --caption-section "Instagram Caption" \
        --content-id kiko-discovery-001 \
        --live

    # force re-publish even if already published
    python publish_pompom_reel.py \
        --video output/final-reel.mp4 \
        --caption "Updated caption" \
        --content-id kiko-discovery-001 \
        --force \
        --live

    # what has already been published
    python publish_pompom_reel.py --history
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from pompom_meta_publisher.publishing import (
    PublishLedger,
    load_meta_config,
    publish_to_meta,
    read_caption,
    verify_configuration,
)
from pompom_meta_publisher.publishing.errors import PublishError

log = logging.getLogger("publish_pompom_reel")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Publish a Pompom Hills Reel to Facebook and Instagram")
    parser.add_argument("--video", type=str,
                        help="Path of the finished video master")
    parser.add_argument("--caption", type=str,
                        help="Caption text passed directly")
    parser.add_argument("--caption-file", type=str,
                        help="Caption source: a .md file section or a .txt file")
    parser.add_argument("--caption-section", type=str, default="Instagram Caption",
                        help="Markdown heading to read the caption from")
    parser.add_argument("--content-id", type=str,
                        help="Stable id used for duplicate protection (e.g. kiko-discovery-001)")
    parser.add_argument("--video-url", type=str,
                        help="Skip the storage step and use this public HTTPS URL")
    parser.add_argument("--platform", action="append",
                        choices=("facebook", "instagram"),
                        help="Restrict to one platform; repeatable")
    parser.add_argument("--dry-run", action="store_true",
                        help="Force dry run regardless of META_DRY_RUN")
    parser.add_argument("--live", action="store_true",
                        help="Force a real publish, overriding META_DRY_RUN")
    parser.add_argument("--force", action="store_true",
                        help="Publish again even if the ledger holds a SUCCESS row")
    parser.add_argument("--check", action="store_true",
                        help="Validate configuration and exit")
    parser.add_argument("--history", action="store_true",
                        help="Print the publication ledger and exit")
    parser.add_argument("--quiet", action="store_true", help="Reduce log output")
    return parser.parse_args()


def print_history(ledger_path: Path) -> None:
    records = PublishLedger(ledger_path).history(limit=100)
    if not records:
        print("\nNo publication recorded yet.\n")
        return
    print(f"\n{'─' * 96}")
    print(f"  {'content_id':<25} {'platform':<10} {'status':<18} "
          f"{'media_id':<22} published_at")
    print(f"{'─' * 96}")
    for record in records:
        print(f"  {record.content_id:<25} {record.platform:<10} "
              f"{record.status:<18} {str(record.media_id or '-'):<22} "
              f"{record.published_at}")
    print(f"{'─' * 96}\n")


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.dry_run and args.live:
        raise SystemExit("--dry-run and --live cannot be combined")

    config = load_meta_config()
    if args.dry_run:
        config.dry_run = True
    if args.live:
        config.dry_run = False

    if args.history:
        print_history(config.ledger_path)
        return 0

    if args.check:
        print(json.dumps(verify_configuration(config), indent=2, ensure_ascii=False))
        return 0

    # ── Resolve target ────────────────────────────────────────────────────
    if not args.video:
        raise SystemExit("--video is required (use --help for usage)")
    
    video_path = Path(args.video)
    if not video_path.exists():
        raise SystemExit(f"Video not found: {video_path}")

    caption = ""
    if args.caption:
        caption = args.caption
    elif args.caption_file:
        caption = read_caption(args.caption_file, args.caption_section)
    
    if not caption.strip():
        raise SystemExit(
            "Caption is required. Pass --caption or --caption-file.")

    content_id = args.content_id
    if not content_id:
        # Auto-generate from video filename if not provided
        content_id = video_path.stem
        log.info("Auto-generated content_id: %s", content_id)

    if config.dry_run:
        log.warning("Dry run — no request will be sent to Meta.")
    if not config.any_target_enabled:
        raise SystemExit(
            "No Meta target is enabled. Set META_ENABLE_FACEBOOK or "
            "META_ENABLE_INSTAGRAM with the matching id and token.")

    try:
        report = publish_to_meta(
            video_path=video_path,
            caption=caption,
            content_id=content_id,
            config=config,
            video_url=args.video_url,
            platforms=args.platform,
            force=args.force,
        )
    except PublishError as exc:
        log.error("Publishing could not start: %s", exc)
        return 2

    print(f"\n{'─' * 70}")
    print(f"  Content    : {report.content_id}")
    print(f"  Video      : {report.video_path}")
    if report.video_url:
        print(f"  Hosted URL : {report.video_url}")
    for result in report.results.values():
        line = f"  {result.platform:<10}: {result.status}"
        if result.media_id:
            line += f"  (id={result.media_id})"
        print(line)
        if result.permalink:
            print(f"              {result.permalink}")
        if result.detail and result.status not in ("SUCCESS",):
            print(f"              {result.detail}")
    print(f"{'─' * 70}\n")

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
