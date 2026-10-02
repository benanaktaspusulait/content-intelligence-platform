#!/usr/bin/env python3
"""
get_insights.py — Yayınlanmış içerik performans raporları.

Meta Graph API'den yayınlanmış videoların performance metrics'lerini çeker.

Usage:
    # Tek post insights
    python get_insights.py --post-id 123456789012345_98765 --platform facebook
    
    # Tek reel insights
    python get_insights.py --post-id 18012345678901234 --platform instagram
    
    # Content ID'den otomatik bul ve rapor al
    python get_insights.py --content-id lucas-treasure-001
    
    # Tüm yayınların raporu (son 30)
    python get_insights.py --all --limit 30
    
    # CSV export
    python get_insights.py --all --export insights.csv
    
    # Page/Account genel insights
    python get_insights.py --page-summary
    python get_insights.py --account-summary
"""
import argparse
import csv
import json
import logging
import sys
from pathlib import Path

from pompom_meta_publisher.analytics import (
    get_facebook_post_insights,
    get_instagram_reel_insights,
    get_page_insights,
    get_account_insights,
)
from pompom_meta_publisher.publishing import PublishLedger, load_meta_config
from pompom_meta_publisher.publishing.errors import PublishError

log = logging.getLogger("get_insights")


def print_facebook_insights(insights):
    """Facebook insights pretty print."""
    print(f"\n{'═' * 70}")
    print(f"  Facebook Post Insights")
    print(f"{'═' * 70}")
    print(f"  Post ID:        {insights.post_id}")
    print(f"  Permalink:      {insights.permalink}")
    print(f"  Created:        {insights.created_time}")
    print(f"{'─' * 70}")
    print(f"  Impressions:    {insights.impressions:,}")
    print(f"  Engagement:     {insights.engagement:,}")
    print(f"  Video Views:    {insights.video_views:,}")
    print(f"  Watch Time:     {insights.video_view_time / 1000:.1f}s")
    print(f"  Likes:          {insights.likes:,}")
    print(f"  Comments:       {insights.comments:,}")
    print(f"  Shares:         {insights.shares:,}")
    print(f"{'═' * 70}\n")


def print_instagram_insights(insights):
    """Instagram insights pretty print."""
    print(f"\n{'═' * 70}")
    print(f"  Instagram Reel Insights")
    print(f"{'═' * 70}")
    print(f"  Media ID:       {insights.media_id}")
    print(f"  Permalink:      {insights.permalink}")
    print(f"  Posted:         {insights.timestamp}")
    print(f"{'─' * 70}")
    print(f"  Reach:          {insights.reach:,}")
    print(f"  Impressions:    {insights.impressions:,}")
    print(f"  Plays:          {insights.plays:,}")
    print(f"  Engagement:     {insights.engagement:,}")
    print(f"  Likes:          {insights.likes:,}")
    print(f"  Comments:       {insights.comments:,}")
    print(f"  Shares:         {insights.shares:,}")
    print(f"  Saves:          {insights.saves:,}")
    print(f"{'═' * 70}\n")


def get_insights_for_content_id(content_id: str, config):
    """Content ID'den media ID'leri bulup insights çek."""
    ledger = PublishLedger(config.ledger_path)
    
    results = []
    
    # Facebook
    fb_record = ledger.already_published(content_id, "facebook")
    if fb_record and fb_record.media_id:
        try:
            insights = get_facebook_post_insights(fb_record.media_id, config=config)
            results.append(("facebook", insights))
            print_facebook_insights(insights)
        except PublishError as e:
            log.error("Facebook insights error: %s", e)
    
    # Instagram
    ig_record = ledger.already_published(content_id, "instagram")
    if ig_record and ig_record.media_id:
        try:
            insights = get_instagram_reel_insights(ig_record.media_id, config=config)
            results.append(("instagram", insights))
            print_instagram_insights(insights)
        except PublishError as e:
            log.error("Instagram insights error: %s", e)
    
    return results


