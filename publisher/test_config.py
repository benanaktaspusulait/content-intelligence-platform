#!/usr/bin/env python3
"""
test_config.py — Konfigürasyonu test et ve raporla.

Meta API bağlantısını, token'ları ve storage backend'ini test eder.
"""
import json
import sys
from pathlib import Path

from pompom_meta_publisher.publishing import (
    load_meta_config,
    verify_configuration,
)
from pompom_meta_publisher.publishing.errors import PublishError


def print_section(title: str) -> None:
    print(f"\n{'═' * 80}")
    print(f"  {title}")
    print(f"{'═' * 80}\n")


def print_item(key: str, value: str, status: str = "") -> None:
    status_icon = {
        "ok": "✅",
        "warn": "⚠️",
        "error": "❌",
        "info": "ℹ️",
    }.get(status.lower(), "  ")
    print(f"  {status_icon} {key:<30} {value}")


def main() -> int:
    print_section("Pompom Meta Publisher - Configuration Test")
    
    # Load config
    try:
        config = load_meta_config()
        print_item("Configuration loaded", "Success", "ok")
    except PublishError as e:
        print_item("Configuration error", str(e), "error")
        return 1
    
    # Basic settings
    print_section("Basic Settings")
    print_item("API Version", config.api_version, "info")
    print_item("Dry Run Mode", str(config.dry_run), "warn" if config.dry_run else "info")
    print_item("Graph API Base", config.graph_base, "info")
    
    # Facebook settings
    print_section("Facebook Configuration")
    print_item("Enabled", str(config.enable_facebook), "ok" if config.enable_facebook else "info")
    
    if config.enable_facebook:
        usable, reason = config.facebook_ready()
        if usable:
            print_item("Status", "Ready to publish", "ok")
            print_item("Page ID", config.page_id, "info")
            if config.facebook_reel_title:
                print_item("Reel Title", config.facebook_reel_title, "info")
        else:
            print_item("Status", f"Not ready: {reason}", "error")
    
    # Instagram settings
    print_section("Instagram Configuration")
    print_item("Enabled", str(config.enable_instagram), "ok" if config.enable_instagram else "info")
    
    if config.enable_instagram:
        usable, reason = config.instagram_ready()
        if usable:
            print_item("Status", "Ready to publish", "ok")
            print_item("Account ID", config.instagram_account_id, "info")
            print_item("Share to Feed", str(config.instagram_share_to_feed), "info")
        else:
            print_item("Status", f"Not ready: {reason}", "error")
    
    # Storage settings
    print_section("Storage Configuration")
    try:
        from pompom_meta_publisher.publishing.storage import create_storage
        storage = create_storage()
        print_item("Backend", storage.name, "ok" if storage.can_host else "warn")
        print_item("Can Host URLs", str(storage.can_host), "ok" if storage.can_host else "warn")
        
        if not storage.can_host and config.enable_instagram:
            print_item("Warning", "Instagram requires hosted URLs", "warn")
    except PublishError as e:
        print_item("Storage error", str(e), "error")
    
    # API Verification
    print_section("Meta API Connection Test")
    try:
        report = verify_configuration(config)
        
        # Facebook API test
        if config.enable_facebook:
            fb = report.get("facebook", {})
            if fb.get("reachable"):
                print_item("Facebook API", f"Connected to {fb.get('page_name')}", "ok")
                print_item("Page ID", fb.get("page_id", ""), "info")
            else:
                error = fb.get("error", "Unknown error")
                print_item("Facebook API", f"Failed: {error}", "error")
        
        # Instagram API test
        if config.enable_instagram:
            ig = report.get("instagram", {})
            if ig.get("reachable"):
                print_item("Instagram API", f"Connected to @{ig.get('username')}", "ok")
                print_item("Account ID", ig.get("account_id", ""), "info")
                
                # Publishing limits
                limits = ig.get("publishing_limit", {})
                if limits:
                    for item in limits:
                        quota = item.get("config", {}).get("quota_total", "?")
                        usage = item.get("quota_usage", "?")
                        print_item("Publishing Quota", f"{usage}/{quota} used", "info")
            else:
                error = ig.get("error", "Unknown error")
                print_item("Instagram API", f"Failed: {error}", "error")
    
    except Exception as e:
        print_item("API test failed", str(e), "error")
        return 1
    
    # Summary
    print_section("Summary")
    
    ready_platforms = []
    if config.enable_facebook:
        usable, _ = config.facebook_ready()
        if usable:
            ready_platforms.append("Facebook")
    
    if config.enable_instagram:
        usable, _ = config.instagram_ready()
        if usable:
            ready_platforms.append("Instagram")
    
    if ready_platforms:
        print_item("Ready to publish to", ", ".join(ready_platforms), "ok")
    else:
        print_item("Status", "No platforms ready", "error")
        return 1
    
    if config.dry_run:
        print_item("Mode", "DRY RUN - No actual publishing", "warn")
    else:
        print_item("Mode", "LIVE - Real publishing enabled", "ok")
    
    print_item("Ledger path", str(config.ledger_path), "info")
    
    # Full JSON report
    print_section("Full Configuration Report (JSON)")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    print(f"\n{'═' * 80}\n")
    print("✅ Configuration test complete!\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
