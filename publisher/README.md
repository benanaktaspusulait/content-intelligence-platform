# Pompom Multi-Platform Publisher

Standalone social media publishing module for Pompom Hills content. Supports Meta (Facebook + Instagram), TikTok, and YouTube Shorts.

## Features

### Meta (Facebook + Instagram)
- **Facebook Page Reels** - Three-phase video API upload and publish
- **Instagram Professional Account Reels** - Container-based publishing
- **Pluggable storage** - Support for local hosting, S3, R2, B2, or pre-hosted URLs

### TikTok
- **Content Posting API** - Full API implementation with chunked upload
- **Privacy controls** - Public, friends-only, or private
- **Shorts optimization** - Auto-formatted for TikTok

### YouTube
- **YouTube Shorts** - Resumable upload with YouTube Data API v3
- **Auto-tagging** - Automatic #Shorts hashtag
- **OAuth2 support** - Token refresh handling
- **COPPA compliance** - Made for kids setting

### Common Features
- **Content-agnostic** - Works with any vertical video + caption + content_id
- **Duplicate protection** - SQLite ledger prevents re-publishing
- **Modular design** - Each platform works independently
- **Dry-run mode** - Test without actually publishing
- **Token scrubbing** - Secrets never appear in logs
- **Retry with backoff** - Handles transient API failures
- **Batch publishing** - Upload multiple videos at once
- **Analytics** - Meta insights and metrics (coming soon for TikTok/YouTube)

## Installation

```bash
cd pompom-meta-publisher
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

## Quick Start

### Meta (Facebook + Instagram)

```bash
# Check configuration
python publish_pompom_reel.py --check

# Dry run
python publish_pompom_reel.py \
    --video video.mp4 \
    --caption "Watch Kiko discover something amazing! 🌟" \
    --content-id kiko-001 \
    --dry-run

# Live publish
python publish_pompom_reel.py --video video.mp4 --caption "..." --content-id kiko-001 --live
```

### TikTok

```bash
# Check configuration
python publish_to_tiktok.py --verify

# Dry run
python publish_to_tiktok.py video.mp4 "Watch Kiko! 🌟" --dry-run

# Live publish
python publish_to_tiktok.py video.mp4 "Watch Kiko! 🌟" --content-id kiko-001
```

### YouTube Shorts

```bash
# Check configuration
python publish_to_youtube.py --verify

# Dry run
YOUTUBE_DRY_RUN=true python publish_to_youtube.py video.mp4 "Kiko's Discovery"

# Live publish
python publish_to_youtube.py video.mp4 "Kiko's Discovery" \
    --description "Watch Kiko discover something amazing! #Shorts" \
    --tags "kids,animation,shorts" \
    --content-id kiko-001
```

### Batch Publishing (All Platforms)

```bash
# Publish to all platforms
python batch_publish.py --json videos.json --all-platforms --live

# Publish to specific platforms
python batch_publish.py --json videos.json --meta --tiktok --live

# Check publication history
python publish_pompom_reel.py --history
```

## Configuration

All configuration is via environment variables or `.env` file:

### Meta (Facebook + Instagram)

**Required:**
```bash
META_PAGE_ID=your-facebook-page-id
META_INSTAGRAM_ACCOUNT_ID=your-instagram-business-account-id
META_PAGE_ACCESS_TOKEN=your-long-lived-page-access-token
META_ENABLE_FACEBOOK=true
META_ENABLE_INSTAGRAM=true
META_DRY_RUN=false
```

**Storage Backend (for Instagram):**
```bash
META_STORAGE_BACKEND=s3  # or: public_dir, template, none
META_S3_BUCKET=pompom-reels
META_S3_ENDPOINT_URL=https://your-endpoint.com
META_S3_PUBLIC_BASE_URL=https://cdn.pompomhills.com
META_S3_ACCESS_KEY_ID=your-key
META_S3_SECRET_ACCESS_KEY=your-secret
```

### TikTok

**Required:**
```bash
TIKTOK_ENABLE=true
TIKTOK_ACCESS_TOKEN=your-tiktok-access-token
TIKTOK_DRY_RUN=false
```

**Optional:**
```bash
TIKTOK_CLIENT_KEY=your-client-key
TIKTOK_CLIENT_SECRET=your-client-secret
TIKTOK_API_BASE=https://open.tiktokapis.com
```

### YouTube

**Required:**
```bash
YOUTUBE_ENABLE=true
YOUTUBE_CLIENT_ID=your-google-oauth-client-id
YOUTUBE_CLIENT_SECRET=your-google-oauth-client-secret
YOUTUBE_REFRESH_TOKEN=your-oauth-refresh-token
YOUTUBE_DRY_RUN=false
```

**Optional:**
```bash
YOUTUBE_PRIVACY=public  # or: unlisted, private
YOUTUBE_MADE_FOR_KIDS=true  # COPPA compliance
```

See `.env.example` for complete configuration options.

## Programmatic Usage

```python
from pompom_meta_publisher.publishing import publish_to_meta

