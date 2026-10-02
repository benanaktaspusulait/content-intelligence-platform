"""
tiktok_publisher.py — TikTok Content Posting API integration.

TikTok for Developers API kullanarak video yayınlar.

Flow:
    1. Video upload URL al (initialize)
    2. Video'yu chunk'lar halinde upload et
    3. Video publish et
    4. Status kontrolü

API Doc: https://developers.tiktok.com/doc/content-posting-api-get-started
"""
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..publishing.config import env_bool, env_str
from ..publishing.errors import PublishError
from ..publishing.http_client import register_secret
from ..publishing.ledger import PublishLedger
from ..common.retry import RetryPolicy

log = logging.getLogger("pompom_meta.tiktok")

TIKTOK = "tiktok"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_DRY_RUN = "DRY_RUN"
STATUS_ALREADY_PUBLISHED = "ALREADY_PUBLISHED"


@dataclass
class TikTokConfig:
    """TikTok API configuration."""
    
    client_key: str = ""
    client_secret: str = ""
    access_token: str = ""
    
    api_base: str = "https://open.tiktokapis.com"
    api_version: str = "v2"
    
    enable_tiktok: bool = False
    dry_run: bool = True
    
    chunk_size: int = 10 * 1024 * 1024  # 10MB chunks
    poll_timeout: int = 300
    poll_interval: int = 5
    request_timeout: float = 120.0
    upload_timeout: float = 600.0
    max_attempts: int = 5
    
    ledger_path: Path = Path("data/publish_log.db")
    
    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(max_attempts=self.max_attempts)
    
    def tiktok_ready(self) -> tuple[bool, str]:
        """Check if TikTok is ready to publish."""
        if not self.enable_tiktok:
            return False, "TIKTOK_ENABLE is disabled"
        if not self.access_token:
            return False, "TIKTOK_ACCESS_TOKEN is not set"
        return True, ""


def load_tiktok_config() -> TikTokConfig:
    """Load TikTok configuration from environment."""
    from ..publishing.config import load_env_file, DEFAULT_ENV_PATH
    load_env_file(DEFAULT_ENV_PATH)
    
    config = TikTokConfig(
        client_key=env_str("TIKTOK_CLIENT_KEY"),
        client_secret=env_str("TIKTOK_CLIENT_SECRET"),
        access_token=env_str("TIKTOK_ACCESS_TOKEN"),
        api_base=env_str("TIKTOK_API_BASE", "https://open.tiktokapis.com"),
        enable_tiktok=env_bool("TIKTOK_ENABLE", False),
        dry_run=env_bool("TIKTOK_DRY_RUN", True),
        ledger_path=Path(env_str("TIKTOK_PUBLISH_DB", "data/publish_log.db")),
    )
    
    # Register secrets
    register_secret(config.client_secret)
    register_secret(config.access_token)
    
    return config


@dataclass
class TikTokPublishResult:
    """TikTok publishing result."""
    platform: str = TIKTOK
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
class TikTokPublishReport:
    """TikTok publishing report."""
    content_id: str
    video_path: Path
    dry_run: bool = False
    result: TikTokPublishResult | None = None
    
    @property
    def ok(self) -> bool:
        return self.result and self.result.succeeded
    
    def summary(self) -> str:
        if not self.result:
            return f"{self.content_id}: no result"
        return f"{self.content_id}: {self.result}"


