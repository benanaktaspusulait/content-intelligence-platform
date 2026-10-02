from __future__ import annotations

import json
from typing import Any

from .database import Database


def plan(database: Database, platform: str, limit: int = 10) -> dict[str, Any]:
    with database.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            """SELECT v.id,v.filename,v.series,f.creative_quality_score,f.features_json,
            COALESCE((SELECT c.status FROM video_characters vc JOIN characters c ON c.id=vc.character_id
              WHERE vc.video_id=v.id AND vc.is_primary=1 LIMIT 1),'UNASSIGNED') character_status,
            (SELECT c.name FROM video_characters vc JOIN characters c ON c.id=vc.character_id
              WHERE vc.video_id=v.id AND vc.is_primary=1 LIMIT 1) primary_character,
            EXISTS(SELECT 1 FROM performance_trajectories t WHERE t.video_id=v.id AND t.platform=?) published
            FROM videos v JOIN creative_fingerprints f ON f.video_id=v.id
            ORDER BY f.creative_quality_score DESC""", (platform,)
        )]
    candidates = [row for row in rows if not row["published"]]
    assignments = []
    slots = ["EXPLOIT"] * 6 + ["ADJACENT"] * 2 + ["EXPLORE"] * 2
    for index, row in enumerate(candidates[:limit]):
        allocation = slots[index % len(slots)]
        if row["character_status"] in {"NEW", "UNTESTED"}:
            allocation = f"{allocation} CREATIVE + NEW CHARACTER"
        assignments.append({
            "rank": index + 1, "video_id": row["id"], "filename": row["filename"], "series": row["series"],
            "creative_quality_score": row["creative_quality_score"], "primary_character": row["primary_character"],
            "character_status": row["character_status"], "allocation": allocation,
            "hypothesis": "Test platform fit while changing one declared creative or character dimension",
        })
    return {
        "platform": platform, "creative_budget": {"exploit": 0.6, "adjacent": 0.2, "explore": 0.2},
        "character_budget": {"established": 0.7, "limited_data": 0.2, "new_or_untested": 0.1},
        "assignments": assignments,
        "notice": "Planning recommendations are experiments, not performance guarantees",
    }


def create_experiment(database: Database, name: str, platform: str, hypothesis: str, design: str,
                      primary_metric: str = "views", horizon_minutes: int = 1440) -> int:
    with database.connect() as connection:
        cursor = connection.execute(
            """INSERT INTO experiments(name,platform,design,hypothesis,primary_metric,horizon_minutes,audience_overlap_risk)
            VALUES(?,?,?,?,?,?,?)""",
            (name, platform, design, hypothesis, primary_metric, horizon_minutes,
             "Avoid simultaneous duplicate uploads" if design == "DIRECT_AB" else None),
        )
        return int(cursor.lastrowid)


def list_experiments(database: Database) -> list[dict[str, Any]]:
    with database.connect() as connection:
        experiments = [dict(row) for row in connection.execute("SELECT * FROM experiments ORDER BY created_at DESC")]
        for experiment in experiments:
            experiment["arms"] = [dict(row) for row in connection.execute("SELECT * FROM experiment_arms WHERE experiment_id=?", (experiment["id"],))]
        return experiments
