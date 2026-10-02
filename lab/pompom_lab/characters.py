from __future__ import annotations

import statistics
from typing import Any

from .database import Database


def list_characters(database: Database) -> list[dict[str, Any]]:
    with database.connect() as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM characters ORDER BY name")]


def add_character(database: Database, name: str, status: str = "NEW", notes: str | None = None) -> int:
    with database.connect() as connection:
        cursor = connection.execute("INSERT INTO characters(name,status,notes) VALUES(?,?,?)", (name, status, notes))
        return int(cursor.lastrowid)


def assign(database: Database, video_id: str, character_name: str, role: str = "UNKNOWN", primary: bool = False,
           screen_time_ratio: float | None = None, action_share: float | None = None,
           speaking_share: float | None = None, reaction_intensity: float | None = None) -> None:
    with database.connect() as connection:
        character = connection.execute("SELECT id FROM characters WHERE name=? COLLATE NOCASE", (character_name,)).fetchone()
        if not character:
            raise KeyError(f"Unknown character: {character_name}")
        if not connection.execute("SELECT 1 FROM videos WHERE id=?", (video_id,)).fetchone():
            raise KeyError(f"Unknown video: {video_id}")
        if primary:
            connection.execute("UPDATE video_characters SET is_primary=0 WHERE video_id=?", (video_id,))
        connection.execute(
            """INSERT INTO video_characters(video_id,character_id,role,is_primary,screen_time_ratio,action_share,speaking_share,reaction_intensity)
            VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(video_id,character_id) DO UPDATE SET role=excluded.role,is_primary=excluded.is_primary,
            screen_time_ratio=excluded.screen_time_ratio,action_share=excluded.action_share,speaking_share=excluded.speaking_share,
            reaction_intensity=excluded.reaction_intensity,source='HUMAN',confidence=1""",
            (video_id, character["id"], role, int(primary), screen_time_ratio, action_share, speaking_share, reaction_intensity),
        )


def statistics_by_platform(database: Database, platform: str) -> list[dict[str, Any]]:
    with database.connect() as connection:
        characters = [dict(row) for row in connection.execute("SELECT * FROM characters WHERE active=1 ORDER BY name")]
        global_values = [float(row[0]) for row in connection.execute(
            "SELECT views FROM performance_trajectories WHERE platform=? AND checkpoint_minutes=1440 AND views IS NOT NULL", (platform,)
        )]
        global_mean = statistics.median(global_values) if global_values else 0.0
        output = []
        prior_strength = 8.0
        for character in characters:
            rows = [dict(row) for row in connection.execute(
                """SELECT t.* FROM performance_trajectories t JOIN video_characters vc ON vc.video_id=t.video_id
                WHERE vc.character_id=? AND t.platform=? AND t.checkpoint_minutes=1440 AND t.views IS NOT NULL""",
                (character["id"], platform),
            )]
            values = [float(row["views"]) for row in rows]
            raw = statistics.median(values) if values else None
            adjusted = (sum(values) + prior_strength * global_mean) / (len(values) + prior_strength) if values else global_mean
            follows = [1000 * float(row["follows"] or 0) / float(row["views"]) for row in rows if row["views"]]
            output.append({
                "character_id": character["id"], "name": character["name"], "status": character["status"],
                "platform": platform, "sample_size": len(values), "raw_median_24h_views": raw,
                "shrunk_24h_view_estimate": round(adjusted, 1),
                "median_follows_per_1000_views": statistics.median(follows) if follows else None,
                "rate_2k": sum(value >= 2_000 for value in values) / len(values) if values else None,
                "rate_5k": sum(value >= 5_000 for value in values) / len(values) if values else None,
                "rate_20k": sum(value >= 20_000 for value in values) / len(values) if values else None,
                "rate_50k": sum(value >= 50_000 for value in values) / len(values) if values else None,
                "confidence": "HIGH" if len(values) >= 20 else "MEDIUM" if len(values) >= 8 else "LOW",
                "notice": "Observational association; adjusted toward platform baseline for small samples",
            })
        return output


def pair_statistics(database: Database, platform: str) -> list[dict[str, Any]]:
    with database.connect() as connection:
        rows = connection.execute(
            """SELECT c1.name first_character,c2.name second_character,t.views,t.follows
            FROM video_characters v1 JOIN video_characters v2 ON v1.video_id=v2.video_id AND v1.character_id<v2.character_id
            JOIN characters c1 ON c1.id=v1.character_id JOIN characters c2 ON c2.id=v2.character_id
            JOIN performance_trajectories t ON t.video_id=v1.video_id
            WHERE t.platform=? AND t.checkpoint_minutes=1440 AND t.views IS NOT NULL""", (platform,)
        ).fetchall()
    grouped: dict[tuple[str, str], list[Any]] = {}
    for row in rows:
        grouped.setdefault((row["first_character"], row["second_character"]), []).append(row)
    return [{
        "pair": f"{pair[0]} + {pair[1]}", "sample_size": len(items),
        "median_24h_views": statistics.median(float(item["views"]) for item in items),
        "confidence": "MEDIUM" if len(items) >= 8 else "LOW",
    } for pair, items in grouped.items()]

