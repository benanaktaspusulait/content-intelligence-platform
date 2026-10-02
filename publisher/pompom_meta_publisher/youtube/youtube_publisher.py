"""
youtube_publisher.py — YouTube Shorts Publishing API integration.

YouTube Data API v3 kullanarak Shorts yayınlar.

Flow:
    1. OAuth2 token ile authenticate
    2. Video metadata hazırla (title, description, tags, category)
    3. Resumable upload ile video yükle
    4. #Shorts hashtag ile Short olarak işaretle

API Doc: https://developers.google.com/youtube/v3/docs/videos/insert
"""
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from ..publishing.config import env_bool, env_str
from ..publishing.errors import PublishError
from ..publishing.http_client import register_secret
from ..publishing.ledger import PublishLedger
from ..common.retry import RetryPolicy

log = logging.getLogger("pompom_meta.youtube")

YOUTUBE = "youtube"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_DRY_RUN = "DRY_RUN"
STATUS_ALREADY_PUBLISHED = "ALREADY_PUBLISHED"


@dataclass
class YouTubeConfig:
    """YouTube API configuration."""
    
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    access_token: str = ""
    
    api_base: str = "https://www.googleapis.com/youtube/v3"
    upload_base: str = "https://www.googleapis.com/upload/youtube/v3"
    
    enable_youtube: bool = False
    dry_run: bool = True
    
    # YouTube Shorts requirements
    max_duration: int = 60  # seconds
    max_size: int = 512 * 1024 * 1024  # 512MB
    
    chunk_size: int = 10 * 1024 * 1024  # 10MB chunks
    request_timeout: float = 120.0
    upload_timeout: float = 600.0
    max_attempts: int = 5
    
    # Default metadata
    default_category: str = "22"  # People & Blogs
    default_privacy: str = "public"  # public, unlisted, private
    made_for_kids: bool = True
    
    ledger_path: Path = Path("data/publish_log.db")
    
    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(max_attempts=self.max_attempts)
    
    def youtube_ready(self) -> tuple[bool, str]:
        """Check if YouTube is ready to publish."""
        if not self.enable_youtube:
            return False, "YOUTUBE_ENABLE is disabled"
        if not self.access_token and not self.refresh_token:
            return False, "YOUTUBE_ACCESS_TOKEN or YOUTUBE_REFRESH_TOKEN required"
        return True, ""


def load_youtube_config() -> YouTubeConfig:
    """Load YouTube configuration from environment."""
    from ..publishing.config import load_env_file, DEFAULT_ENV_PATH
    load_env_file(DEFAULT_ENV_PATH)
    
    config = YouTubeConfig(
        client_id=env_str("YOUTUBE_CLIENT_ID"),
        client_secret=env_str("YOUTUBE_CLIENT_SECRET"),
        refresh_token=env_str("YOUTUBE_REFRESH_TOKEN"),
        access_token=env_str("YOUTUBE_ACCESS_TOKEN"),
        enable_youtube=env_bool("YOUTUBE_ENABLE", False),
        dry_run=env_bool("YOUTUBE_DRY_RUN", True),
        default_privacy=env_str("YOUTUBE_PRIVACY", "public"),
        made_for_kids=env_bool("YOUTUBE_MADE_FOR_KIDS", True),
        ledger_path=Path(env_str("YOUTUBE_PUBLISH_DB", "data/publish_log.db")),
    )
    
    # Register secrets
    register_secret(config.client_secret)
    register_secret(config.access_token)
    register_secret(config.refresh_token)
    
    return config


@dataclass
class YouTubePublishResult:
    """YouTube publishing result."""
    platform: str = YOUTUBE
    status: str = ""
    video_id: str | None = None
    share_url: str | None = None
    detail: str | None = None
    
    @property
    def succeeded(self) -> bool:
        return self.status in (STATUS_SUCCESS, STATUS_ALREADY_PUBLISHED)
    
    def __str__(self) -> str:
        parts = [f"{self.platform}={self.status}"]
        if self.video_id:
            parts.append(f"id={self.video_id}")
        if self.detail:
            parts.append(f"detail={self.detail}")
        return " ".join(parts)


@dataclass
class YouTubePublishReport:
    """YouTube publishing report."""
    content_id: str
    video_path: Path
    dry_run: bool = False
    result: YouTubePublishResult | None = None
    
    @property
    def ok(self) -> bool:
        return self.result and self.result.succeeded
    
    def summary(self) -> str:
        if not self.result:
            return f"{self.content_id}: no result"
        return f"{self.content_id}: {self.result}"


