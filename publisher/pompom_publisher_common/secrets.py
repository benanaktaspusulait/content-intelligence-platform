"""Shared secret registration and log scrubbing."""

_SECRETS: set[str] = set()


def register_secret(value: str | None) -> None:
    """Remember a value that must never appear in a log line."""
    if value and len(value) >= 8:
        _SECRETS.add(value)


def scrub(text: str | None) -> str:
    """Replace every registered secret with a placeholder."""
    if not text:
        return ""
    cleaned = text
    for secret in _SECRETS:
        cleaned = cleaned.replace(secret, "<redacted>")
    return cleaned
