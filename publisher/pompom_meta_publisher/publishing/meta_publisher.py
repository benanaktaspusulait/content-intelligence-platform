"""
meta_publisher.py — Publish a finished vertical video as a Reel on a
Facebook Page and on an Instagram professional account.

The publisher is deliberately content agnostic. It only knows about
`video_path`, `caption`, and `content_id`, so any Pompom Hills content
can reuse it unchanged.

Flow
----
    prepare video -> host it on an HTTPS URL -> create a Reel container
    -> poll upload/processing status -> publish -> log the result

Facebook Page Reels use the three phase Video API on the
`/{page-id}/video_reels` edge (start, upload, finish). Instagram uses the
content publishing flow: `POST /{ig-user-id}/media` with
`media_type=REELS`, status polling on the container, then
`POST /{ig-user-id}/media_publish`.

Public API
----------
    publish_to_meta(video_path, caption, content_id)   top level entry point
    publish_facebook_reel(...)
    publish_instagram_reel(...)
    wait_until_media_ready(container_id, timeout=300, interval=5)
    verify_configuration()

Tokens
------
Facebook Reels publishing needs a **Page Access Token** for a Page the
app user administers, with `pages_manage_posts`, `pages_read_engagement`,
and `pages_show_list`. Instagram needs `instagram_basic` and
`instagram_content_publish`. Derive a long lived Page token from a long
lived User token with:

    GET /{page-id}?fields=access_token&access_token={long-lived-user-token}

Set it as META_PAGE_ACCESS_TOKEN. Tokens are never logged.
"""
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import MetaConfig, load_meta_config
from .errors import (
    MetaApiError,
    MetaConfigurationError,
    MetaProcessingTimeout,
    MetaStorageError,
    MetaUploadError,
    PublishError,
)
from .http_client import get_json, post_form, request, scrub
from .ledger import PublishLedger
from .storage import VideoStorage, create_storage

log = logging.getLogger("pompom_meta.publisher")

FACEBOOK = "facebook"
INSTAGRAM = "instagram"

STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_SKIPPED = "SKIPPED"
STATUS_DRY_RUN = "DRY_RUN"
STATUS_ALREADY_PUBLISHED = "ALREADY_PUBLISHED"

# Instagram container status codes.
IG_READY = "FINISHED"
IG_TERMINAL_FAILURES = {"ERROR", "EXPIRED"}

# Facebook upload/processing phase states.
FB_PHASE_COMPLETE = "complete"
FB_PHASE_ERROR = "error"

# Instagram caption hard limit.
IG_CAPTION_LIMIT = 2200


# ── Result objects ─────────────────────────────────────────────────────────────

@dataclass
class PublishResult:
    platform: str
    status: str
    media_id: str | None = None
    permalink: str | None = None
    detail: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status in (STATUS_SUCCESS, STATUS_ALREADY_PUBLISHED)

    def __str__(self) -> str:
        parts = [f"{self.platform}={self.status}"]
        if self.media_id:
            parts.append(f"id={self.media_id}")
        if self.detail:
            parts.append(f"detail={self.detail}")
        return " ".join(parts)


@dataclass
class PublishReport:
    content_id: str
    video_path: Path
    video_url: str | None = None
    dry_run: bool = False
    results: dict[str, PublishResult] = field(default_factory=dict)

    def add(self, result: PublishResult) -> None:
        self.results[result.platform] = result

    @property
    def failures(self) -> list[PublishResult]:
        return [r for r in self.results.values() if r.status == STATUS_FAILED]

    @property
    def published(self) -> list[PublishResult]:
        return [r for r in self.results.values() if r.status == STATUS_SUCCESS]

    @property
    def ok(self) -> bool:
        return not self.failures

    def raise_for_status(self) -> None:
        """Raise when any enabled platform failed. Optional for callers."""
        if self.failures:
            detail = "; ".join(f"{r.platform}: {r.detail}" for r in self.failures)
            raise PublishError(f"Meta publishing failed — {detail}")

    def summary(self) -> str:
        if not self.results:
            return f"{self.content_id}: no target platform enabled"
        return f"{self.content_id}: " + ", ".join(
            str(r) for r in self.results.values())


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _resolved_config(config: MetaConfig | None) -> MetaConfig:
    return config if config is not None else load_meta_config()


