"""
storage.py — Pluggable public video hosting for Meta ingestion.

Meta must fetch the video itself, so a local path is never enough:
Instagram only accepts `video_url`, and Facebook can either read a
`file_url` or receive raw bytes. This module turns a local file into an
HTTPS URL behind a single interface:

    storage = create_storage()
    video_url = storage.upload(video_path, content_id="pompom-reel-001")
    ...
    storage.cleanup(video_url)

Backends are selected with META_STORAGE_BACKEND:

    none        no hosting; Facebook falls back to a direct byte upload
                and Instagram is skipped unless a video_url is supplied
    public_dir  copy into a directory already served over HTTPS
    s3          any S3 compatible bucket (AWS S3, Cloudflare R2,
                Backblaze B2, MinIO, ...) via boto3
    template    an already published URL pattern, useful for tests

Adding Azure Blob or another CDN means writing one subclass of
VideoStorage and registering it in the factory below.
"""
import logging
import mimetypes
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from ..common.env import env_bool, env_str
from .errors import MetaConfigurationError, MetaStorageError
from .http_client import register_secret

log = logging.getLogger("pompom_meta.storage")


class VideoStorage(ABC):
    """Turns a local video file into a publicly reachable HTTPS URL."""

    name = "abstract"
    #: True when the backend can actually produce a URL.
    can_host = True

    @abstractmethod
    def upload(self, video_path: Path, *, content_id: str | None = None) -> str:
        """Publish the file and return an HTTPS URL Meta can download."""

    def cleanup(self, video_url: str) -> None:
        """Remove the temporary copy. Best effort; never raises."""
        return None

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<{type(self).__name__} name={self.name!r}>"


class NullStorage(VideoStorage):
    """No hosting available.

    Facebook still works through the resumable byte upload; Instagram
    requires a URL, so it is skipped with a clear reason.
    """

    name = "none"
    can_host = False

    def upload(self, video_path: Path, *, content_id: str | None = None) -> str:
        raise MetaStorageError(
            "No public video storage is configured. Set META_STORAGE_BACKEND "
            "(public_dir, s3, template) or pass an explicit video_url.")


class PublicDirectoryStorage(VideoStorage):
    """Copy the file into a directory that is already served over HTTPS.

    Useful when the machine or a mounted volume sits behind nginx,
    Caddy, or a static site host.

    Environment:
        META_STORAGE_DIR        local directory to copy into
        META_STORAGE_BASE_URL   HTTPS prefix that maps to that directory
        META_STORAGE_CLEANUP    delete the copy after publishing (default true)
    """

    name = "public_dir"

    def __init__(self, directory: Path, base_url: str, cleanup_after: bool = True):
        self.directory = directory
        self.base_url = base_url.rstrip("/")
        self.cleanup_after = cleanup_after
        self._published: dict[str, Path] = {}

    def upload(self, video_path: Path, *, content_id: str | None = None) -> str:
        if not video_path.exists():
            raise MetaStorageError(f"Video not found: {video_path}")
        self.directory.mkdir(parents=True, exist_ok=True)
        object_name = _object_name(video_path, content_id)
        target = self.directory / object_name
        shutil.copy2(video_path, target)
        url = f"{self.base_url}/{object_name}"
        self._published[url] = target
        log.info("Uploading video... hosted at %s", url)
        return url

    def cleanup(self, video_url: str) -> None:
        target = self._published.pop(video_url, None)
        if target is None or not self.cleanup_after:
            return
        try:
            target.unlink(missing_ok=True)
            log.info("Temporary hosted copy removed: %s", target.name)
        except OSError as exc:
            log.warning("Could not remove hosted copy %s: %s", target.name, exc)


