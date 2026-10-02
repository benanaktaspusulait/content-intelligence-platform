from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .database import Database


def create_challenger(database: Database, platform: str, as_of: str | None = None) -> dict[str, Any]:
    cutoff = as_of or datetime.now(timezone.utc).isoformat()
    with database.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            """SELECT t.video_id,t.checkpoint_minutes,t.views,t.trajectory_label,f.feature_version,f.features_json
            FROM performance_trajectories t JOIN creative_fingerprints f ON f.video_id=t.video_id
            WHERE t.platform=? AND t.rebuilt_at<=? ORDER BY t.video_id,t.checkpoint_minutes""", (platform, cutoff)
        )]
        serialised = json.dumps(rows, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialised.encode()).hexdigest()
        dataset_version = f"{platform}-{cutoff[:10]}-{digest[:8]}"
        cursor = connection.execute(
            "INSERT INTO dataset_snapshots(version,as_of,platform,row_count,query_json,content_hash) VALUES(?,?,?,?,?,?)",
            (dataset_version, cutoff, platform, len(rows), json.dumps({"table": "performance_trajectories", "cutoff": cutoff}), digest),
        )
        dataset_id = int(cursor.lastrowid)
        unique_videos = len({row["video_id"] for row in rows})
        validation = {
            "strategy": "walk-forward-required", "available_videos": unique_videos,
            "promotion_eligible": False, "reason": "Explicit backtest and human promotion required",
        }
        version = f"empirical-challenger-{platform}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        model_cursor = connection.execute(
            """INSERT INTO model_versions(version,platform,algorithm,feature_version,dataset_snapshot_id,status,parameters_json,validation_json)
            VALUES(?,?,?,?,?,'CHALLENGER',?,?)""",
            (version, platform, "regularised-empirical-baseline", "creative-fingerprint-v1", dataset_id,
             json.dumps({"prior_strength": 8, "minimum_promotion_samples": 30}), json.dumps(validation)),
        )
    return {"model_id": int(model_cursor.lastrowid), "version": version, "dataset_version": dataset_version, **validation}


def models(database: Database) -> list[dict[str, Any]]:
    with database.connect() as connection:
        return [dict(row) for row in connection.execute(
            """SELECT m.*,d.version dataset_version,d.row_count,d.as_of FROM model_versions m
            LEFT JOIN dataset_snapshots d ON d.id=m.dataset_snapshot_id ORDER BY m.created_at DESC"""
        )]


def promote(database: Database, model_id: int) -> None:
    with database.connect() as connection:
        model = connection.execute("SELECT * FROM model_versions WHERE id=?", (model_id,)).fetchone()
        if not model:
            raise KeyError(model_id)
        validation = json.loads(model["validation_json"])
        if not validation.get("promotion_eligible"):
            raise ValueError("Challenger is not promotion-eligible; complete backtest and validation first")
        connection.execute("UPDATE model_versions SET status='RETIRED' WHERE platform=? AND status='CHAMPION'", (model["platform"],))
        connection.execute("UPDATE model_versions SET status='CHAMPION',promoted_at=CURRENT_TIMESTAMP WHERE id=?", (model_id,))

