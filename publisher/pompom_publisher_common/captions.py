"""
captions.py — Read a caption out of an existing markdown document.

Extracts a specific section from markdown files so captions are never
duplicated or retyped in code.
"""
import logging
from pathlib import Path

log = logging.getLogger("pompom_publisher_common.captions")

DEFAULT_SECTION = "Instagram Caption"


def extract_markdown_section(markdown_path: Path | str,
                             section: str = DEFAULT_SECTION) -> str:
    """Return the body of a markdown heading, trimmed of blank edges.

    Matching is case insensitive and ignores the leading `#` characters,
    so "## Instagram Caption" and "### instagram caption" both work. The
    section ends at the next heading of the same or a higher level.

    Raises:
        FileNotFoundError: the document does not exist.
        ValueError: the section is missing or empty.
    """
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"Caption source not found: {path}")

    wanted = section.lstrip("#").strip().lower()
    lines = path.read_text(encoding="utf-8").splitlines()

    start = None
    start_level = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        title = stripped.lstrip("#").strip().lower()
        if title == wanted:
            start = index + 1
            start_level = level
            break

    if start is None:
        raise ValueError(f"Section '{section}' not found in {path}")

    body: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= start_level:
                break
        body.append(line.rstrip())

    caption = "\n".join(body).strip("\n").strip()
    if not caption:
        raise ValueError(f"Section '{section}' in {path} is empty")
    log.info("Caption loaded from %s (%s characters)", path, len(caption))
    return caption


def read_caption(source: Path | str, section: str = DEFAULT_SECTION) -> str:
    """Read a caption from a markdown section or from a plain text file."""
    path = Path(source)
    if path.suffix.lower() in (".md", ".markdown"):
        return extract_markdown_section(path, section)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Caption file is empty: {path}")
    return text
