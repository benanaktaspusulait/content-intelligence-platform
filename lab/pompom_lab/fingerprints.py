from __future__ import annotations

import json
from typing import Any

from .database import Database

FEATURE_VERSION = "creative-fingerprint-v1"


def build(database: Database, video_id: str, force: bool = False) -> dict[str, Any]:
    detail = database.detail(video_id)
    if not detail:
        raise KeyError(video_id)
    scores = detail["analysis"]["scores"]
    duration = float(detail["duration"])
    dead_time = sum(float(item["end"]) - float(item["start"]) for item in detail["analysis"].get("dead_time", []))
    features = {
        "hook_anomaly": float(scores.get("first_frame_hook", 0)) / 10,
        "character_goal": float(scores.get("character_goal", 0)) / 10,
        "physical_action": float(scores.get("physical_action", 0)) / 10,
        "problem_resistance": float(scores.get("problem_resistance", 0)) / 10,
        "escalation": float(scores.get("escalation", 0)) / 10,
        "final_twist": float(scores.get("final_twist", 0)) / 10,
        "loopability": float(scores.get("loopability", 0)) / 10,
        "rule_clarity": float(scores.get("rule_clarity", 0)) / 10,
        "dead_time_seconds": round(dead_time, 3),
        "dead_time_ratio": round(dead_time / duration, 4) if duration else 0,
        "duration_seconds": duration,
        "dialogue_dependency": None,
        "cta_interruption": None,
        "mystery": None,
        "cute_emotion": None,
        "visual_search": None,
        "world_curiosity": None,
        "character_interaction": None,
    }
    quality = float(detail["action_dna"])
    evidence = {"analysis_id": detail["analysis_id"], "provider": detail["analysis"].get("provider"), "unmeasured_features": [key for key, value in features.items() if value is None]}
    with database.connect() as connection:
        if force:
            connection.execute("DELETE FROM creative_fingerprints WHERE video_id=? AND feature_version=?", (video_id, FEATURE_VERSION))
        connection.execute(
            """INSERT OR IGNORE INTO creative_fingerprints(video_id,feature_version,source_analysis_id,creative_quality_score,
            features_json,evidence_json,confidence) VALUES(?,?,?,?,?,?,?)""",
            (video_id, FEATURE_VERSION, detail["analysis_id"], quality, json.dumps(features), json.dumps(evidence), float(detail["confidence"])),
        )
        row = connection.execute("SELECT * FROM creative_fingerprints WHERE video_id=? AND feature_version=?", (video_id, FEATURE_VERSION)).fetchone()
    result = dict(row)
    result["features"] = json.loads(result.pop("features_json"))
    result["evidence"] = json.loads(result.pop("evidence_json"))
    return result


def build_all(database: Database, force: bool = False) -> list[dict[str, Any]]:
    return [build(database, row["id"], force) for row in database.list_videos()]

