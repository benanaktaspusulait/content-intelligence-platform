from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from pompom_lab.database import Database
from pompom_lab.prediction import _historical, audit, lock_prediction
from pompom_lab.spreadsheet_ingest import import_path, inspect_file, resolve_row
from pompom_lab.trajectory import rebuild


class LearningSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Path(__file__).resolve().parent.parent
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / "lab.sqlite3", self.project / "migrations")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO videos(id,content_hash,path,filename,series,duration,fps,width,height,codec,has_audio,size_bytes)
                VALUES('video-1','hash-1',?,'video-one.mp4','Test Series',15,30,1080,1920,'h264',1,1000)""",
                (str(self.root / "video-one.mp4"),),
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_csv(self, name: str, rows: list[dict[str, object]]) -> Path:
        path = self.root / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_import_is_deduplicated_and_missing_metric_stays_null(self) -> None:
        source = self.write_csv("meta.csv", [{
            "Video ID": "video-1", "Published At": "2026-03-29 00:30", "Measurement Timestamp": "2026-03-29 02:30",
            "Reach": "1200", "Views": "", "Metric Semantics": "SNAPSHOT",
        }])
        first = import_path(self.database, source, "facebook")
        second = import_path(self.database, source, "facebook")
        self.assertEqual(first["files"][0]["mapped"], 1)
        self.assertEqual(second["files"][0]["status"], "ALREADY_IMPORTED")
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM normalised_performance").fetchone()
        self.assertIsNone(row["views"])
        self.assertEqual(row["reach"], 1200)
        self.assertIn("+01:00", row["measurement_timestamp_local"])

    def test_daily_rows_build_cumulative_trajectory(self) -> None:
        source = self.write_csv("daily.csv", [
            {"Video ID": "video-1", "Published At": "2026-01-01 00:00", "Measurement Timestamp": "2026-01-01 12:00", "Views": "100", "Metric Semantics": "DAILY_INCREMENT"},
            {"Video ID": "video-1", "Published At": "2026-01-01 00:00", "Measurement Timestamp": "2026-01-02 00:00", "Views": "250", "Metric Semantics": "DAILY_INCREMENT"},
        ])
        import_path(self.database, source, "instagram")
        result = rebuild(self.database)
        self.assertGreater(result["rebuilt"], 0)
        with self.database.connect() as connection:
            row = connection.execute("SELECT views FROM performance_trajectories WHERE checkpoint_minutes=1440").fetchone()
        self.assertEqual(row["views"], 350)

    def test_conflicting_overlap_is_flagged(self) -> None:
        common = {"Video ID": "video-1", "Published At": "2026-01-01 00:00", "Measurement Timestamp": "2026-01-02 00:00", "Metric Semantics": "CUMULATIVE"}
        import_path(self.database, self.write_csv("one.csv", [{**common, "Views": "100"}]), "instagram")
        import_path(self.database, self.write_csv("two.csv", [{**common, "Views": "200"}]), "instagram")
        with self.database.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM performance_conflicts WHERE metric='views'").fetchone()[0]
        self.assertEqual(count, 1)

    def test_unresolved_row_can_be_reconciled_without_reimport(self) -> None:
        source = self.write_csv("unknown.csv", [{"Post ID": "external-7", "Views": "77"}])
        result = import_path(self.database, source, "facebook")
        self.assertEqual(result["files"][0]["unresolved"], 1)
        with self.database.connect() as connection:
            row = connection.execute("SELECT source_row_id,video_id,views FROM normalised_performance").fetchone()
        self.assertIsNone(row["video_id"])
        resolve_row(self.database, row["source_row_id"], "video-1")
        with self.database.connect() as connection:
            resolved = connection.execute("SELECT video_id FROM normalised_performance WHERE source_row_id=?", (row["source_row_id"],)).fetchone()[0]
        self.assertEqual(resolved, "video-1")

    def test_locked_prediction_and_children_are_immutable(self) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO predictions(video_id,platform,mode,model_version,feature_version,dataset_version,
                knowledge_cutoff,creative_fingerprint_snapshot,confidence,comparable_sample_size,payload_json)
                VALUES('video-1','instagram','PRE_PUBLISH','v1','f1','d1','2026-01-01T00:00:00+00:00','{}','LOW',0,'{}')"""
            )
            prediction_id = int(cursor.lastrowid)
            connection.execute("INSERT INTO prediction_targets(prediction_id,horizon_minutes,expected_value) VALUES(?,?,?)", (prediction_id, 1440, 1000))
        lock_prediction(self.database, prediction_id)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.database.connect() as connection:
                connection.execute("UPDATE predictions SET confidence='HIGH' WHERE id=?", (prediction_id,))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.database.connect() as connection:
                connection.execute("UPDATE prediction_targets SET expected_value=9999 WHERE prediction_id=?", (prediction_id,))

    def test_pre_publish_history_excludes_future_imports(self) -> None:
        with self.database.connect() as connection:
            for import_id, imported_at, measured, views in (
                (1, "2026-01-02 00:00:00", "2026-01-01T12:00:00+00:00", 100),
                (2, "2026-02-02 00:00:00", "2026-02-01T12:00:00+00:00", 9000),
            ):
                connection.execute(
                    """INSERT INTO performance_imports(id,source_filename,source_path,file_hash,file_size,imported_at,platform,
                    detected_export_type,parser_version,schema_mapping_version,account_timezone,timezone_assumption,sheet_count,
                    row_count,column_mapping_json,quality_report_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (import_id, f"{import_id}.csv", f"/{import_id}.csv", f"hash-{import_id}", 10, imported_at, "instagram", "csv", "v1", "v1", "Europe/London", "test", 1, 1, "{}", "{}"),
                )
                raw = connection.execute("INSERT INTO raw_import_rows(import_id,sheet_name,source_row_number,raw_json,row_hash) VALUES(?, 's', 2, '{}', ?)", (import_id, f"row-{import_id}")).lastrowid
                observation = connection.execute(
                    """INSERT INTO normalised_performance(source_import_id,source_row_id,platform,video_id,measurement_timestamp_utc,
                    metric_semantics,views) VALUES(?,?,?,?,?,'SNAPSHOT',?)""", (import_id, raw, "instagram", "video-1", measured, views),
                ).lastrowid
                connection.execute(
                    """INSERT INTO performance_trajectories(video_id,platform,checkpoint_minutes,views,performance_band,
                    trajectory_label,source_observation_ids_json) VALUES('video-1','instagram',1440,?,?,?,?)""",
                    (views, "LOW" if views < 500 else "STRONG", "SLOW_GROWTH", json.dumps([observation])),
                )
                if import_id == 1:
                    connection.execute("DELETE FROM performance_trajectories WHERE id=(SELECT MAX(id) FROM performance_trajectories)")
                    connection.execute(
                        """INSERT INTO performance_trajectories(video_id,platform,checkpoint_minutes,views,performance_band,
                        trajectory_label,source_observation_ids_json) VALUES('video-1','instagram',60,?,'LOW','SLOW_GROWTH',?)""",
                        (views, json.dumps([observation])),
                    )
        rows = _historical(self.database, "instagram", 1440, "2026-01-15T00:00:00+00:00")
        self.assertEqual(rows, [])
        early = _historical(self.database, "instagram", 60, "2026-01-15T00:00:00+00:00")
        self.assertEqual([row["views"] for row in early], [100.0])

    def test_audit_calculates_interval_coverage_and_brier(self) -> None:
        with self.database.connect() as connection:
            prediction_id = int(connection.execute(
                """INSERT INTO predictions(video_id,platform,mode,model_version,feature_version,dataset_version,
                knowledge_cutoff,creative_fingerprint_snapshot,confidence,comparable_sample_size,payload_json)
                VALUES('video-1','facebook','PRE_PUBLISH','v1','f1','d1','2026-01-01T00:00:00+00:00','{}','LOW',2,'{}')"""
            ).lastrowid)
            connection.execute("INSERT INTO prediction_targets(prediction_id,horizon_minutes,expected_value,interval_50_low,interval_50_high,interval_80_low,interval_80_high) VALUES(?,1440,6000,4000,8000,1000,12000)", (prediction_id,))
            connection.execute("INSERT INTO prediction_probabilities VALUES(?,1440,'BAND','STRONG',.7)", (prediction_id,))
            connection.execute("INSERT INTO prediction_probabilities VALUES(?,1440,'BAND','LOW',.3)", (prediction_id,))
            connection.execute("INSERT INTO performance_trajectories(video_id,platform,checkpoint_minutes,views,performance_band,trajectory_label,source_observation_ids_json) VALUES('video-1','facebook',1440,7000,'STRONG','SECOND_WAVE','[]')")
        lock_prediction(self.database, prediction_id)
        result = audit(self.database, prediction_id)
        item = result["audits"][0]
        self.assertEqual(item["inside_interval_50"], 1)
        self.assertAlmostEqual(item["brier_score"], .09)

    def test_xlsx_inspects_multiple_sheets(self) -> None:
        path = self.root / "multi.xlsx"
        workbook = '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="IG" sheetId="1" r:id="rId1"/><sheet name="FB" sheetId="2" r:id="rId2"/></sheets></workbook>'
        rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>'
        sheet = '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="inlineStr"><is><t>Video ID</t></is></c><c r="B1" t="inlineStr"><is><t>Views</t></is></c></row><row><c r="A2" t="inlineStr"><is><t>video-1</t></is></c><c r="B2"><v>12</v></c></row></sheetData></worksheet>'
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/workbook.xml", workbook)
            archive.writestr("xl/_rels/workbook.xml.rels", rels)
            archive.writestr("xl/worksheets/sheet1.xml", sheet)
            archive.writestr("xl/worksheets/sheet2.xml", sheet.replace("12", "24"))
        preview = inspect_file(path, "instagram")
        self.assertEqual(len(preview.sheets), 2)
        self.assertEqual(preview.row_count, 2)


if __name__ == "__main__":
    unittest.main()