class S3CompatibleStorage(VideoStorage):
    """Upload to any S3 compatible object store.

    Works with AWS S3, Cloudflare R2, Backblaze B2, MinIO and similar by
    pointing META_S3_ENDPOINT_URL at the provider.

    Environment:
        META_S3_BUCKET            bucket name (required)
        META_S3_ENDPOINT_URL      custom endpoint, e.g. Cloudflare R2
        META_S3_REGION            region name
        META_S3_KEY_PREFIX        key prefix, default "meta-reels"
        META_S3_PUBLIC_BASE_URL   public HTTPS prefix, e.g. a CDN domain
        META_S3_PRESIGN_SECONDS   presign instead of a public prefix
        META_S3_ACCESS_KEY_ID     falls back to AWS_ACCESS_KEY_ID
        META_S3_SECRET_ACCESS_KEY falls back to AWS_SECRET_ACCESS_KEY
        META_STORAGE_CLEANUP      delete the object after publishing
    """

    name = "s3"

    def __init__(self, bucket: str, *, endpoint_url: str = "", region: str = "",
                 key_prefix: str = "meta-reels", public_base_url: str = "",
                 presign_seconds: int = 0, access_key_id: str = "",
                 secret_access_key: str = "", cleanup_after: bool = True):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.region = region
        self.key_prefix = key_prefix.strip("/")
        self.public_base_url = public_base_url.rstrip("/")
        self.presign_seconds = presign_seconds
        self.cleanup_after = cleanup_after
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._keys: dict[str, str] = {}
        self._client = None

    def _boto_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3  # noqa: PLC0415 - optional dependency
        except ImportError as exc:
            raise MetaStorageError(
                "META_STORAGE_BACKEND=s3 requires boto3. "
                "Install it with: pip install boto3") from exc
        kwargs = {}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        if self.region:
            kwargs["region_name"] = self.region
        if self._access_key_id and self._secret_access_key:
            kwargs["aws_access_key_id"] = self._access_key_id
            kwargs["aws_secret_access_key"] = self._secret_access_key
        self._client = boto3.client("s3", **kwargs)
        return self._client

    def upload(self, video_path: Path, *, content_id: str | None = None) -> str:
        if not video_path.exists():
            raise MetaStorageError(f"Video not found: {video_path}")
        client = self._boto_client()
        object_name = _object_name(video_path, content_id)
        key = f"{self.key_prefix}/{object_name}" if self.key_prefix else object_name
        content_type = mimetypes.guess_type(video_path.name)[0] or "video/mp4"

        log.info("Uploading video... s3://%s/%s", self.bucket, key)
        try:
            with open(video_path, "rb") as handle:
                client.upload_fileobj(
                    handle, self.bucket, key,
                    ExtraArgs={"ContentType": content_type},
                )
        except Exception as exc:  # boto3 raises provider specific errors
            raise MetaStorageError(f"S3 upload failed: {exc}") from exc

        if self.public_base_url:
            url = f"{self.public_base_url}/{key}"
        elif self.presign_seconds > 0:
            try:
                url = client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=self.presign_seconds,
                )
            except Exception as exc:
                raise MetaStorageError(f"Could not presign S3 object: {exc}") from exc
        else:
            raise MetaStorageError(
                "Set META_S3_PUBLIC_BASE_URL or META_S3_PRESIGN_SECONDS so Meta "
                "can download the uploaded object.")

        self._keys[url] = key
        log.info("Video hosted for Meta ingestion (key=%s)", key)
        return url

    def cleanup(self, video_url: str) -> None:
        key = self._keys.pop(video_url, None)
        if key is None or not self.cleanup_after:
            return
        try:
            self._boto_client().delete_object(Bucket=self.bucket, Key=key)
            log.info("Temporary object removed: %s", key)
        except Exception as exc:
            log.warning("Could not remove temporary object %s: %s", key, exc)


class UrlTemplateStorage(VideoStorage):
    """Assume the file is already reachable at a predictable URL.

    Environment:
        META_STORAGE_URL_TEMPLATE  e.g. https://cdn.pompomhills.com/reels/{filename}

    Supported placeholders: {filename}, {stem}, {content_id}.
    """

    name = "template"

    def __init__(self, template: str):
        self.template = template

    def upload(self, video_path: Path, *, content_id: str | None = None) -> str:
        url = self.template.format(
            filename=video_path.name,
            stem=video_path.stem,
            content_id=content_id or video_path.stem,
        )
        log.info("Using pre-hosted video URL: %s", url)
        return url


def _object_name(video_path: Path, content_id: str | None) -> str:
    """Collision free, URL safe object name for a temporary upload."""
    suffix = video_path.suffix or ".mp4"
    slug = "".join(
        ch if ch.isalnum() or ch in "-_" else "-"
        for ch in (content_id or video_path.stem)
    ).strip("-").lower() or "video"
    return f"{slug}-{uuid.uuid4().hex[:12]}{suffix}"


def create_storage(backend: str | None = None) -> VideoStorage:
    """Build the storage backend named by META_STORAGE_BACKEND."""
    name = (backend or env_str("META_STORAGE_BACKEND", "none")).lower() or "none"
    cleanup_after = env_bool("META_STORAGE_CLEANUP", True)

    if name in ("none", "off", "disabled"):
        return NullStorage()

    if name in ("public_dir", "dir", "local"):
        directory = env_str("META_STORAGE_DIR")
        base_url = env_str("META_STORAGE_BASE_URL")
        if not directory or not base_url:
            raise MetaConfigurationError(
                "META_STORAGE_BACKEND=public_dir requires META_STORAGE_DIR "
                "and META_STORAGE_BASE_URL")
        return PublicDirectoryStorage(Path(directory), base_url, cleanup_after)

    if name in ("s3", "r2", "minio", "b2"):
        bucket = env_str("META_S3_BUCKET")
        if not bucket:
            raise MetaConfigurationError(
                "META_STORAGE_BACKEND=s3 requires META_S3_BUCKET")
        secret_key = env_str("META_S3_SECRET_ACCESS_KEY") or env_str("AWS_SECRET_ACCESS_KEY")
        register_secret(secret_key)
        return S3CompatibleStorage(
            bucket,
            endpoint_url=env_str("META_S3_ENDPOINT_URL"),
            region=env_str("META_S3_REGION"),
            key_prefix=env_str("META_S3_KEY_PREFIX", "meta-reels"),
            public_base_url=env_str("META_S3_PUBLIC_BASE_URL"),
            presign_seconds=int(env_str("META_S3_PRESIGN_SECONDS", "0") or 0),
            access_key_id=env_str("META_S3_ACCESS_KEY_ID") or env_str("AWS_ACCESS_KEY_ID"),
            secret_access_key=secret_key,
            cleanup_after=cleanup_after,
        )

    if name in ("template", "url"):
        template = env_str("META_STORAGE_URL_TEMPLATE")
        if not template:
            raise MetaConfigurationError(
                "META_STORAGE_BACKEND=template requires META_STORAGE_URL_TEMPLATE")
        return UrlTemplateStorage(template)

    raise MetaConfigurationError(
        f"Unknown META_STORAGE_BACKEND={name!r}. "
        "Supported values: none, public_dir, s3, template.")