def _log_payload(label: str, url: str, payload: dict) -> None:
    """Log an endpoint and its payload with tokens removed."""
    safe = {
        key: ("<redacted>" if "token" in key.lower() else scrub(str(value))[:200])
        for key, value in payload.items()
    }
    log.info("%s -> POST %s", label, scrub(url))
    log.info("%s    payload: %s", label, safe)


def _permalink(node_id: str, field_name: str, config: MetaConfig,
               token: str) -> str | None:
    """Best effort permalink lookup; never breaks a successful publish."""
    try:
        data = get_json(
            f"{config.graph_base}/{node_id}",
            {"fields": field_name, "access_token": token},
            timeout=config.request_timeout,
            retry=config.retry_policy,
        )
        return data.get(field_name)
    except PublishError as exc:
        log.debug("Permalink lookup failed for %s: %s", node_id, exc)
        return None


def _truncate_caption(caption: str, limit: int = IG_CAPTION_LIMIT) -> str:
    """Keep captions inside the platform limit without breaking UTF-8."""
    if caption is None:
        return ""
    if len(caption) <= limit:
        return caption
    log.warning("Caption is %s characters; trimming to %s for Instagram.",
                len(caption), limit)
    return caption[: limit - 1].rstrip() + "…"


# ── Status polling ─────────────────────────────────────────────────────────────

def wait_until_media_ready(container_id: str, timeout: int = 300,
                           interval: int = 5, *,
                           config: MetaConfig | None = None,
                           platform: str = INSTAGRAM,
                           token: str | None = None) -> dict:
    """Poll a media container until it is ready to publish.

    Controlled polling instead of a fixed sleep: one status request every
    `interval` seconds for at most `timeout` seconds.

    Args:
        container_id: Instagram creation id, or Facebook video id.
        timeout: total seconds to wait before giving up.
        interval: seconds between two status requests.
        platform: "instagram" or "facebook".

    Returns:
        The last status payload received from the Graph API.

    Raises:
        MetaUploadError: the platform reported a terminal failure.
        MetaProcessingTimeout: still not ready when the window closed.
    """
    cfg = _resolved_config(config)
    interval = max(1, int(interval))
    deadline = time.monotonic() + max(interval, int(timeout))
    access_token = token or (
        cfg.instagram_token() if platform == INSTAGRAM else cfg.facebook_token())
    probe = _instagram_status if platform == INSTAGRAM else _facebook_status

    attempt = 0
    last_payload: dict = {}
    while True:
        attempt += 1
        ready, failed, state, last_payload = probe(container_id, cfg, access_token)
        if ready:
            log.info("%s media %s is ready (%s) after %s check(s)",
                     platform.capitalize(), container_id, state, attempt)
            return last_payload
        if failed:
            raise MetaUploadError(
                f"{platform.capitalize()} media {container_id} failed during "
                f"processing: {state}")
        if time.monotonic() >= deadline:
            raise MetaProcessingTimeout(
                f"{platform.capitalize()} media {container_id} was still in "
                f"state '{state}' after {timeout}s. The video was not published; "
                "the local file is untouched.")
        log.info("%s media processing... (%s)", platform.capitalize(), state)
        time.sleep(interval)


def _instagram_status(container_id: str, config: MetaConfig,
                      token: str) -> tuple[bool, bool, str, dict]:
    payload = get_json(
        f"{config.graph_base}/{container_id}",
        {"fields": "status_code,status", "access_token": token},
        timeout=config.request_timeout,
        retry=config.retry_policy,
    )
    code = (payload.get("status_code") or "").upper()
    detail = payload.get("status") or code or "UNKNOWN"
    if code in ("FINISHED", "PUBLISHED"):
        return True, False, code, payload
    if code in IG_TERMINAL_FAILURES:
        return False, True, scrub(str(detail)), payload
    return False, False, code or "IN_PROGRESS", payload