def publish_tiktok_video(
    video_path: Path | str,
    caption: str,
    *,
    config: TikTokConfig | None = None,
) -> TikTokPublishResult:
    """
    Publish a video to TikTok.
    
    Args:
        video_path: Local path to video file
        caption: Video caption/description
        config: TikTok configuration
    
    Returns:
        TikTokPublishResult
    
    Note:
        TikTok API requires:
        - Video: MP4, max 287.6MB, max 10 min
        - Caption: max 2200 characters
        - Hashtags: part of caption
    """
    cfg = config or load_tiktok_config()
    
    usable, reason = cfg.tiktok_ready()
    if not usable:
        log.info("TikTok publishing skipped: %s", reason)
        return TikTokPublishResult(status=STATUS_SKIPPED, detail=reason)
    
    video_path = Path(video_path)
    if not video_path.exists():
        return TikTokPublishResult(
            status=STATUS_FAILED,
            detail=f"Video not found: {video_path}"
        )
    
    # Check file size (TikTok limit: ~288MB)
    file_size = video_path.stat().st_size
    max_size = 287 * 1024 * 1024  # 287MB
    if file_size > max_size:
        return TikTokPublishResult(
            status=STATUS_FAILED,
            detail=f"Video too large: {file_size / 1024 / 1024:.1f}MB (max: 287MB)"
        )
    
    # Truncate caption if needed
    if len(caption) > 2200:
        log.warning("Caption too long (%s chars), truncating to 2200", len(caption))
        caption = caption[:2199] + "…"
    
    if cfg.dry_run:
        log.info("[dry-run] TikTok video upload")
        log.info("[dry-run] Video: %s (%s MB)", video_path.name, file_size / 1024 / 1024)
        log.info("[dry-run] Caption: %s", caption[:100])
        return TikTokPublishResult(
            status=STATUS_DRY_RUN,
            detail="dry run, nothing was uploaded"
        )
    
    try:
        # Step 1: Initialize upload
        log.info("TikTok: Initializing upload...")
        init_response = _initialize_upload(video_path, cfg)
        
        publish_id = init_response.get("publish_id")
        upload_url = init_response.get("upload_url")
        
        if not publish_id or not upload_url:
            return TikTokPublishResult(
                status=STATUS_FAILED,
                detail=f"TikTok init failed: {init_response}"
            )
        
        log.info("TikTok: Upload initialized (publish_id=%s)", publish_id)
        
        # Step 2: Upload video
        log.info("TikTok: Uploading video...")
        _upload_video_to_tiktok(video_path, upload_url, cfg)
        log.info("TikTok: Video uploaded successfully")
        
        # Step 3: Wait for processing
        log.info("TikTok: Waiting for processing...")
        status_result = _wait_for_processing(publish_id, cfg)
        
        if status_result.get("status") == "PUBLISH_COMPLETE":
            share_url = status_result.get("share_url", "")
            log.info("TikTok: Video published successfully!")
            
            return TikTokPublishResult(
                status=STATUS_SUCCESS,
                video_id=publish_id,
                share_url=share_url,
                detail="Published successfully"
            )
        else:
            return TikTokPublishResult(
                status=STATUS_FAILED,
                video_id=publish_id,
                detail=f"Processing failed: {status_result.get('fail_reason', 'Unknown')}"
            )
    
    except Exception as e:
        log.exception("TikTok upload failed")
        return TikTokPublishResult(
            status=STATUS_FAILED,
            detail=str(e)
        )


def publish_to_tiktok(
    video_path: Path | str,
    caption: str,
    content_id: str,
    *,
    config: TikTokConfig | None = None,
    ledger: PublishLedger | None = None,
    force: bool = False,
) -> TikTokPublishReport:
    """
    Publish video to TikTok with duplicate protection.
    
    Args:
        video_path: Local video file path
        caption: Video caption
        content_id: Unique content identifier
        config: TikTok configuration
        ledger: Publication ledger
        force: Force re-publish
    
    Returns:
        TikTokPublishReport
    """
    cfg = config or load_tiktok_config()
    video_path = Path(video_path)
    
    if not video_path.exists():
        raise PublishError(f"Video not found: {video_path}")
    if not content_id:
        raise PublishError("content_id is required")
    
    book = ledger or PublishLedger(cfg.ledger_path)
    report = TikTokPublishReport(
        content_id=content_id,
        video_path=video_path,
        dry_run=cfg.dry_run
    )
    
    # Check if already published
    if not force:
        existing = book.already_published(content_id, TIKTOK)
        if existing:
            log.info("TikTok already published for %s (id=%s at %s)",
                     content_id, existing.media_id, existing.published_at)
            report.result = TikTokPublishResult(
                status=STATUS_ALREADY_PUBLISHED,
                video_id=existing.media_id,
                share_url=existing.permalink,
                detail=f"published at {existing.published_at}"
            )
            return report
    
    # Publish
    try:
        result = publish_tiktok_video(video_path, caption, config=cfg)
        report.result = result
        
        # Record in ledger
        book.record(
            content_id=content_id,
            platform=TIKTOK,
            status=result.status,
            media_id=result.video_id,
            permalink=result.share_url,
            detail=result.detail
        )
    
    except Exception as exc:
        log.exception("TikTok publishing failed")
        result = TikTokPublishResult(
            status=STATUS_FAILED,
            detail=str(exc)
        )
        report.result = result
        
        book.record(
            content_id=content_id,
            platform=TIKTOK,
            status=STATUS_FAILED,
            detail=str(exc)
        )
    
    log.info("TikTok publishing summary — %s", report.summary())
    return report