report = publish_to_meta(
    video_path="path/to/final-vertical.mp4",
    caption="Watch Kiko discover something amazing! 🌟",
    content_id="kiko-discovery-001",
)

if report.ok:
    print(f"Published successfully!")
    for result in report.published:
        print(f"  {result.platform}: {result.permalink}")
else:
    print("Publishing failed:")
    for failure in report.failures:
        print(f"  {failure.platform}: {failure.detail}")
```

## Token Management

### Getting a Long-Lived Page Access Token

1. Get a User Access Token from [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Extend it to a long-lived token:
   ```bash
   curl -G "https://graph.facebook.com/v21.0/oauth/access_token" \
     -d "grant_type=fb_exchange_token" \
     -d "client_id=YOUR_APP_ID" \
     -d "client_secret=YOUR_APP_SECRET" \
     -d "fb_exchange_token=SHORT_LIVED_USER_TOKEN"
   ```
3. Get Page Access Token:
   ```bash
   curl -G "https://graph.facebook.com/v21.0/PAGE_ID" \
     -d "fields=access_token" \
     -d "access_token=LONG_LIVED_USER_TOKEN"
   ```

### Required Permissions

- `pages_manage_posts` - Publish to Facebook Page
- `pages_read_engagement` - Read Page insights
- `instagram_basic` - Access Instagram account
- `instagram_content_publish` - Publish Instagram Reels

## Troubleshooting

### Instagram skipped: "no public URL"
- Configure `META_STORAGE_BACKEND` (Instagram requires HTTPS URL)

### Facebook works but Instagram fails
- Check `META_INSTAGRAM_ACCOUNT_ID` is correct
- Verify Instagram account is a Professional/Business account
- Ensure Instagram account is linked to the Facebook Page

### "Token is invalid or expired"
- Regenerate long-lived Page Access Token
- Check permissions in Meta App dashboard

### Video processing timeout
- Increase `META_POLL_TIMEOUT` (default: 300 seconds)
- Check video codec (H.264 recommended)
- Reduce video file size if very large

## Project Structure

```
pompom-meta-publisher/
├── README.md                          This file
├── setup.py                           Package installation
├── .env.example                       Environment template
├── .gitignore
├── publish_pompom_reel.py             Meta CLI tool
├── publish_to_tiktok.py               TikTok CLI tool
├── publish_to_youtube.py              YouTube CLI tool
├── batch_publish.py                   Multi-platform orchestration
├── pompom_meta_publisher/             Facebook + Instagram only
│   ├── __init__.py
│   ├── py.typed
│   ├── common/                        Compatibility re-exports
│   └── publishing/                    Meta publishing implementation
├── pompom_tiktok_publisher/           TikTok implementation
├── pompom_youtube_publisher/          YouTube implementation
├── pompom_publisher_common/           Neutral shared utilities
│   ├── env.py                         Environment loading
│   ├── retry.py                       Exponential backoff
│   ├── ledger.py                      Publication tracking
│   ├── captions.py                    Caption helpers
│   ├── errors.py                      Base publishing error
│   └── secrets.py                     Secret scrubbing
└── data/
    ├── publish_log.db                 Meta SQLite ledger
    ├── tiktok_publish_log.db          TikTok SQLite ledger
    └── youtube_publish_log.db         YouTube SQLite ledger
```

## License

Proprietary - Pompom Hills / Yuvarlak Dunya Project
