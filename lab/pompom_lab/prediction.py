from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from typing import Any

from .database import Database
from .fingerprints import FEATURE_VERSION, build as build_fingerprint
from .trajectory import CHECKPOINTS, performance_band

BANDS = ("LOW", "PARTIAL", "MEANINGFUL", "STRONG", "PERSISTENT", "BREAKOUT")
TRAJECTORIES = ("EARLY_STALL", "SLOW_GROWTH", "SECOND_WAVE", "MULTI_WAVE", "PERSISTENT_GROWTH", "LATE_BREAKOUT")


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def _historical(database: Database, platform: str, horizon: int, cutoff: str) -> list[dict[str, Any]]:
    with database.connect() as connection:
        return [dict(row) for row in connection.execute(
            """SELECT t.*,f.features_json,f.creative_quality_score FROM performance_trajectories t
            LEFT JOIN creative_fingerprints f ON f.video_id=t.video_id AND f.feature_version=?
            WHERE t.platform=? AND t.checkpoint_minutes=? AND t.views IS NOT NULL
            AND EXISTS (
              SELECT 1 FROM json_each(t.source_observation_ids_json) source
              JOIN normalised_performance np ON np.id=source.value
              JOIN performance_imports pi ON pi.id=np.source_import_id
              WHERE pi.imported_at<=? AND COALESCE(np.measurement_timestamp_utc,np.publication_timestamp_utc,pi.imported_at)<=?
            )""",
            (FEATURE_VERSION, platform, horizon, cutoff, cutoff),
        )]


def _band_probabilities(values: list[float]) -> dict[str, float]:
    counts = {band: 1.0 for band in BANDS}
    for value in values:
        counts[performance_band(value) or "LOW"] += 1
    total = sum(counts.values())
    return {band: counts[band] / total for band in BANDS}


def _trajectory_probabilities(rows: list[dict[str, Any]]) -> dict[str, float]:
    counts = {label: 1.0 for label in TRAJECTORIES}
    for row in rows:
        if row.get("trajectory_label") in counts:
            counts[row["trajectory_label"]] += 1
    total = sum(counts.values())
    return {label: counts[label] / total for label in TRAJECTORIES}