def verify_tiktok_configuration(config: TikTokConfig | None = None) -> dict:
    """
    Verify TikTok configuration without publishing.
    
    Returns a dict describing the configuration status.
    """
    cfg = config or load_tiktok_config()
    
    report = {
        "platform": "tiktok",
        "api_version": cfg.api_version,
        "dry_run": cfg.dry_run,
        "enabled": cfg.enable_tiktok,
    }
    
    usable, reason = cfg.tiktok_ready()
    report["configured"] = usable
    
    if not usable:
        report["reason"] = reason
    else:
        # Test API connection
        try:
            import urllib.request
            import json as json_module
            
            # Try to get creator info to test token
            url = f"{cfg.api_base}/v2/post/publish/creator_info/query/"
            headers = {
                "Authorization": f"Bearer {cfg.access_token}",
                "Content-Type": "application/json",
            }
            
            req = urllib.request.Request(url, headers=headers, method="POST")
            req.add_header("Content-Type", "application/json")
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json_module.loads(response.read())
                
                if data.get("data"):
                    report["api_reachable"] = True
                    report["creator_info"] = {
                        "username": data["data"].get("creator_username", ""),
                        "avatar": data["data"].get("creator_avatar_url", ""),
                    }
                else:
                    report["api_reachable"] = False
                    report["error"] = data.get("error", {}).get("message", "Unknown")
        except Exception as e:
            report["api_reachable"] = False
            report["error"] = str(e)
    
    return report


# ── TikTok API Helper Functions ────────────────────────────────────────────────

def _initialize_upload(video_path: Path, config: TikTokConfig) -> dict:
    """
    Step 1: Initialize TikTok upload and get upload URL.
    
    POST /v2/post/publish/video/init/
    """
    import urllib.request
    import json as json_module
    
    file_size = video_path.stat().st_size
    chunk_size = config.chunk_size
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    
    url = f"{config.api_base}/v2/post/publish/video/init/"
    
    payload = {
        "post_info": {
            "title": "Pompom Hills",  # Optional
            "privacy_level": "SELF_ONLY",  # or "PUBLIC_TO_EVERYONE"
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        }
    }
    
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }
    
    data = json_module.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=config.request_timeout) as response:
            result = json_module.loads(response.read())
            
            if result.get("error"):
                error_msg = result["error"].get("message", "Unknown error")
                raise PublishError(f"TikTok init error: {error_msg}")
            
            return result.get("data", {})
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise PublishError(f"TikTok init failed (HTTP {e.code}): {error_body}")


def _upload_video_to_tiktok(video_path: Path, upload_url: str, config: TikTokConfig):
    """
    Step 2: Upload video chunks to TikTok.
    
    PUT upload_url with video data
    """
    import urllib.request
    
    file_size = video_path.stat().st_size
    chunk_size = config.chunk_size
    
    with open(video_path, 'rb') as video_file:
        chunk_index = 0
        uploaded = 0
        
        while uploaded < file_size:
            chunk_data = video_file.read(chunk_size)
            if not chunk_data:
                break
            
            chunk_start = uploaded
            chunk_end = min(uploaded + len(chunk_data) - 1, file_size - 1)
            
            headers = {
                "Content-Range": f"bytes {chunk_start}-{chunk_end}/{file_size}",
                "Content-Type": "video/mp4",
            }
            
            req = urllib.request.Request(
                upload_url,
                data=chunk_data,
                headers=headers,
                method="PUT"
            )
            
            try:
                with urllib.request.urlopen(req, timeout=config.upload_timeout) as response:
                    if response.status not in (200, 201, 204):
                        raise PublishError(f"Chunk upload failed: HTTP {response.status}")
                
                uploaded += len(chunk_data)
                chunk_index += 1
                
                progress = (uploaded / file_size) * 100
                log.info("TikTok upload progress: %.1f%% (%d/%d bytes)", 
                        progress, uploaded, file_size)
            
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                raise PublishError(f"Chunk {chunk_index} upload failed: {error_body}")


def _wait_for_processing(publish_id: str, config: TikTokConfig) -> dict:
    """
    Step 3: Wait for TikTok to process the video.
    
    POST /v2/post/publish/status/fetch/
    """
    import urllib.request
    import json as json_module
    
    url = f"{config.api_base}/v2/post/publish/status/fetch/"
    
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Content-Type": "application/json",
    }
    
    payload = {"publish_id": publish_id}
    
    deadline = time.time() + config.poll_timeout
    attempt = 0
    
    while time.time() < deadline:
        attempt += 1
        
        data = json_module.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=config.request_timeout) as response:
                result = json_module.loads(response.read())
                
                if result.get("error"):
                    error_msg = result["error"].get("message", "Unknown error")
                    raise PublishError(f"TikTok status check error: {error_msg}")
                
                data_obj = result.get("data", {})
                status = data_obj.get("status", "")
                
                log.info("TikTok processing status: %s (attempt %d)", status, attempt)
                
                # Status values: PROCESSING_UPLOAD, PROCESSING_DOWNLOAD, 
                #                SEND_TO_USER_INBOX, PUBLISH_COMPLETE, FAILED
                
                if status == "PUBLISH_COMPLETE":
                    return data_obj
                
                if status == "FAILED":
                    return data_obj
                
                # Still processing, wait and retry
                time.sleep(config.poll_interval)
        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            log.warning("Status check failed: %s", error_body)
            time.sleep(config.poll_interval)
    
    # Timeout
    raise PublishError(
        f"TikTok processing timeout after {config.poll_timeout}s"
    )