def _facebook_status(video_id: str, config: MetaConfig,
                     token: str) -> tuple[bool, bool, str, dict]:
    payload = get_json(
        f"{config.graph_base}/{video_id}",
        {"fields": "status", "access_token": token},
        timeout=config.request_timeout,
        retry=config.retry_policy,
    )
    status = payload.get("status") or {}
    uploading = (status.get("uploading_phase") or {}).get("status", "")
    processing = (status.get("processing_phase") or {}).get("status", "")
    video_status = status.get("video_status", "")
    state = f"upload={uploading or '?'} processing={processing or '?'}"

    for phase in ("uploading_phase", "processing_phase"):
        phase_data = status.get(phase) or {}
        if phase_data.get("status") == FB_PHASE_ERROR:
            error = phase_data.get("errors") or phase_data.get("error") or phase
            return False, True, scrub(str(error)), payload

    if processing == FB_PHASE_COMPLETE or video_status == "ready":
        return True, False, state, payload
    return False, False, state, payload


# ── Facebook Page Reels ────────────────────────────────────────────────────────

def publish_facebook_reel(video_path: Path | str, caption: str, *,
                          config: MetaConfig | None = None,
                          video_url: str | None = None,
                          timeout: int | None = None,
                          interval: int | None = None) -> PublishResult:
    """Publish a Reel on a Facebook Page.

    Uses the three phase Video API on `/{page-id}/video_reels`:
      1. `upload_phase=start` creates the upload session and video id
      2. the bytes are sent to the returned rupload endpoint, either as a
         hosted `file_url` or as a single resumable byte range
      3. `upload_phase=finish` with `video_state=PUBLISHED` publishes it

    A hosted `video_url` is preferred when available; otherwise the local
    file is uploaded directly, which means Facebook works even without a
    storage backend.
    """
    cfg = _resolved_config(config)
    usable, reason = cfg.facebook_ready()
    if not usable:
        log.info("Facebook publishing skipped: %s", reason)
        return PublishResult(FACEBOOK, STATUS_SKIPPED, detail=reason)

    video_path = Path(video_path)
    if video_url is None and not video_path.exists():
        raise MetaUploadError(f"Video not found: {video_path}")

    token = cfg.facebook_token()
    edge = f"{cfg.graph_base}/{cfg.page_id}/video_reels"

    if cfg.dry_run:
        _log_payload("[dry-run] facebook:start", edge,
                     {"upload_phase": "start", "access_token": token})
        _log_payload("[dry-run] facebook:finish", edge, {
            "upload_phase": "finish",
            "video_id": "<from start phase>",
            "video_state": "PUBLISHED",
            "description": caption,
        })
        if video_url:
            log.info("[dry-run] facebook:upload -> POST %s (file_url=%s)",
                     cfg.rupload_base, video_url)
        else:
            log.info("[dry-run] facebook:upload -> POST %s/<video_id> "
                     "(%s bytes from %s)", cfg.rupload_base,
                     video_path.stat().st_size, video_path)
        return PublishResult(FACEBOOK, STATUS_DRY_RUN,
                             detail="dry run, nothing was sent to Meta")

    # ── Phase 1: initialize the upload session ────────────────────────────
    start = post_form(edge, {"upload_phase": "start", "access_token": token},
                      timeout=cfg.request_timeout, retry=cfg.retry_policy)
    video_id = start.get("video_id")
    upload_url = start.get("upload_url") or f"{cfg.rupload_base}/{video_id}"
    if not video_id:
        raise MetaUploadError(
            f"Facebook did not return a video_id: {scrub(str(start))}")
    log.info("Facebook reel container created (video_id=%s)", video_id)

    # ── Phase 2: transfer the video ───────────────────────────────────────
    upload_headers = {"Authorization": f"OAuth {token}"}
    if video_url:
        log.info("Uploading video... Facebook will ingest %s", video_url)
        upload_headers["file_url"] = video_url
        body = b""
    else:
        size = video_path.stat().st_size
        log.info("Uploading video... %s bytes to Facebook (%s)",
                 size, video_path.name)
        upload_headers.update({
            "offset": "0",
            "file_size": str(size),
            "Content-Type": "application/octet-stream",
        })
        body = video_path.read_bytes()

    upload_response = request(
        "POST", upload_url, data=body, headers=upload_headers,
        timeout=cfg.upload_timeout, retry=cfg.retry_policy,
    ).json()
    if not upload_response.get("success", True):
        raise MetaUploadError(
            f"Facebook rejected the upload: {scrub(str(upload_response))}")
    log.info("Facebook upload accepted for video_id=%s", video_id)

    # ── Phase 3: wait for processing, then publish ────────────────────────
    wait_until_media_ready(
        video_id,
        timeout=timeout if timeout is not None else cfg.poll_timeout,
        interval=interval if interval is not None else cfg.poll_interval,
        config=cfg, platform=FACEBOOK, token=token,
    )

    finish_params = {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption or "",
        "access_token": token,
    }
    if cfg.facebook_reel_title:
        finish_params["title"] = cfg.facebook_reel_title
    finish = post_form(edge, finish_params,
                       timeout=cfg.request_timeout, retry=cfg.retry_policy)
    if not finish.get("success", True):
        raise MetaUploadError(
            f"Facebook could not publish the reel: {scrub(str(finish))}")

    media_id = finish.get("post_id") or video_id
    permalink = _permalink(video_id, "permalink_url", cfg, token)
    log.info("Facebook reel published: %s", media_id)
    if permalink:
        log.info("Facebook reel URL: %s", permalink)
    return PublishResult(FACEBOOK, STATUS_SUCCESS,
                         media_id=str(media_id), permalink=permalink)