def create_prediction(database: Database, video_id: str, platform: str, planned_publish_time: str | None = None,
                      mode: str = "PRE_PUBLISH", knowledge_cutoff: str | None = None, lock: bool = False) -> dict[str, Any]:
    if mode not in {"PRE_PUBLISH", "EARLY_LIVE"}:
        raise ValueError(mode)
    cutoff = knowledge_cutoff or datetime.now(timezone.utc).isoformat()
    fingerprint = build_fingerprint(database, video_id)
    targets: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for horizon in CHECKPOINTS[1:]:
        rows = _historical(database, platform, horizon, cutoff)
        all_rows.extend(rows)
        values = [float(row["views"]) for row in rows]
        expected = statistics.median(values) if values else None
        target = {
            "horizon_minutes": horizon,
            "expected_value": expected,
            "interval_50_low": _quantile(values, .25) if values else None,
            "interval_50_high": _quantile(values, .75) if values else None,
            "interval_80_low": _quantile(values, .10) if values else None,
            "interval_80_high": _quantile(values, .90) if values else None,
            "bands": _band_probabilities(values),
            "trajectories": _trajectory_probabilities(rows),
        }
        targets.append(target)
    sample_size = len({row["video_id"] for row in all_rows})
    confidence = "HIGH" if sample_size >= 50 else "MEDIUM" if sample_size >= 15 else "LOW"
    fit = min(100.0, float(fingerprint["creative_quality_score"]) * (0.75 + min(sample_size, 50) / 200))
    opportunity = min(100.0, 0.65 * fit + 35 * (1 - min(sample_size, 20) / 20))
    uncertainty = []
    if sample_size < 15:
        uncertainty.append("Small platform-specific comparable sample")
    if any(value is None for value in fingerprint["features"].values()):
        uncertainty.append("Some creative fingerprint dimensions are unmeasured")
    payload = {"platform": platform, "mode": mode, "targets": targets, "notice": "Historical estimate, not a performance guarantee"}
    with database.connect() as connection:
        cursor = connection.execute(
            """INSERT INTO predictions(video_id,platform,mode,model_version,feature_version,dataset_version,planned_publish_time,
            knowledge_cutoff,creative_fingerprint_snapshot,confidence,comparable_sample_size,historical_platform_fit_score,
            learned_opportunity_score,uncertainty_reasons_json,payload_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (video_id, platform, mode, "empirical-baseline-v1", FEATURE_VERSION, f"as-of:{cutoff}", planned_publish_time,
             cutoff, json.dumps(fingerprint), confidence, sample_size, fit, opportunity, json.dumps(uncertainty), json.dumps(payload)),
        )
        prediction_id = int(cursor.lastrowid)
        for target in targets:
            connection.execute(
                """INSERT INTO prediction_targets(prediction_id,horizon_minutes,expected_value,interval_50_low,interval_50_high,
                interval_80_low,interval_80_high) VALUES(?,?,?,?,?,?,?)""",
                (prediction_id, target["horizon_minutes"], target["expected_value"], target["interval_50_low"],
                 target["interval_50_high"], target["interval_80_low"], target["interval_80_high"]),
            )
            for label, probability in target["bands"].items():
                connection.execute("INSERT INTO prediction_probabilities VALUES(?,?,?,?,?)", (prediction_id, target["horizon_minutes"], "BAND", label, probability))
            for label, probability in target["trajectories"].items():
                connection.execute("INSERT INTO prediction_probabilities VALUES(?,?,?,?,?)", (prediction_id, target["horizon_minutes"], "TRAJECTORY", label, probability))
        if lock:
            connection.execute("UPDATE predictions SET locked_at=CURRENT_TIMESTAMP,lock_note='locked at creation' WHERE id=?", (prediction_id,))
    return get_prediction(database, prediction_id)


def lock_prediction(database: Database, prediction_id: int, note: str = "confirmed for publication") -> None:
    with database.connect() as connection:
        row = connection.execute("SELECT locked_at FROM predictions WHERE id=?", (prediction_id,)).fetchone()
        if not row:
            raise KeyError(prediction_id)
        if row["locked_at"]:
            return
        connection.execute("UPDATE predictions SET locked_at=CURRENT_TIMESTAMP,lock_note=? WHERE id=?", (note, prediction_id))


def get_prediction(database: Database, prediction_id: int) -> dict[str, Any]:
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM predictions WHERE id=?", (prediction_id,)).fetchone()
        if not row:
            raise KeyError(prediction_id)
        result = dict(row)
        result["targets"] = [dict(item) for item in connection.execute("SELECT * FROM prediction_targets WHERE prediction_id=? ORDER BY horizon_minutes", (prediction_id,))]
        result["probabilities"] = [dict(item) for item in connection.execute("SELECT * FROM prediction_probabilities WHERE prediction_id=? ORDER BY horizon_minutes,probability_type,label", (prediction_id,))]
        return result


def audit(database: Database, prediction_id: int) -> dict[str, Any]:
    prediction = get_prediction(database, prediction_id)
    if not prediction["locked_at"]:
        raise ValueError("Only locked predictions can be audited")
    audited = 0
    with database.connect() as connection:
        for target in prediction["targets"]:
            actual = connection.execute(
                "SELECT * FROM performance_trajectories WHERE video_id=? AND platform=? AND checkpoint_minutes=?",
                (prediction["video_id"], prediction["platform"], target["horizon_minutes"]),
            ).fetchone()
            if not actual or actual["views"] is None:
                continue
            value = float(actual["views"])
            expected = target["expected_value"]
            probs = [dict(row) for row in connection.execute(
                "SELECT label,probability FROM prediction_probabilities WHERE prediction_id=? AND horizon_minutes=? AND probability_type='BAND'",
                (prediction_id, target["horizon_minutes"]),
            )]
            actual_band = performance_band(value)
            predicted_band = max(probs, key=lambda row: row["probability"])["label"] if probs else None
            brier = sum((float(row["probability"]) - (1.0 if row["label"] == actual_band else 0.0)) ** 2 for row in probs) / max(1, len(probs))
            connection.execute(
                """INSERT INTO prediction_audits(prediction_id,horizon_minutes,actual_value,absolute_error,absolute_log_error,
                inside_interval_50,inside_interval_80,predicted_band,actual_band,band_correct,predicted_trajectory,actual_trajectory,
                trajectory_correct,brier_score) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(prediction_id,horizon_minutes,metric) DO UPDATE SET actual_value=excluded.actual_value,
                absolute_error=excluded.absolute_error,absolute_log_error=excluded.absolute_log_error,inside_interval_50=excluded.inside_interval_50,
                inside_interval_80=excluded.inside_interval_80,predicted_band=excluded.predicted_band,actual_band=excluded.actual_band,
                band_correct=excluded.band_correct,actual_trajectory=excluded.actual_trajectory,trajectory_correct=excluded.trajectory_correct,
                brier_score=excluded.brier_score,audited_at=CURRENT_TIMESTAMP""",
                (prediction_id, target["horizon_minutes"], value, None if expected is None else abs(value - expected),
                 None if expected is None else abs(math.log1p(value) - math.log1p(expected)),
                 int(target["interval_50_low"] is not None and target["interval_50_low"] <= value <= target["interval_50_high"]),
                 int(target["interval_80_low"] is not None and target["interval_80_low"] <= value <= target["interval_80_high"]),
                 predicted_band, actual_band, int(predicted_band == actual_band), None, actual["trajectory_label"], None, brier),
            )
            audited += 1
        rows = [dict(row) for row in connection.execute("SELECT * FROM prediction_audits WHERE prediction_id=?", (prediction_id,))]
    return {"prediction_id": prediction_id, "audited_horizons": audited, "audits": rows}


def reliability(database: Database, platform: str | None = None) -> dict[str, Any]:
    where = "WHERE p.platform=?" if platform else ""
    params = (platform,) if platform else ()
    with database.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            f"SELECT a.*,p.platform,p.model_version FROM prediction_audits a JOIN predictions p ON p.id=a.prediction_id {where}", params
        )]
    errors = [row["absolute_log_error"] for row in rows if row["absolute_log_error"] is not None]
    return {
        "sample_size": len(rows),
        "median_absolute_log_error": statistics.median(errors) if errors else None,
        "interval_50_coverage": sum(row["inside_interval_50"] for row in rows) / len(rows) if rows else None,
        "interval_80_coverage": sum(row["inside_interval_80"] for row in rows) / len(rows) if rows else None,
        "band_accuracy": sum(row["band_correct"] for row in rows) / len(rows) if rows else None,
        "mean_brier_score": statistics.mean(row["brier_score"] for row in rows if row["brier_score"] is not None) if rows else None,
    }


def record_human_prediction(database: Database, video_id: str, platform: str, horizon_minutes: int,
                            expected_value: float | None, predicted_band: str | None, rationale: str | None) -> int:
    with database.connect() as connection:
        cursor = connection.execute(
            "INSERT INTO human_predictions(video_id,platform,horizon_minutes,expected_value,predicted_band,rationale) VALUES(?,?,?,?,?,?)",
            (video_id, platform, horizon_minutes, expected_value, predicted_band, rationale),
        )
        return int(cursor.lastrowid)


def backtest(database: Database, platform: str, horizon_minutes: int = 1440) -> dict[str, Any]:
    with database.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            """SELECT t.video_id,t.views,t.performance_band,np.publication_timestamp_utc
            FROM performance_trajectories t
            JOIN json_each(t.source_observation_ids_json) source
            JOIN normalised_performance np ON np.id=source.value
            WHERE t.platform=? AND t.checkpoint_minutes=? AND t.views IS NOT NULL
              AND np.publication_timestamp_utc IS NOT NULL
            GROUP BY t.video_id ORDER BY np.publication_timestamp_utc""", (platform, horizon_minutes)
        )]
    errors: list[float] = []
    band_hits = 0
    evaluated = 0
    history: list[float] = []
    for row in rows:
        if history:
            expected = statistics.median(history)
            errors.append(abs(math.log1p(float(row["views"])) - math.log1p(expected)))
            band_hits += int(performance_band(expected) == row["performance_band"])
            evaluated += 1
        history.append(float(row["views"]))
    metrics = {
        "sample_size": evaluated,
        "median_absolute_log_error": statistics.median(errors) if errors else None,
        "band_accuracy": band_hits / evaluated if evaluated else None,
        "temporal_ordering": "publication_timestamp_utc",
    }
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO model_evaluations(model_version,platform,horizon_minutes,evaluation_start,evaluation_end,
            sample_size,metrics_json,method) VALUES(?,?,?,?,?,?,?,'EXPANDING_WINDOW')""",
            ("empirical-baseline-v1", platform, horizon_minutes,
             rows[0]["publication_timestamp_utc"] if rows else None, rows[-1]["publication_timestamp_utc"] if rows else None,
             evaluated, json.dumps(metrics)),
        )
    return metrics


def research_questions(database: Database) -> dict[str, Any]:
    by_platform = {platform: reliability(database, platform) for platform in ("instagram", "facebook", "tiktok")}
    with database.connect() as connection:
        unpredictable = [dict(row) for row in connection.execute(
            """SELECT v.series,COUNT(*) n,AVG(a.absolute_log_error) mean_log_error
            FROM prediction_audits a JOIN predictions p ON p.id=a.prediction_id JOIN videos v ON v.id=p.video_id
            WHERE a.absolute_log_error IS NOT NULL GROUP BY v.series HAVING COUNT(*)>=3 ORDER BY mean_log_error DESC"""
        )]
    return {"platform_reliability": by_platform, "most_unpredictable_series": unpredictable,
            "notice": "Descriptive evidence only; empty samples remain unknown"}
