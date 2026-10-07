# Platform Integration Guide

This document explains how each social media platform is integrated.

## Package Boundaries

Each platform has its own top-level package. `pompom_meta_publisher` contains only Facebook/Instagram code, `pompom_tiktok_publisher` contains only TikTok code, and `pompom_youtube_publisher` contains only YouTube code. Neutral environment, retry, caption, ledger, error, and secret helpers live in `pompom_publisher_common`. `batch_publish.py` is the intentional orchestration boundary when multiple platforms are selected.

## 📊 Platform Comparison

| Feature | Meta (FB+IG) | TikTok | YouTube |
|---------|-------------|---------|----------|
| **API Maturity** | ✅ Stable | ✅ Stable | ✅ Stable |
| **Upload Method** | 3-phase + URL | Chunked | Resumable |
| **Public URL Required** | ✅ IG only | ❌ No | ❌ No |
| **Max File Size** | ~1GB | 287MB | 512MB |
| **Max Duration** | 90s | 60s (Shorts) | 60s (Shorts) |
| **OAuth Required** | ❌ No | ❌ No | ✅ Yes |
| **Duplicate Detection** | ✅ Ledger | ✅ Ledger | ✅ Ledger |
| **Analytics** | ✅ Included | 🚧 Coming | 🚧 Coming |

---

## 🔵 Meta (Facebook + Instagram)

### Overview
- **Facebook:** Page Reels API with 3-phase upload (init → upload → publish)
- **Instagram:** Professional Account Reels with container-based publishing
- **API:** Meta Graph API v21.0+

### Requirements
- Facebook Page ID
- Instagram Business/Professional Account ID
- Long-lived Page Access Token
- Public HTTPS URL (for Instagram only)

### Storage Options
Instagram requires a publicly accessible video URL:

1. **S3/R2/B2** (Recommended)
   - Auto-upload to cloud storage
   - Generate public URL
   - Auto-cleanup after publish

2. **Public Directory**
   - Copy to web-accessible directory
   - Use local server URL

3. **URL Template**
   - Assume video is already hosted
   - Use filename-based URL template

4. **None** (Facebook only)
   - Direct upload to Facebook
   - Instagram will be skipped

### API Flow

**Facebook:**
```
1. POST /video_reels (init)
   → Returns upload_url + video_id

2. POST upload_url (upload chunks)
   → Upload video data

3. POST /{video_id} (publish)
   → Set description, publish status
```

**Instagram:**
```
1. POST /{ig_account}/media (create container)
   → Provide public video_url, caption
   → Returns container_id

2. Poll GET /{container_id}?fields=status_code
   → Wait for FINISHED

3. POST /{ig_account}/media_publish
   → Publish container
```

### Token Setup
```bash
# 1. Get User Token from Graph API Explorer
# 2. Exchange for long-lived token
curl -G "https://graph.facebook.com/v21.0/oauth/access_token" \
  -d "grant_type=fb_exchange_token" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET" \
  -d "fb_exchange_token=SHORT_LIVED_USER_TOKEN"

# 3. Get Page Access Token
curl -G "https://graph.facebook.com/v21.0/PAGE_ID" \
  -d "fields=access_token" \
  -d "access_token=LONG_LIVED_USER_TOKEN"
```

### Files
- `pompom_meta_publisher/publishing/meta_api.py` - Core API
- `pompom_meta_publisher/publishing/storage.py` - Storage backends
- `publish_pompom_reel.py` - CLI tool

---

## 🎵 TikTok

### Overview
- **API:** TikTok Content Posting API v2
- **Method:** Chunked upload (10MB chunks)
- **Privacy:** Configurable (public/private/friends)

### Requirements
- TikTok for Developers App
- Client Key + Client Secret
- User Access Token (OAuth)

### API Flow
```
1. POST /v2/post/publish/video/init/
   → Provide video metadata, chunk info
   → Returns publish_id + upload_url

2. PUT upload_url (chunked upload)
   → Upload video in 10MB chunks
   → Use Content-Range headers

3. POST /v2/post/publish/status/fetch/
   → Poll for processing status
   → Wait for PUBLISH_COMPLETE
   → Returns share_url
```

### Token Setup
1. Create app at https://developers.tiktok.com/
2. Implement OAuth flow or use Login Kit
3. Get user access token with `video.upload` scope

### Limitations
- Max 287MB file size
- Max 10 minutes duration (Shorts: 60s recommended)
- Max 2200 chars caption
- Processing can take 1-5 minutes

### Files
- `pompom_tiktok_publisher/tiktok_publisher.py` - Core API
- `publish_to_tiktok.py` - CLI tool

---

## 📺 YouTube

### Overview
- **API:** YouTube Data API v3
- **Method:** Resumable upload protocol
- **Format:** Auto-tagged as #Shorts

### Requirements
- Google Cloud Project with YouTube Data API enabled
- OAuth 2.0 Client ID + Secret
- Refresh Token (from OAuth flow)

### API Flow
```
1. POST /upload/youtube/v3/videos?uploadType=resumable
   → Provide metadata (title, description, privacy)
   → Returns Location header (upload_url)

2. PUT upload_url (chunked upload)
   → Upload video in chunks
   → Use Content-Range headers
   → Last chunk returns video info

3. Video is live immediately
   → Returns video_id
   → Share URL: https://youtube.com/shorts/{video_id}
```