def publish_youtube_short(
    video_path: Path | str,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    *,
    config: YouTubeConfig | None = None,
) -> YouTubePublishResult:
    """
    Publish a video as YouTube Short.
    
    Args:
        video_path: Local path to video file
        title: Video title (max 100 chars)
        description: Video description (auto-adds #Shorts)
        tags: Video tags (optional, max 500 chars total)
        config: YouTube configuration
    
    Returns:
        YouTubePublishResult
    
    Note:
        YouTube Shorts requirements:
        - Duration: ≤60 seconds
        - Aspect ratio: 9:16 (vertical)
        - Resolution: min 1080x1920
        - Must include #Shorts in title or description
    """
    cfg = config or load_youtube_config()
    
    usable, reason = cfg.youtube_ready()
    if not usable:
        log.info("YouTube publishing skipped: %s", reason)
        return YouTubePublishResult(status=STATUS_SKIPPED, detail=reason)
    
    video_path = Path(video_path)
    if not video_path.exists():
        return YouTubePublishResult(
            status=STATUS_FAILED,
            detail=f"Video not found: {video_path}"
        )
    
    # Check file size
    file_size = video_path.stat().st_size
    if file_size > cfg.max_size:
        return YouTubePublishResult(
            status=STATUS_FAILED,
            detail=f"Video too large: {file_size / 1024 / 1024:.1f}MB (max: {cfg.max_size / 1024 / 1024}MB)"
        )
    
    # Ensure #Shorts in description
    if "#Shorts" not in description and "#shorts" not in description:
        description = f"{description}\n\n#Shorts" if description else "#Shorts"
    
    # Truncate title if needed
    if len(title) > 100:
        log.warning("Title too long (%s chars), truncating to 100", len(title))
        title = title[:97] + "..."
    
    if cfg.dry_run:
        log.info("[dry-run] YouTube Shorts upload")
        log.info("[dry-run] Video: %s (%s MB)", video_path.name, file_size / 1024 / 1024)
        log.info("[dry-run] Title: %s", title)
        log.info("[dry-run] Description: %s", description[:100])
        return YouTubePublishResult(
            status=STATUS_DRY_RUN,
            detail="dry run, nothing was uploaded"
        )
    
    try:
        # Refresh access token if needed
        if cfg.refresh_token and not cfg.access_token:
            log.info("Refreshing YouTube access token...")
            cfg.access_token = _refresh_access_token(cfg)
        
        # Step 1: Initialize resumable upload
        log.info("YouTube: Initializing upload...")
        upload_url = _initialize_resumable_upload(
            video_path, title, description, tags or [], cfg
        )
        log.info("YouTube: Upload URL obtained")
        
        # Step 2: Upload video
        log.info("YouTube: Uploading video...")
        video_id = _upload_video_resumable(video_path, upload_url, cfg)
        log.info("YouTube: Video uploaded successfully (id=%s)", video_id)
        
        share_url = f"https://youtube.com/shorts/{video_id}"
        
        return YouTubePublishResult(
            status=STATUS_SUCCESS,
            video_id=video_id,
            share_url=share_url,
            detail="Published successfully"
        )
    
    except Exception as e:
        log.exception("YouTube upload failed")
        return YouTubePublishResult(
            status=STATUS_FAILED,
            detail=str(e)
        )


def publish_to_youtube(
    video_path: Path | str,
    title: str,
    description: str,
    content_id: str,
    tags: list[str] | None = None,
    *,
    config: YouTubeConfig | None = None,
    ledger: PublishLedger | None = None,
    force: bool = False,
) -> YouTubePublishReport:
    """
    Publish video to YouTube with duplicate protection.
    
    Args:
        video_path: Local video file path
        title: Video title
        description: Video description
        content_id: Unique content identifier
        tags: Video tags
        config: YouTube configuration
        ledger: Publication ledger
        force: Force re-publish
    
    Returns:
        YouTubePublishReport
    """
    cfg = config or load_youtube_config()
    video_path = Path(video_path)
    
    if not video_path.exists():
        raise PublishError(f"Video not found: {video_path}")
    if not content_id:
        raise PublishError("content_id is required")
    
    book = ledger or PublishLedger(cfg.ledger_path)
    report = YouTubePublishReport(
        content_id=content_id,
        video_path=video_path,
        dry_run=cfg.dry_run
    )
    
    # Check if already published
    if not force:
        existing = book.already_published(content_id, YOUTUBE)
        if existing:
            log.info("YouTube already published for %s (id=%s at %s)",
                     content_id, existing.media_id, existing.published_at)
            report.result = YouTubePublishResult(
                status=STATUS_ALREADY_PUBLISHED,
                video_id=existing.media_id,
                share_url=existing.permalink,
                detail=f"published at {existing.published_at}"
            )
            return report
    
    # Publish
    try:
        result = publish_youtube_short(
            video_path, title, description, tags, config=cfg
        )
        report.result = result
        
        # Record in ledger
        book.record(
            content_id=content_id,
            platform=YOUTUBE,
            status=result.status,
            media_id=result.video_id,
            permalink=result.share_url,
            detail=result.detail
        )
    
    except Exception as exc:
        log.exception("YouTube publishing failed")
        result = YouTubePublishResult(
            status=STATUS_FAILED,
            detail=str(exc)
        )
        report.result = result
        
        book.record(
            content_id=content_id,
            platform=YOUTUBE,
            status=STATUS_FAILED,
            detail=str(exc)
        )
    
    log.info("YouTube publishing summary — %s", report.summary())
    return report


