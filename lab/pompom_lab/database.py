from __future__ import annotations

import json
import sqlite3
import statistics
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterator

from .models import AnalysisResult, RescueResult, VideoMetadata


class Database:
    def __init__(self, path: Path, migrations_dir: Path) -> None:
        self.path = path
        self.migrations_dir = migrations_dir
        path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            applied = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            for migration in sorted(self.migrations_dir.glob("*.sql")):
                if migration.name in applied:
                    continue
                connection.executescript(migration.read_text())
                connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (migration.name,))

    def is_current(self, video_id: str, analysis_version: str, rubric_version: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM analysis_runs WHERE video_id=? AND analysis_version=? AND rubric_version=?",
                (video_id, analysis_version, rubric_version),
            ).fetchone()
        return row is not None

    def is_rescue_current(self, video_id: str, analysis_version: str, prompt_version: str = "stock-creative-rescue-v1") -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM rescue_runs WHERE video_id=? AND analysis_version=? AND prompt_version=?",
                (video_id, analysis_version, prompt_version),
            ).fetchone()
        return row is not None

    def ensure_video(self, metadata: VideoMetadata, video_id: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO videos(id,content_hash,path,filename,series,duration,fps,width,height,codec,has_audio,size_bytes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET path=excluded.path,filename=excluded.filename,
                series=excluded.series,duration=excluded.duration,fps=excluded.fps,width=excluded.width,height=excluded.height,
                codec=excluded.codec,has_audio=excluded.has_audio,size_bytes=excluded.size_bytes,updated_at=CURRENT_TIMESTAMP""",
                (video_id, metadata.content_hash, metadata.path, metadata.filename, metadata.series, metadata.duration,
                 metadata.fps, metadata.width, metadata.height, metadata.codec, int(metadata.has_audio), metadata.size_bytes),
            )

    def save_rescue(self, result: RescueResult, artifact_dir: Path, analysis_version: str) -> None:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM rescue_runs WHERE video_id=? AND analysis_version=? AND prompt_version=?",
                (result.video_id, analysis_version, result.prompt_version),
            ).fetchone()
            values = (
                result.provider, result.model, result.classification, result.classification_label,
                json.dumps(result.creative_engine, ensure_ascii=False), result.core_viewer_question,
                result.hook_score, result.ending_score, result.publishing_use, result.confidence,
                json.dumps(result.as_dict(), ensure_ascii=False), str(artifact_dir), int(result.performance_override),
            )
            if existing:
                connection.execute(
                    """UPDATE rescue_runs SET provider=?,model=?,classification=?,classification_label=?,creative_engine_json=?,
                    core_viewer_question=?,hook_score=?,ending_score=?,publishing_use=?,confidence=?,result_json=?,artifact_dir=?,
                    performance_override=?,created_at=CURRENT_TIMESTAMP WHERE id=?""", (*values, int(existing["id"])),
                )
            else:
                connection.execute(
                    """INSERT INTO rescue_runs(video_id,analysis_version,prompt_version,provider,model,classification,
                    classification_label,creative_engine_json,core_viewer_question,hook_score,ending_score,publishing_use,
                    confidence,result_json,artifact_dir,performance_override) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (result.video_id, analysis_version, result.prompt_version, *values),
                )

    def performance_for_video(self, video_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM performance_metrics WHERE video_id=? ORDER BY published_at DESC", (video_id,)
            )]

    def record_rescue_edit(self, video_id: str, variant: str, output: Path, comparison: dict[str, Any]) -> None:
        with self.connect() as connection:
            run = connection.execute("SELECT id FROM rescue_runs WHERE video_id=? ORDER BY id DESC LIMIT 1", (video_id,)).fetchone()
            if not run:
                raise KeyError(f"No rescue run for {video_id}")
            connection.execute(
                "INSERT INTO rescue_edits(video_id,rescue_run_id,variant,output_path,comparison_json) VALUES(?,?,?,?,?)",
                (video_id, int(run["id"]), variant, str(output), json.dumps(comparison)),
            )

    def save(self, result: AnalysisResult, artifact_dir: Path, analysis_version: str) -> None:
        metadata = result.metadata
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO videos(id,content_hash,path,filename,series,duration,fps,width,height,codec,has_audio,size_bytes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET path=excluded.path,filename=excluded.filename,series=excluded.series,
                   duration=excluded.duration,fps=excluded.fps,width=excluded.width,height=excluded.height,codec=excluded.codec,
                   has_audio=excluded.has_audio,size_bytes=excluded.size_bytes,updated_at=CURRENT_TIMESTAMP""",
                (result.video_id, metadata.content_hash, metadata.path, metadata.filename, metadata.series, metadata.duration,
                 metadata.fps, metadata.width, metadata.height, metadata.codec, int(metadata.has_audio), metadata.size_bytes),
            )
            existing = connection.execute(
                "SELECT id FROM analysis_runs WHERE video_id=? AND analysis_version=? AND rubric_version=?",
                (result.video_id, analysis_version, result.rubric_version),
            ).fetchone()
            if existing:
                analysis_id = int(existing["id"])
                for table in ("scores", "timeline_events", "issues", "fix_plans"):
                    connection.execute(f"DELETE FROM {table} WHERE analysis_id=?", (analysis_id,))
                connection.execute(
                    """UPDATE analysis_runs SET provider=?,model=?,classification=?,classification_reason=?,diagnosis=?,action_dna=?,
                    confidence=?,result_json=?,artifact_dir=?,created_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (result.provider, result.model, result.classification, result.classification_reason, result.diagnosis,
                     result.creative_structure_match, result.confidence, json.dumps(result.as_dict()), str(artifact_dir), analysis_id),
                )
            else:
                cursor = connection.execute(
                    """INSERT INTO analysis_runs(video_id,analysis_version,rubric_version,provider,model,classification,
                    classification_reason,diagnosis,action_dna,confidence,result_json,artifact_dir) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (result.video_id, analysis_version, result.rubric_version, result.provider, result.model,
                     result.classification, result.classification_reason, result.diagnosis, result.creative_structure_match,
                     result.confidence, json.dumps(result.as_dict()), str(artifact_dir)),
                )
                analysis_id = int(cursor.lastrowid)
            connection.executemany("INSERT INTO scores(analysis_id,dimension,score) VALUES(?,?,?)", [(analysis_id, key, value) for key, value in result.scores.items()])
            connection.executemany(
                "INSERT INTO timeline_events(analysis_id,start_time,end_time,kind,detail,confidence) VALUES(?,?,?,?,?,?)",
                [(analysis_id, item.start, item.end, item.kind, item.detail, item.confidence) for item in result.timeline],
            )
            connection.executemany(
                """INSERT INTO issues(analysis_id,code,severity,start_time,end_time,evidence,consequence,proposed_change,auto_fixable)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                [(analysis_id, item.code, item.severity, item.start, item.end, item.evidence, item.consequence,
                  item.proposed_change, int(item.auto_fixable)) for item in result.issues],
            )
            connection.execute("INSERT INTO fix_plans(analysis_id,operations_json) VALUES(?,?)", (analysis_id, json.dumps([asdict(item) for item in result.fix_plan])))

    def list_videos(self) -> list[dict[str, Any]]:
        query = """
        SELECT v.*, a.classification, a.action_dna, a.confidence, a.diagnosis, a.artifact_dir,
               json_extract(a.result_json,'$.scores.first_frame_hook') hook_score,
               json_extract(a.result_json,'$.scores.character_goal') goal_score,
               json_extract(a.result_json,'$.scores.physical_action') action_score,
               json_extract(a.result_json,'$.scores.escalation') escalation_score,
               json_extract(a.result_json,'$.scores.final_twist') final_score,
               (SELECT COUNT(*) FROM issues i WHERE i.analysis_id=a.id AND i.code LIKE 'CONTINUITY%') continuity_issues,
               (SELECT MAX(COALESCE(pm.reach,pm.views)) FROM performance_metrics pm WHERE pm.video_id=v.id) actual_performance,
               hr.override_classification, hr.confirmed_classification, hr.note human_note,
               rr.classification rescue_classification,rr.classification_label rescue_classification_label,
               rr.creative_engine_json rescue_engine,rr.hook_score rescue_hook,rr.ending_score rescue_ending,
               rr.publishing_use rescue_publishing_use,rr.confidence rescue_confidence,
               rrv.override_classification rescue_override_classification,rrv.note rescue_human_note
        FROM videos v JOIN analysis_runs a ON a.id=(SELECT a2.id FROM analysis_runs a2 WHERE a2.video_id=v.id ORDER BY a2.id DESC LIMIT 1)
        LEFT JOIN human_reviews hr ON hr.video_id=v.id
        LEFT JOIN rescue_runs rr ON rr.id=(SELECT rr2.id FROM rescue_runs rr2 WHERE rr2.video_id=v.id ORDER BY rr2.id DESC LIMIT 1)
        LEFT JOIN rescue_reviews rrv ON rrv.video_id=v.id
        ORDER BY a.created_at DESC
        """
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query)]

    def detail(self, video_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT v.*,a.id analysis_id,a.classification,a.action_dna,a.confidence,a.result_json,a.artifact_dir,
                hr.confirmed_classification,hr.override_classification,hr.analysis_wrong,hr.note human_note,hr.fix_decision,
                rr.id rescue_run_id,rr.result_json rescue_result_json,rr.classification rescue_classification,
                rr.classification_label rescue_classification_label,rr.artifact_dir rescue_artifact_dir,
                rrv.confirmed_classification rescue_confirmed_classification,
                rrv.override_classification rescue_override_classification,rrv.engine_override,
                rrv.note rescue_human_note,rrv.edit_decision rescue_edit_decision
                FROM videos v JOIN analysis_runs a ON a.id=(SELECT a2.id FROM analysis_runs a2 WHERE a2.video_id=v.id ORDER BY a2.id DESC LIMIT 1)
                LEFT JOIN rescue_runs rr ON rr.id=(SELECT rr2.id FROM rescue_runs rr2 WHERE rr2.video_id=v.id ORDER BY rr2.id DESC LIMIT 1)
                LEFT JOIN human_reviews hr ON hr.video_id=v.id
                LEFT JOIN rescue_reviews rrv ON rrv.video_id=v.id
                WHERE v.id=?""", (video_id,),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["analysis"] = json.loads(result.pop("result_json"))
            rescue_json = result.pop("rescue_result_json")
            result["rescue"] = json.loads(rescue_json) if rescue_json else None
            result["performance"] = [dict(item) for item in connection.execute("SELECT * FROM performance_metrics WHERE video_id=? ORDER BY published_at DESC", (video_id,))]
            return result

    def save_rescue_review(self, video_id: str, payload: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO rescue_reviews(video_id,confirmed_classification,override_classification,engine_override,note,edit_decision)
                VALUES(?,?,?,?,?,?) ON CONFLICT(video_id) DO UPDATE SET confirmed_classification=excluded.confirmed_classification,
                override_classification=excluded.override_classification,engine_override=excluded.engine_override,note=excluded.note,
                edit_decision=excluded.edit_decision,reviewed_at=CURRENT_TIMESTAMP""",
                (video_id, payload.get("confirmed_classification"), payload.get("override_classification"),
                 payload.get("engine_override"), payload.get("note"), payload.get("edit_decision")),
            )

    def save_review(self, video_id: str, payload: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO human_reviews(video_id,confirmed_classification,override_classification,analysis_wrong,note,fix_decision)
                VALUES(?,?,?,?,?,?) ON CONFLICT(video_id) DO UPDATE SET confirmed_classification=excluded.confirmed_classification,
                override_classification=excluded.override_classification,analysis_wrong=excluded.analysis_wrong,note=excluded.note,
                fix_decision=excluded.fix_decision,reviewed_at=CURRENT_TIMESTAMP""",
                (video_id, payload.get("confirmed_classification"), payload.get("override_classification"),
                 int(bool(payload.get("analysis_wrong"))), payload.get("note"), payload.get("fix_decision")),
            )

    def save_performance(self, video_id: str, payload: dict[str, Any]) -> None:
        fields = ["platform", "published_at", "views", "reach", "average_watch_seconds", "three_second_views",
                  "fifteen_second_views", "likes", "comments", "shares", "saves", "follows", "country_distribution_json",
                  "source_note", "is_approximate"]
        with self.connect() as connection:
            source_note = payload.get("source_note")
            if source_note:
                duplicate = connection.execute(
                    "SELECT 1 FROM performance_metrics WHERE video_id=? AND platform=? AND source_note=?",
                    (video_id, payload.get("platform"), source_note),
                ).fetchone()
                if duplicate:
                    return
            connection.execute(
                f"INSERT INTO performance_metrics(video_id,{','.join(fields)}) VALUES(? ,{','.join('?' for _ in fields)})",
                [video_id, *[payload.get(field) or None for field in fields]],
            )

    def record_edit(self, video_id: str, analysis_id: int, output_path: Path, status: str, comparison: dict[str, Any] | None = None) -> None:
        with self.connect() as connection:
            connection.execute("INSERT INTO edits(video_id,analysis_id,output_path,status,comparison_json) VALUES(?,?,?,?,?)",
                               (video_id, analysis_id, str(output_path), status, json.dumps(comparison) if comparison else None))

    def series_summary(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT v.series,a.action_dna,a.classification,
                json_extract(a.result_json,'$.scores.first_frame_hook') hook,
                json_extract(a.result_json,'$.scores.physical_action') action,
                (SELECT MAX(COALESCE(pm.reach,pm.views)) FROM performance_metrics pm WHERE pm.video_id=v.id) observed_performance
                FROM videos v JOIN analysis_runs a ON a.id=(SELECT a2.id FROM analysis_runs a2 WHERE a2.video_id=v.id ORDER BY a2.id DESC LIMIT 1)"""
            )
            grouped: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                item = dict(row)
                grouped.setdefault(item["series"], []).append(item)
            summaries = []
            for series, items in grouped.items():
                observed = [float(item["observed_performance"]) for item in items if item["observed_performance"] is not None]
                summaries.append({
                    "series": series,
                    "video_count": len(items),
                    "median_action_dna": round(statistics.median(float(item["action_dna"]) for item in items), 1),
                    "median_hook": round(statistics.median(float(item["hook"]) for item in items), 1),
                    "median_action": round(statistics.median(float(item["action"]) for item in items), 1),
                    "strong_count": sum(item["classification"] in {"GOOD", "WINNER CANDIDATE"} for item in items),
                    "observed_median_performance": round(statistics.median(observed), 1) if observed else None,
                })
            return sorted(summaries, key=lambda item: item["median_action_dna"], reverse=True)

    def lab_overview(self) -> dict[str, Any]:
        with self.connect() as connection:
            scalar = lambda query: connection.execute(query).fetchone()[0]
            imports = [dict(row) for row in connection.execute(
                "SELECT id,source_filename,platform,imported_at,row_count,quality_report_json,status FROM performance_imports ORDER BY id DESC LIMIT 20"
            )]
            predictions = [dict(row) for row in connection.execute(
                """SELECT p.id,p.video_id,v.filename,p.platform,p.mode,p.model_version,p.confidence,p.comparable_sample_size,
                p.historical_platform_fit_score,p.learned_opportunity_score,p.prediction_created_at,p.locked_at
                FROM predictions p JOIN videos v ON v.id=p.video_id ORDER BY p.id DESC LIMIT 30"""
            )]
            models = [dict(row) for row in connection.execute(
                """SELECT m.id,m.version,m.platform,m.algorithm,m.status,m.validation_json,m.created_at,d.row_count,d.as_of
                FROM model_versions m LEFT JOIN dataset_snapshots d ON d.id=m.dataset_snapshot_id ORDER BY m.id DESC LIMIT 20"""
            )]
            experiments = [dict(row) for row in connection.execute("SELECT * FROM experiments ORDER BY id DESC LIMIT 20")]
            characters = [dict(row) for row in connection.execute(
                """SELECT c.id,c.name,c.status,c.active,COUNT(DISTINCT vc.video_id) video_count,
                GROUP_CONCAT(DISTINCT t.platform) platforms,MAX(t.rebuilt_at) last_measured
                FROM characters c LEFT JOIN video_characters vc ON vc.character_id=c.id
                LEFT JOIN performance_trajectories t ON t.video_id=vc.video_id GROUP BY c.id ORDER BY c.name"""
            )]
            trajectories = [dict(row) for row in connection.execute(
                """SELECT t.video_id,v.filename,t.platform,MAX(t.checkpoint_minutes) checkpoint_minutes,MAX(t.views) views,
                MAX(t.reach) reach,MAX(t.views_per_hour) peak_velocity,MAX(t.performance_band) performance_band,
                MAX(t.trajectory_label) trajectory_label FROM performance_trajectories t JOIN videos v ON v.id=t.video_id
                GROUP BY t.video_id,t.platform ORDER BY MAX(t.views) DESC LIMIT 50"""
            )]
            return {
                "counts": {
                    "imports": scalar("SELECT COUNT(*) FROM performance_imports"),
                    "normalised_observations": scalar("SELECT COUNT(*) FROM normalised_performance"),
                    "unresolved": scalar("SELECT COUNT(*) FROM import_row_matches WHERE status IN ('UNRESOLVED','SUGGESTED')"),
                    "conflicts": scalar("SELECT COUNT(*) FROM performance_conflicts WHERE status='OPEN'"),
                    "locked_predictions": scalar("SELECT COUNT(*) FROM predictions WHERE locked_at IS NOT NULL"),
                    "experiments": scalar("SELECT COUNT(*) FROM experiments"),
                },
                "imports": imports, "predictions": predictions, "models": models, "experiments": experiments,
                "characters": characters, "trajectories": trajectories,
            }
