"""
env.py — dotenv loading and typed environment readers.

Single implementation for environment variable management. Real process
environment variables always win over `.env`, so a CI or cron override
never gets silently replaced by a file value.
"""
import os
from pathlib import Path

DEFAULT_ENV_PATH = Path(".env")

_TRUE_VALUES = {"1", "true", "yes", "on", "y"}
_FALSE_VALUES = {"0", "false", "no", "off", "n", ""}


class EnvError(ValueError):
    """An environment variable holds a value of the wrong type."""


def load_env_file(env_path: Path = DEFAULT_ENV_PATH) -> None:
    """Populate os.environ from a dotenv file without overriding real vars."""
    path = Path(env_path)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise EnvError(f"{name} must be a boolean value, got {raw!r}")


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise EnvError(f"{name} must be an integer, got {raw!r}") from exc


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise EnvError(f"{name} must be a number, got {raw!r}") from exc


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma separated list, lowercased and stripped of blanks."""
    raw = os.environ.get(name)
    value = raw if raw is not None else default
    return [item.strip().lower() for item in value.split(",") if item.strip()]