def verify_youtube_configuration(config: YouTubeConfig | None = None) -> dict:
    """
    Verify YouTube configuration without publishing.
    
    Returns a dict describing the configuration status.
    """
    cfg = config or load_youtube_config()
    
    report = {
        "platform": "youtube",
        "api_base": cfg.api_base,
        "dry_run": cfg.dry_run,
        "enabled": cfg.enable_youtube,
        "made_for_kids": cfg.made_for_kids,
        "privacy": cfg.default_privacy,
    }
    
    usable, reason = cfg.youtube_ready()
    report["configured"] = usable
    
    if not usable:
        report["reason"] = reason
    else:
        # Test API connection
        try:
            import urllib.request
            import json as json_module
            
            # Try to get channel info to test token
            access_token = cfg.access_token
            if not access_token and cfg.refresh_token:
                access_token = _refresh_access_token(cfg)
            
            url = f"{cfg.api_base}/channels?part=snippet&mine=true"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json_module.loads(response.read())
                
                if data.get("items"):
                    channel = data["items"][0]
                    report["api_reachable"] = True
                    report["channel_info"] = {
                        "title": channel["snippet"]["title"],
                        "id": channel["id"],
                    }
                else:
                    report["api_reachable"] = False
                    report["error"] = "No channel found"
        except Exception as e:
            report["api_reachable"] = False
            report["error"] = str(e)
    
    return report


# ── YouTube API Helper Functions ───────────────────────────────────────────────

def _refresh_access_token(config: YouTubeConfig) -> str:
    """
    Refresh OAuth2 access token using refresh token.
    
    POST https://oauth2.googleapis.com/token
    """
    import urllib.request
    import urllib.parse
    import json as json_module
    
    url = "https://oauth2.googleapis.com/token"
    
    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "refresh_token": config.refresh_token,
        "grant_type": "refresh_token",
    }
    
    encoded_data = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=encoded_data, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json_module.loads(response.read())
            access_token = result.get("access_token")
            
            if not access_token:
                raise PublishError("Failed to refresh access token")
            
            log.info("Access token refreshed successfully")
            return access_token
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise PublishError(f"Token refresh failed (HTTP {e.code}): {error_body}")


def _initialize_resumable_upload(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    config: YouTubeConfig,
) -> str:
    """
    Step 1: Initialize resumable upload and get upload URL.
    
    POST /upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
    """
    import urllib.request
    import json as json_module
    
    url = f"{config.upload_base}/videos?uploadType=resumable&part=snippet,status"
    
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": config.default_category,
        },
        "status": {
            "privacyStatus": config.default_privacy,
            "selfDeclaredMadeForKids": config.made_for_kids,
        }
    }
    
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*",
        "X-Upload-Content-Length": str(video_path.stat().st_size),
    }
    
    data = json_module.dumps(metadata).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=config.request_timeout) as response:
            upload_url = response.headers.get("Location")
            
            if not upload_url:
                raise PublishError("No upload URL received from YouTube")
            
            return upload_url
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise PublishError(f"YouTube init failed (HTTP {e.code}): {error_body}")


def _upload_video_resumable(
    video_path: Path,
    upload_url: str,
    config: YouTubeConfig,
) -> str:
    """
    Step 2: Upload video using resumable upload.
    
    PUT upload_url with video data
    """
    import urllib.request
    import json as json_module
    
    file_size = video_path.stat().st_size
    chunk_size = config.chunk_size
    
    with open(video_path, 'rb') as video_file:
        uploaded = 0
        
        while uploaded < file_size:
            chunk_data = video_file.read(chunk_size)
            if not chunk_data:
                break
            
            chunk_start = uploaded
            chunk_end = min(uploaded + len(chunk_data) - 1, file_size - 1)
            
            headers = {
                "Content-Range": f"bytes {chunk_start}-{chunk_end}/{file_size}",
                "Content-Type": "video/*",
            }
            
            req = urllib.request.Request(
                upload_url,
                data=chunk_data,
                headers=headers,
                method="PUT"
            )
            
            try:
                with urllib.request.urlopen(req, timeout=config.upload_timeout) as response:
                    uploaded += len(chunk_data)
                    
                    progress = (uploaded / file_size) * 100
                    log.info("YouTube upload progress: %.1f%% (%d/%d bytes)", 
                            progress, uploaded, file_size)
                    
                    # Last chunk returns video info
                    if uploaded >= file_size:
                        result = json_module.loads(response.read())
                        video_id = result.get("id")
                        
                        if not video_id:
                            raise PublishError("No video ID received from YouTube")
                        
                        return video_id
            
            except urllib.error.HTTPError as e:
                # 308 Resume Incomplete is expected for non-final chunks
                if e.code == 308:
                    uploaded += len(chunk_data)
                    continue
                
                error_body = e.read().decode('utf-8')
                raise PublishError(f"Chunk upload failed: {error_body}")
    
    raise PublishError("Upload completed but no video ID received")
