"""
config.py — Environment driven configuration for Meta publishing.

Nothing is hard-coded: every id, token, and toggle comes from the process
environment or from the project `.env` file. Tokens are registered with the
HTTP layer so they can never be written to a log line.
"""
import logging
from dataclasses import dataclass
from pathlib import Path

from pompom_publisher_common.env import (
    DEFAULT_ENV_PATH,
    EnvError,
    env_bool,
    env_float,
    env_int,
    env_str,
    load_env_file,
)
from pompom_publisher_common.retry import RetryPolicy
from .errors import MetaConfigurationError
from .http_client import register_secret

log = logging.getLogger("pompom_meta.config")

# Latest published Graph API version at the time of writing. Override with
# META_API_VERSION when Meta promotes a newer one.
DEFAULT_API_VERSION = "v26.0"

GRAPH_HOST = "https://graph.facebook.com"
RUPLOAD_HOST = "https://rupload.facebook.com"

# Environment helpers live in pompom_publisher_common.env and remain available
# from the old Meta path through a compatibility re-export.
__all__ = [
    "DEFAULT_API_VERSION",
    "DEFAULT_ENV_PATH",
    "GRAPH_HOST",
    "MetaConfig",
    "RUPLOAD_HOST",
    "env_bool",
    "env_float",
    "env_int",
    "env_str",
    "load_env_file",
    "load_meta_config",
]


@dataclass
class MetaConfig:
    """Resolved Meta publishing settings."""

    access_token: str = ""
    page_id: str = ""
    instagram_account_id: str = ""
    api_version: str = DEFAULT_API_VERSION

    # Overridable so the flow can be exercised against a local stub.
    graph_host: str = GRAPH_HOST
    rupload_host: str = RUPLOAD_HOST

    enable_facebook: bool = False
    enable_instagram: bool = False
    dry_run: bool = True

    # Optional per-platform tokens. A Page Access Token is required for
    # Facebook Reels; Instagram accepts the same Page token when the
    # professional account is linked to that Page.
    page_access_token: str = ""
    instagram_access_token: str = ""

    poll_timeout: int = 300
    poll_interval: int = 5
    request_timeout: float = 120.0
    upload_timeout: float = 600.0
    max_attempts: int = 5

    instagram_share_to_feed: bool = True
    facebook_reel_title: str = ""

    ledger_path: Path = Path("data/publish_log.db")

    # ── Derived helpers ────────────────────────────────────────────────────

    @property
    def graph_base(self) -> str:
        return f"{self.graph_host.rstrip('/')}/{self.api_version}"

    @property
    def rupload_base(self) -> str:
        return f"{self.rupload_host.rstrip('/')}/video-upload/{self.api_version}"

    @property
    def retry_policy(self) -> RetryPolicy:
        return RetryPolicy(max_attempts=self.max_attempts)

    def facebook_token(self) -> str:
        return self.page_access_token or self.access_token

    def instagram_token(self) -> str:
        return self.instagram_access_token or self.page_access_token or self.access_token

    def facebook_ready(self) -> tuple[bool, str]:
        """Return (usable, reason) for the Facebook target."""
        if not self.enable_facebook:
            return False, "META_ENABLE_FACEBOOK is disabled"
        if not self.page_id:
            return False, "META_PAGE_ID is not set"
        if not self.facebook_token():
            return False, "META_PAGE_ACCESS_TOKEN / META_ACCESS_TOKEN is not set"
        return True, ""

    def instagram_ready(self) -> tuple[bool, str]:
        """Return (usable, reason) for the Instagram target."""
        if not self.enable_instagram:
            return False, "META_ENABLE_INSTAGRAM is disabled"
        if not self.instagram_account_id:
            return False, "META_INSTAGRAM_ACCOUNT_ID is not set"
        if not self.instagram_token():
            return False, "META_ACCESS_TOKEN is not set"
        return True, ""

    @property
    def any_target_enabled(self) -> bool:
        return self.facebook_ready()[0] or self.instagram_ready()[0]


def load_meta_config(env_path: Path = DEFAULT_ENV_PATH) -> MetaConfig:
    """Build a MetaConfig from the environment and the project .env file."""
    load_env_file(env_path)
    try:
        return _build_meta_config()
    except EnvError as exc:
        raise MetaConfigurationError(str(exc)) from exc


def _build_meta_config() -> MetaConfig:
    version = env_str("META_API_VERSION", DEFAULT_API_VERSION)
    if version and not version.startswith("v"):
        version = f"v{version}"

    config = MetaConfig(
        access_token=env_str("META_ACCESS_TOKEN"),
        page_id=env_str("META_PAGE_ID"),
        instagram_account_id=env_str("META_INSTAGRAM_ACCOUNT_ID"),
        api_version=version or DEFAULT_API_VERSION,
        graph_host=env_str("META_GRAPH_HOST", GRAPH_HOST),
        rupload_host=env_str("META_RUPLOAD_HOST", RUPLOAD_HOST),
        enable_facebook=env_bool("META_ENABLE_FACEBOOK", False),
        enable_instagram=env_bool("META_ENABLE_INSTAGRAM", False),
        dry_run=env_bool("META_DRY_RUN", True),
        page_access_token=env_str("META_PAGE_ACCESS_TOKEN"),
        instagram_access_token=env_str("META_INSTAGRAM_ACCESS_TOKEN"),
        poll_timeout=env_int("META_POLL_TIMEOUT", 300),
        poll_interval=env_int("META_POLL_INTERVAL", 5),
        request_timeout=env_float("META_REQUEST_TIMEOUT", 120.0),
        upload_timeout=env_float("META_UPLOAD_TIMEOUT", 600.0),
        max_attempts=env_int("META_MAX_ATTEMPTS", 5),
        instagram_share_to_feed=env_bool("META_IG_SHARE_TO_FEED", True),
        facebook_reel_title=env_str("META_FACEBOOK_REEL_TITLE"),
        ledger_path=Path(env_str("META_PUBLISH_DB", "data/publish_log.db")),
    )

    for token in (config.access_token, config.page_access_token,
                  config.instagram_access_token):
        register_secret(token)

    if config.poll_interval < 1:
        raise MetaConfigurationError("META_POLL_INTERVAL must be at least 1 second")
    if config.poll_timeout < config.poll_interval:
        raise MetaConfigurationError(
            "META_POLL_TIMEOUT must be greater than META_POLL_INTERVAL")

    return config