# ── Instagram Reels ────────────────────────────────────────────────────────────

def publish_instagram_reel(video_path: Path | str, caption: str, *,
                           video_url: str | None = None,
                           config: MetaConfig | None = None,
                           timeout: int | None = None,
                           interval: int | None = None) -> PublishResult:
    """Publish a Reel on an Instagram professional account.

    Instagram only ingests a publicly reachable HTTPS URL, so a storage
    backend (or an explicit `video_url`) is required.

      1. `POST /{ig-user-id}/media` with `media_type=REELS`, `video_url`,
         `caption` returns a creation id
      2. the container is polled until `status_code=FINISHED`
      3. `POST /{ig-user-id}/media_publish` with `creation_id` publishes it
    """
    cfg = _resolved_config(config)
    usable, reason = cfg.instagram_ready()
    if not usable:
        log.info("Instagram publishing skipped: %s", reason)
        return PublishResult(INSTAGRAM, STATUS_SKIPPED, detail=reason)

    if not video_url:
        reason = ("Instagram needs a public HTTPS video URL; configure "
                  "META_STORAGE_BACKEND or pass video_url explicitly")
        log.warning("Instagram publishing skipped: %s", reason)
        return PublishResult(INSTAGRAM, STATUS_SKIPPED, detail=reason)

    token = cfg.instagram_token()
    caption = _truncate_caption(caption or "")
    media_edge = f"{cfg.graph_base}/{cfg.instagram_account_id}/media"
    publish_edge = f"{cfg.graph_base}/{cfg.instagram_account_id}/media_publish"

    container_params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true" if cfg.instagram_share_to_feed else "false",
        "access_token": token,
    }

    if cfg.dry_run:
        _log_payload("[dry-run] instagram:container", media_edge, container_params)
        _log_payload("[dry-run] instagram:publish", publish_edge,
                     {"creation_id": "<from container>", "access_token": token})
        return PublishResult(INSTAGRAM, STATUS_DRY_RUN,
                             detail="dry run, nothing was sent to Meta")

    container = post_form(media_edge, container_params,
                          timeout=cfg.request_timeout, retry=cfg.retry_policy)
    creation_id = container.get("id")
    if not creation_id:
        raise MetaUploadError(
            f"Instagram did not return a creation id: {scrub(str(container))}")
    log.info("Instagram container created (creation_id=%s)", creation_id)

    wait_until_media_ready(
        creation_id,
        timeout=timeout if timeout is not None else cfg.poll_timeout,
        interval=interval if interval is not None else cfg.poll_interval,
        config=cfg, platform=INSTAGRAM, token=token,
    )

    published = post_form(
        publish_edge,
        {"creation_id": creation_id, "access_token": token},
        timeout=cfg.request_timeout, retry=cfg.retry_policy,
    )
    media_id = published.get("id")
    if not media_id:
        raise MetaUploadError(
            f"Instagram did not return a media id: {scrub(str(published))}")

    permalink = _permalink(media_id, "permalink", cfg, token)
    log.info("Instagram reel published: %s", media_id)
    if permalink:
        log.info("Instagram reel URL: %s", permalink)
    return PublishResult(INSTAGRAM, STATUS_SUCCESS,
                         media_id=str(media_id), permalink=permalink)


