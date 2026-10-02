from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .database import Database

CHECKPOINTS = (15, 30, 60, 120, 180, 360, 720, 1440, 2880, 10080)


def performance_band(value: float | None) -> str | None:
    if value is None:
        return None
    if value < 500:
        return "LOW"
    if value < 2_000:
        return "PARTIAL"
    if value < 5_000:
        return "MEANINGFUL"
    if value < 20_000:
        return "STRONG"
    if value < 50_000:
        return "PERSISTENT"
    return "BREAKOUT"


def trajectory_label(points: list[tuple[int, float]]) -> str:
    if len(points) < 2:
        return "UNKNOWN"
    velocities = [(b[1] - a[1]) / max(1, b[0] - a[0]) for a, b in zip(points, points[1:])]
    peak = max(velocities)
    last = velocities[-1]
    if points[-1][1] < 500 and last <= max(0.1, peak * 0.25):
        return "EARLY_STALL"
    waves = sum(velocities[index] > velocities[index - 1] * 1.5 for index in range(1, len(velocities)))
    if waves >= 2:
        return "MULTI_WAVE"
    if waves == 1:
        return "SECOND_WAVE"
    if last > 0 and last >= peak * 0.7:
        return "PERSISTENT_GROWTH"
    if len(points) >= 3 and velocities[-1] > velocities[0] * 2:
        return "LATE_BREAKOUT"
    return "SLOW_GROWTH"


def _as_dt(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def _effective_observations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda row: row.get("measurement_timestamp_utc") or row.get("measurement_date") or "")
    cumulative: dict[str, float] = {}
    output: list[dict[str, Any]] = []
    for row in rows:
        current = dict(row)
        semantics = row["metric_semantics"]
        for metric in ("views", "reach", "likes", "comments", "shares", "saves", "follows"):
            value = row.get(metric)
            if value is None:
                current[metric] = cumulative.get(metric)
            elif semantics == "DAILY_INCREMENT":
                cumulative[metric] = cumulative.get(metric, 0) + float(value)
                current[metric] = cumulative[metric]
            else:
                cumulative[metric] = float(value)
                current[metric] = float(value)
        output.append(current)
    return output


def rebuild(database: Database) -> dict[str, int]:
    rebuilt = skipped = 0
    with database.connect() as connection:
        groups = connection.execute(
            "SELECT DISTINCT video_id,platform FROM normalised_performance WHERE video_id IS NOT NULL AND is_paid=0"
        ).fetchall()
        for group in groups:
            rows = [dict(row) for row in connection.execute(
                "SELECT * FROM normalised_performance WHERE video_id=? AND platform=? AND is_paid=0 ORDER BY COALESCE(measurement_timestamp_utc,measurement_date)",
                (group["video_id"], group["platform"]),
            )]
            publication = next((_as_dt(row.get("publication_timestamp_utc")) for row in rows if row.get("publication_timestamp_utc")), None)
            timed = [(row, _as_dt(row.get("measurement_timestamp_utc"))) for row in _effective_observations(rows)]
            timed = [(row, stamp) for row, stamp in timed if stamp]
            if not publication or not timed:
                skipped += 1
                continue
            connection.execute("DELETE FROM performance_trajectories WHERE video_id=? AND platform=?", (group["video_id"], group["platform"]))
            selected: list[tuple[int, dict[str, Any]]] = []
            for checkpoint in CHECKPOINTS:
                eligible = [(row, stamp) for row, stamp in timed if 0 <= (stamp - publication).total_seconds() / 60 <= checkpoint]
                if eligible:
                    selected.append((checkpoint, eligible[-1][0]))
            points = [(checkpoint, float(row["views"])) for checkpoint, row in selected if row.get("views") is not None]
            label = trajectory_label(points)
            previous_views = previous_velocity = None
            previous_checkpoint = 0
            for checkpoint, row in selected:
                views = row.get("views")
                reach = row.get("reach")
                hours = max(checkpoint / 60, 0.25)
                velocity = None if views is None else (float(views) - (previous_views or 0)) / max((checkpoint - previous_checkpoint) / 60, 0.25)
                acceleration = None if velocity is None or previous_velocity is None else velocity - previous_velocity
                connection.execute(
                    """INSERT INTO performance_trajectories(video_id,variant_id,platform,checkpoint_minutes,measurement_timestamp_utc,
                    views,reach,likes,comments,shares,saves,follows,average_watch_seconds,views_per_hour,reach_per_hour,acceleration,
                    follows_per_1000_views,shares_per_1000_views,performance_band,trajectory_label,source_observation_ids_json)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (group["video_id"], row.get("variant_id"), group["platform"], checkpoint, row.get("measurement_timestamp_utc"),
                     views, reach, row.get("likes"), row.get("comments"), row.get("shares"), row.get("saves"), row.get("follows"),
                     row.get("average_watch_seconds"), velocity, None if reach is None else float(reach) / hours, acceleration,
                     None if not views else 1000 * float(row.get("follows") or 0) / float(views),
                     None if not views else 1000 * float(row.get("shares") or 0) / float(views),
                     performance_band(views), label, json.dumps([row["id"]])),
                )
                previous_views, previous_velocity, previous_checkpoint = views, velocity, checkpoint
                rebuilt += 1
    return {"rebuilt": rebuilt, "skipped_groups": skipped}


def summary(database: Database) -> list[dict[str, Any]]:
    with database.connect() as connection:
        return [dict(row) for row in connection.execute(
            """SELECT video_id,platform,MAX(checkpoint_minutes) latest_checkpoint,MAX(views) views,
            MAX(reach) reach,MAX(trajectory_label) trajectory_label FROM performance_trajectories
            GROUP BY video_id,platform ORDER BY MAX(views) DESC"""
        )]
