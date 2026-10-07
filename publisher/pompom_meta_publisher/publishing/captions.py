"""Backward-compatible re-export of neutral caption readers."""

from pompom_publisher_common.captions import (
    DEFAULT_SECTION,
    extract_markdown_section,
    read_caption,
)

__all__ = ["DEFAULT_SECTION", "extract_markdown_section", "read_caption"]