# ── Top level entry point ──────────────────────────────────────────────────────

def publish_to_meta(video_path: Path | str, caption: str, content_id: str, *,
                    config: MetaConfig | None = None,
                    storage: VideoStorage | None = None,
                    ledger: PublishLedger | None = None,
                    video_url: str | None = None,
                    platforms: list[str] | None = None,
                    force: bool = False) -> PublishReport:
    """Publish one finished video to every enabled Meta target.

    Content agnostic: any pipeline that produces a vertical MP4, a caption
    string, and a stable content id can call this.

    Args:
        video_path: local path of the finished master.
        caption: post text; UTF-8 including emojis is preserved as-is.
        content_id: stable id used for duplicate protection, e.g. "pompom-reel-001".
        video_url: skip the storage step and use this HTTPS URL.
        platforms: restrict to a subset of ("facebook", "instagram").
        force: publish again even when the ledger holds a SUCCESS row.

    Returns:
        A PublishReport. Per platform failures are captured in the report
        rather than raised, so a publishing problem cannot destroy a
        successful render. Call `report.raise_for_status()` if the caller
        wants an exception.

    Raises:
        MetaConfigurationError: the configuration itself is unusable.
    """
    cfg = _resolved_config(config)
    video_path = Path(video_path)
    if not video_path.exists():
        raise MetaConfigurationError(f"Video not found: {video_path}")
    if not content_id:
        raise MetaConfigurationError("content_id is required for duplicate protection")

    book = ledger if ledger is not None else PublishLedger(cfg.ledger_path)
    report = PublishReport(content_id=content_id, video_path=video_path,
                           dry_run=cfg.dry_run)

    wanted = [p.lower() for p in (platforms or [FACEBOOK, INSTAGRAM])]
    targets: list[str] = []
    for platform, ready in ((FACEBOOK, cfg.facebook_ready),
                            (INSTAGRAM, cfg.instagram_ready)):
        if platform not in wanted:
            continue
        usable, reason = ready()
        if not usable:
            log.info("%s target disabled: %s", platform.capitalize(), reason)
            report.add(PublishResult(platform, STATUS_SKIPPED, detail=reason))
            continue
        existing = None if force else book.already_published(content_id, platform)
        if existing is not None:
            log.info("%s already published for %s (media_id=%s at %s) — skipping",
                     platform.capitalize(), content_id,
                     existing.media_id, existing.published_at)
            report.add(PublishResult(
                platform, STATUS_ALREADY_PUBLISHED,
                media_id=existing.media_id, permalink=existing.permalink,
                detail=f"published at {existing.published_at}"))
            continue
        targets.append(platform)

    if not targets:
        log.info("Nothing to publish for %s", content_id)
        return report

    if cfg.dry_run:
        log.warning("META_DRY_RUN is enabled — preparing payloads only, "
                    "no request will be sent to Meta.")

    # ── Host the video so Meta can download it ────────────────────────────
    store = storage if storage is not None else create_storage()
    owns_url = False
    needs_url = INSTAGRAM in targets
    if video_url is None:
        if cfg.dry_run:
            # Keep the Instagram payload visible in a dry run without
            # touching the storage backend.
            if needs_url and not store.can_host:
                log.warning(
                    "Storage backend is '%s': in a live run Instagram would be "
                    "skipped because no public URL can be produced.", store.name)
            video_url = f"<{store.name}-storage-url>/{video_path.name}"
        elif needs_url or store.can_host:
            try:
                video_url = store.upload(video_path, content_id=content_id)
                owns_url = True
            except MetaStorageError as exc:
                if needs_url:
                    log.error("Could not host the video for Instagram: %s", exc)
                else:
                    log.info("No hosted URL available (%s); Facebook will "
                             "receive the raw bytes.", exc)
    report.video_url = video_url

    try:
        for platform in targets:
            try:
                if platform == FACEBOOK:
                    result = publish_facebook_reel(
                        video_path, caption, config=cfg, video_url=video_url)
                else:
                    result = publish_instagram_reel(
                        video_path, caption, video_url=video_url, config=cfg)
            except PublishError as exc:
                log.error("%s publishing failed: %s", platform.capitalize(), exc)
                if isinstance(exc, MetaApiError) and exc.body:
                    log.error("%s API response: %s",
                              platform.capitalize(), exc.body)
                result = PublishResult(platform, STATUS_FAILED, detail=str(exc))
            except Exception as exc:  # never let publishing break the caller
                log.exception("%s publishing raised an unexpected error",
                              platform.capitalize())
                result = PublishResult(platform, STATUS_FAILED, detail=str(exc))

            report.add(result)
            book.record(content_id, platform, result.status,
                        media_id=result.media_id, permalink=result.permalink,
                        detail=result.detail)
    finally:
        if owns_url and video_url:
            store.cleanup(video_url)

    log.info("Meta publishing summary — %s", report.summary())
    return report


