"""
ledger.py — SQLite publication ledger.

Guarantees a piece of content is never published twice to the same
platform, and keeps a small audit trail of every attempt:

    content_id | platform | media_id | permalink | published_at | status

Status values: SUCCESS, FAILED, DRY_RUN, SKIPPED.
"""
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("pompom_publisher_common.ledger")

SCHEMA = """
CREATE TABLE IF NOT EXISTS publications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id   TEXT    NOT NULL,
    platform     TEXT    NOT NULL,
    media_id     TEXT,
    permalink    TEXT,
    published_at TEXT    NOT NULL,
    status       TEXT    NOT NULL,
    detail       TEXT
);
CREATE INDEX IF NOT EXISTS idx_publications_lookup
    ON publications (content_id, platform, status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_publications_success
    ON publications (content_id, platform)
    WHERE status = 'SUCCESS';
"""


@dataclass
class PublicationRecord:
    content_id: str
    platform: str
    media_id: str | None
    permalink: str | None
    published_at: str
    status: str
    detail: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PublishLedger:
    """Small SQLite wrapper; safe to construct per run."""

    def __init__(self, db_path: Path = Path("data/publish_log.db")):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def already_published(self, content_id: str, platform: str) -> PublicationRecord | None:
        """Return the successful record when this content was already posted."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM publications "
                "WHERE content_id = ? AND platform = ? AND status = 'SUCCESS' "
                "ORDER BY id DESC LIMIT 1",
                (content_id, platform),
            ).fetchone()
        if row is None:
            return None
        return PublicationRecord(
            content_id=row["content_id"],
            platform=row["platform"],
            media_id=row["media_id"],
            permalink=row["permalink"],
            published_at=row["published_at"],
            status=row["status"],
            detail=row["detail"],
        )

    def record(self, content_id: str, platform: str, status: str, *,
               media_id: str | None = None, permalink: str | None = None,
               detail: str | None = None) -> None:
        """Append an attempt. A duplicate SUCCESS row is ignored."""
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO publications "
                    "(content_id, platform, media_id, permalink, published_at, status, detail) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (content_id, platform, media_id, permalink, utc_now(), status, detail),
                )
            except sqlite3.IntegrityError:
                log.warning(
                    "Ledger already holds a SUCCESS row for %s on %s",
                    content_id, platform)

    def history(self, content_id: str | None = None, limit: int = 50) -> list[PublicationRecord]:
        query = "SELECT * FROM publications"
        params: tuple = ()
        if content_id:
            query += " WHERE content_id = ?"
            params = (content_id,)
        query += " ORDER BY id DESC LIMIT ?"
        params = (*params, limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            PublicationRecord(
                content_id=row["content_id"],
                platform=row["platform"],
                media_id=row["media_id"],
                permalink=row["permalink"],
                published_at=row["published_at"],
                status=row["status"],
                detail=row["detail"],
            )
            for row in rows
        ]