def export_to_csv(insights_list: list, output_path: Path):
    """Export insights to CSV."""
    if not insights_list:
        print("No insights to export.")
        return
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'content_id', 'platform', 'media_id', 'impressions', 'reach',
            'engagement', 'likes', 'comments', 'shares', 'views_plays',
            'permalink', 'timestamp'
        ])
        
        # Data
        for content_id, platform, insights in insights_list:
            if platform == "facebook":
                row = [
                    content_id, platform, insights.post_id,
                    insights.impressions, 0, insights.engagement,
                    insights.likes, insights.comments, insights.shares,
                    insights.video_views, insights.permalink, insights.created_time
                ]
            else:  # instagram
                row = [
                    content_id, platform, insights.media_id,
                    insights.impressions, insights.reach, insights.engagement,
                    insights.likes, insights.comments, insights.shares,
                    insights.plays, insights.permalink, insights.timestamp
                ]
            writer.writerow(row)
    
    print(f"✅ Exported to: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Get performance insights for published content")
    parser.add_argument("--post-id", type=str,
                        help="Specific post/media ID")
    parser.add_argument("--platform", type=str, choices=["facebook", "instagram"],
                        help="Platform for post-id")
    parser.add_argument("--content-id", type=str,
                        help="Content ID to look up in ledger")
    parser.add_argument("--all", action="store_true",
                        help="Get insights for all published content")
    parser.add_argument("--limit", type=int, default=30,
                        help="Limit for --all (default: 30)")
    parser.add_argument("--export", type=str,
                        help="Export to CSV file")
    parser.add_argument("--page-summary", action="store_true",
                        help="Get Facebook Page summary")
    parser.add_argument("--account-summary", action="store_true",
                        help="Get Instagram Account summary")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="Reduce log output")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    
    config = load_meta_config()
    
    # Page summary
    if args.page_summary:
        print("\n📊 Facebook Page Insights (Last 7 days)\n")
        insights = get_page_insights(period="week", config=config)
        if args.json:
            print(json.dumps(insights, indent=2))
        else:
            for key, value in insights.items():
                print(f"  {key:<30} {value:,}")
        print()
        return 0
    
    # Account summary
    if args.account_summary:
        print("\n📊 Instagram Account Insights (Last 7 days)\n")
        insights = get_account_insights(period="week", config=config)
        if args.json:
            print(json.dumps(insights, indent=2))
        else:
            for key, value in insights.items():
                print(f"  {key:<30} {value:,}")
        print()
        return 0
    
    # Single post
    if args.post_id:
        if not args.platform:
            raise SystemExit("--platform required with --post-id")
        
        try:
            if args.platform == "facebook":
                insights = get_facebook_post_insights(args.post_id, config=config)
                if args.json:
                    print(json.dumps(insights.raw_data, indent=2))
                else:
                    print_facebook_insights(insights)
            else:
                insights = get_instagram_reel_insights(args.post_id, config=config)
                if args.json:
                    print(json.dumps(insights.raw_data, indent=2))
                else:
                    print_instagram_insights(insights)
        except PublishError as e:
            log.error("Failed to get insights: %s", e)
            return 1
        return 0
    
    # Content ID
    if args.content_id:
        results = get_insights_for_content_id(args.content_id, config)
        if not results:
            print(f"❌ No published content found for: {args.content_id}")
            return 1
        return 0
    
    # All published content
    if args.all:
        ledger = PublishLedger(config.ledger_path)
        records = ledger.history(limit=args.limit)
        
        if not records:
            print("No published content found.")
            return 0
        
        print(f"\n📊 Fetching insights for {len(records)} published items...\n")
        
        insights_list = []
        for record in records:
            if record.status != "SUCCESS":
                continue
            
            print(f"⏳ {record.content_id} ({record.platform})...")
            
            try:
                if record.platform == "facebook":
                    insights = get_facebook_post_insights(
                        record.media_id, config=config)
                    insights_list.append((record.content_id, "facebook", insights))
                else:
                    insights = get_instagram_reel_insights(
                        record.media_id, config=config)
                    insights_list.append((record.content_id, "instagram", insights))
            except PublishError as e:
                log.warning("Skipped %s: %s", record.content_id, e)
        
        # Export or print
        if args.export:
            export_to_csv(insights_list, Path(args.export))
        else:
            for content_id, platform, insights in insights_list:
                print(f"\n{'─' * 70}")
                print(f"Content ID: {content_id}")
                if platform == "facebook":
                    print_facebook_insights(insights)
                else:
                    print_instagram_insights(insights)
        
        return 0
    
    # No action specified
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