# ── Configuration self check ───────────────────────────────────────────────────

def verify_configuration(config: MetaConfig | None = None) -> dict:
    """Validate tokens and ids without publishing anything.

    Returns a plain dict describing what the configuration can reach, so
    it is safe to print. No token is included.
    """
    cfg = _resolved_config(config)
    report: dict = {
        "api_version": cfg.api_version,
        "dry_run": cfg.dry_run,
        "facebook": {"enabled": cfg.enable_facebook},
        "instagram": {"enabled": cfg.enable_instagram},
        "storage": {},
    }

    try:
        store = create_storage()
        report["storage"] = {"backend": store.name, "can_host": store.can_host}
    except PublishError as exc:
        report["storage"] = {"backend": "invalid", "error": str(exc)}

    usable, reason = cfg.facebook_ready()
    report["facebook"]["configured"] = usable
    if not usable:
        report["facebook"]["reason"] = reason
    else:
        try:
            page = get_json(
                f"{cfg.graph_base}/{cfg.page_id}",
                {"fields": "id,name", "access_token": cfg.facebook_token()},
                timeout=cfg.request_timeout, retry=cfg.retry_policy)
            report["facebook"].update(
                {"page_id": page.get("id"), "page_name": page.get("name"),
                 "reachable": True})
        except PublishError as exc:
            report["facebook"].update({"reachable": False, "error": str(exc)})

    usable, reason = cfg.instagram_ready()
    report["instagram"]["configured"] = usable
    if not usable:
        report["instagram"]["reason"] = reason
    else:
        token = cfg.instagram_token()
        try:
            account = get_json(
                f"{cfg.graph_base}/{cfg.instagram_account_id}",
                {"fields": "id,username", "access_token": token},
                timeout=cfg.request_timeout, retry=cfg.retry_policy)
            report["instagram"].update(
                {"account_id": account.get("id"),
                 "username": account.get("username"), "reachable": True})
        except PublishError as exc:
            report["instagram"].update({"reachable": False, "error": str(exc)})
        try:
            limit = get_json(
                f"{cfg.graph_base}/{cfg.instagram_account_id}/content_publishing_limit",
                {"fields": "config,quota_usage", "access_token": token},
                timeout=cfg.request_timeout, retry=cfg.retry_policy)
            report["instagram"]["publishing_limit"] = limit.get("data")
        except PublishError:
            pass

    return report
