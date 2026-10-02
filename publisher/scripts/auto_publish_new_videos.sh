#!/bin/bash
#
# auto_publish_new_videos.sh — Yeni video klasörlerini otomatik tespit edip yayınla
#
# Bu script belirli bir klasörü tarar, final.mp4 dosyası olan ve henüz
# yayınlanmamış videoları bulur ve otomatik olarak yayınlar.
#
# Usage:
#   ./scripts/auto_publish_new_videos.sh --search-dir ../Can\ You\ Find\ It? --live
#   ./scripts/auto_publish_new_videos.sh --search-dir ../Daily\ Routines* --dry-run

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
SEARCH_DIR=""
DRY_RUN=false
LIVE=false
VIDEO_FILENAME="final.mp4"
CAPTION_FILE="metadata/caption.txt"
DELAY=10

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --search-dir)
            SEARCH_DIR="$2"
            shift 2
            ;;
        --video-filename)
            VIDEO_FILENAME="$2"
            shift 2
            ;;
        --caption-file)
            CAPTION_FILE="$2"
            shift 2
            ;;
        --delay)
            DELAY="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --live)
            LIVE=true
            shift
            ;;
        --help)
            echo "Usage: $0 --search-dir <directory> [options]"
            echo ""
            echo "Options:"
            echo "  --search-dir <dir>        Directory to search for videos"
            echo "  --video-filename <name>   Video filename to look for (default: final.mp4)"
            echo "  --caption-file <path>     Caption file path relative to video dir"
            echo "  --delay <seconds>         Delay between videos (default: 10)"
            echo "  --dry-run                 Test mode"
            echo "  --live                    Real publishing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate
if [ -z "$SEARCH_DIR" ]; then
    echo "Error: --search-dir is required"
    exit 1
fi

if [ "$DRY_RUN" = true ] && [ "$LIVE" = true ]; then
    echo "Error: Cannot use both --dry-run and --live"
    exit 1
fi

MODE_FLAG=""
if [ "$DRY_RUN" = true ]; then
    MODE_FLAG="--dry-run"
elif [ "$LIVE" = true ]; then
    MODE_FLAG="--live"
fi

cd "$PROJECT_ROOT"

echo "═══════════════════════════════════════════════════════════"
echo "  Pompom Auto Publisher"
echo "═══════════════════════════════════════════════════════════"
echo "  Search directory: $SEARCH_DIR"
echo "  Video filename:   $VIDEO_FILENAME"
echo "  Mode:             $([ "$LIVE" = true ] && echo "LIVE" || echo "DRY RUN")"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Find all videos
VIDEO_COUNT=0
PUBLISHED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0

for video_path in $(find "$SEARCH_DIR" -name "$VIDEO_FILENAME" -type f); do
    VIDEO_COUNT=$((VIDEO_COUNT + 1))
    
    # Extract directory name as content ID
    video_dir=$(dirname "$video_path")
    dir_name=$(basename "$video_dir")
    content_id=$(echo "$dir_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g')
    
    echo "─────────────────────────────────────────────────────────"
    echo "[$VIDEO_COUNT] 📹 Found: $dir_name"
    echo "    Video: $video_path"
    echo "    Content ID: $content_id"
    
    # Check if already published
    already_published=$(python3 publish_pompom_reel.py --history 2>/dev/null | grep -c "$content_id" || echo "0")
    
    if [ "$already_published" != "0" ]; then
        echo "    ⏭️  Already published, skipping"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi
    
    # Look for caption file
    caption_path="$video_dir/$CAPTION_FILE"
    caption_arg=""
    
    if [ -f "$caption_path" ]; then
        echo "    📝 Caption file: $caption_path"
        caption_arg="--caption-file $caption_path"
    else
        # Generate default caption
        echo "    📝 Using default caption"
        caption_arg="--caption \"New video from Pompom Hills! 🌟 #PompomHills\""
    fi
    
    # Publish
    echo "    📤 Publishing..."
    
    if python3 publish_pompom_reel.py \
        --video "$video_path" \
        $caption_arg \
        --content-id "$content_id" \
        $MODE_FLAG; then
        echo "    ✅ Published successfully!"
        PUBLISHED_COUNT=$((PUBLISHED_COUNT + 1))
    else
        echo "    ❌ Publishing failed"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
    
    # Delay before next video
    if [ "$DELAY" -gt 0 ]; then
        echo "    ⏳ Waiting $DELAY seconds..."
        sleep "$DELAY"
    fi
done

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Auto Publishing Complete"
echo "═══════════════════════════════════════════════════════════"
echo "  Total found:      $VIDEO_COUNT"
echo "  Published:        $PUBLISHED_COUNT ✅"
echo "  Skipped:          $SKIPPED_COUNT ⏭️"
echo "  Failed:           $FAILED_COUNT ❌"
echo "═══════════════════════════════════════════════════════════"
echo ""

exit $FAILED_COUNT