### OAuth Setup
```python
# 1. Install google-auth-oauthlib
pip install google-auth-oauthlib

# 2. Run OAuth flow
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secrets.json',
    scopes=['https://www.googleapis.com/auth/youtube.upload']
)
credentials = flow.run_local_server()

# 3. Save refresh_token to .env
print(credentials.refresh_token)
```

Or use this quick script:
```bash
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secrets.json',
    scopes=['https://www.googleapis.com/auth/youtube.upload']
)
creds = flow.run_local_server()
print('YOUTUBE_REFRESH_TOKEN=' + creds.refresh_token)
"
```

### Shorts Requirements
- Duration: ≤60 seconds
- Aspect ratio: 9:16 (vertical)
- Resolution: min 1080x1920
- Must include #Shorts in title or description (auto-added)

### COPPA Compliance
```bash
# If content is for children
YOUTUBE_MADE_FOR_KIDS=true
```

### Files
- `pompom_youtube_publisher/youtube_publisher.py` - Core API
- `publish_to_youtube.py` - CLI tool

---

## 🔄 Batch Publishing

### Overview
Publish multiple videos to multiple platforms in one command.

### Usage
```bash
# All platforms
python batch_publish.py --json videos.json --all-platforms --live

# Specific platforms
python batch_publish.py --json videos.json --meta --tiktok --live
python batch_publish.py --csv videos.csv --youtube --live

# Dry run
python batch_publish.py --json videos.json --all-platforms --dry-run
```

### Input Format

**JSON:**
```json
{
  "videos": [
    {
      "video": "path/to/video.mp4",
      "title": "Video Title",
      "caption": "Caption text",
      "description": "Longer description",
      "tags": ["kids", "animation"],
      "content_id": "unique-id-001"
    }
  ]
}
```

**CSV:**
```csv
video_path,title,caption,tags,content_id
path/to/video1.mp4,Title 1,Caption 1,"kids,animation",video-001
path/to/video2.mp4,Title 2,Caption 2,"shorts,fun",video-002
```

### Files
- `batch_publish.py` - Multi-platform batch tool

---

## 📊 Analytics

### Meta Analytics
```bash
# Get insights
python get_insights.py --period last_7d

# Export to CSV
python get_insights.py --period last_30d --output insights.csv

# Specific content
python get_insights.py --content-id kiko-001
```

### TikTok Analytics
🚧 Coming soon - TikTok Analytics API integration

### YouTube Analytics
🚧 Coming soon - YouTube Analytics API integration

### Files
- `pompom_meta_publisher/analytics/meta_insights.py` - Meta analytics
- `get_insights.py` - Analytics CLI

---

## 🗄️ Duplicate Protection

Each platform uses the neutral SQLite ledger implementation with its own default database (`data/publish_log.db` for Meta, `data/tiktok_publish_log.db` for TikTok, and `data/youtube_publish_log.db` for YouTube):

```python
from pompom_publisher_common import PublishLedger

ledger = PublishLedger("data/youtube_publish_log.db")

# Check if already published
existing = ledger.already_published("content-id-001", "youtube")
if existing:
    print(f"Already published: {existing.permalink}")

# Record new publish
ledger.record(
    content_id="content-id-002",
    platform="tiktok",
    status="SUCCESS",
    media_id="7123456789",
    permalink="https://tiktok.com/@user/video/7123456789"
)
```

### Database Schema
```sql
CREATE TABLE publish_log (
    id INTEGER PRIMARY KEY,
    content_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    media_id TEXT,
    permalink TEXT,
    detail TEXT,
    published_at TEXT NOT NULL,
    UNIQUE(content_id, platform)
);
```

---

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Use environment variables in production** - Don't hardcode tokens
3. **Rotate tokens regularly** - Especially long-lived tokens
4. **Use dry-run first** - Test before going live
5. **Monitor ledger** - Check for failed uploads
6. **Enable cleanup** - Auto-delete hosted files after publish

---

## 🚀 Deployment

### Local Development
```bash
cp .env.example .env
# Edit .env with your tokens
python publish_to_youtube.py video.mp4 "Title"
```

### Production (CI/CD)
```bash
# Set environment variables in CI
export YOUTUBE_ENABLE=true
export YOUTUBE_REFRESH_TOKEN=$SECRET_YOUTUBE_TOKEN
export YOUTUBE_DRY_RUN=false

# Run batch publish
python batch_publish.py --json videos.json --all-platforms --live
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENV YOUTUBE_ENABLE=true
ENV YOUTUBE_DRY_RUN=false
CMD ["python", "batch_publish.py", "--json", "videos.json", "--all-platforms", "--live"]
```

---

## 📝 Roadmap

- [x] Meta (Facebook + Instagram)
- [x] TikTok Content Posting API
- [x] YouTube Shorts
- [x] Batch publishing
- [x] SQLite ledger
- [x] Meta analytics
- [ ] TikTok analytics
- [ ] YouTube analytics
- [ ] Web UI dashboard
- [ ] Scheduling (cron/queue)
- [ ] Thumbnail generation
- [ ] Auto-captioning
- [ ] Multi-language support
