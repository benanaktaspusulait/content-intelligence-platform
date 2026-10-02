from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from .database import Database

PARSER_VERSION = "performance-import-v1"
MAPPING_VERSION = "canonical-aliases-v1"
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".json"}
METRICS = (
    "views", "reach", "unique_viewers", "three_second_views", "fifteen_second_views",
    "average_watch_seconds", "total_watch_seconds", "likes", "comments", "shares", "saves",
    "follows", "recommendation_watch_seconds", "recommendation_percentage",
    "followers_watch_percentage", "nonfollowers_watch_percentage",
)

ALIASES = {
    "video_id": {"video id", "internal video id", "pompom video id"},
    "path": {"path", "file path", "video path"},
    "platform_content_id": {"content id", "asset id", "post id", "reel id", "platform content id"},
    "title": {"title", "post title", "video title", "name", "description"},
    "publication_timestamp": {"published at", "publication time", "publish time", "created time", "posted at"},
    "measurement_timestamp": {"measurement timestamp", "snapshot time", "export time", "as of"},
    "measurement_date": {"date", "measurement date", "day"},
    "metric_semantics": {"metric semantics", "row type", "semantics"},
    "views": {"views", "video views", "total views"},
    "reach": {"reach", "people reached", "accounts reached"},
    "unique_viewers": {"unique viewers", "unique video viewers"},
    "three_second_views": {"3-second video views", "3 second views", "three second views", "3s views"},
    "fifteen_second_views": {"15-second video views", "15 second views", "fifteen second views", "15s views"},
    "average_watch_seconds": {"average watch time", "average watch seconds", "avg watch time", "avg watch seconds"},
    "total_watch_seconds": {"total watch seconds", "watch time seconds", "total watch time"},
    "likes": {"likes", "reactions"},
    "comments": {"comments"},
    "shares": {"shares"},
    "saves": {"saves", "saved"},
    "follows": {"follows", "new followers", "followers"},
    "recommendation_watch_seconds": {"recommendation watch seconds"},
    "recommendation_percentage": {"recommendation percentage", "recommended percentage"},
    "followers_watch_percentage": {"followers watch percentage", "follower percentage"},
    "nonfollowers_watch_percentage": {"nonfollowers watch percentage", "non-follower percentage"},
    "country_distribution_json": {"country distribution", "country distribution json", "countries"},
    "is_paid": {"paid", "is paid", "promoted"},
}
ALIAS_LOOKUP = {alias: canonical for canonical, aliases in ALIASES.items() for alias in aliases}


@dataclass(slots=True)
class SheetData:
    name: str
    headers: list[str]
    rows: list[dict[str, Any]]
    header_row: int


@dataclass(slots=True)
class ImportPreview:
    path: Path
    file_hash: str
    sheets: list[SheetData]
    mapping: dict[str, str]
    platform: str
    warnings: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return sum(len(sheet.rows) for sheet in self.sheets)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path), "file_hash": self.file_hash, "platform": self.platform,
            "sheet_count": len(self.sheets), "row_count": self.row_count,
            "sheets": [{"name": s.name, "header_row": s.header_row, "columns": s.headers, "rows": len(s.rows)} for s in self.sheets],
            "mapping": self.mapping, "warnings": self.warnings,
        }


def _clean_header(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", " "))


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cell_column(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper())
    result = 0
    for char in letters.group(0) if letters else "A":
        result = result * 26 + ord(char) - 64
    return result - 1


def _xlsx_sheets(path: Path) -> list[SheetData]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    rel_ns = {"p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//m:t", ns)) for item in root.findall("m:si", ns)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships.findall("p:Relationship", rel_ns)}
        output: list[SheetData] = []
        for sheet in workbook.findall("m:sheets/m:sheet", ns):
            target = targets[sheet.attrib[f"{{{ns['r']}}}id"]].lstrip("/")
            xml_path = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(archive.read(xml_path))
            matrix: list[list[Any]] = []
            for row in root.findall(".//m:sheetData/m:row", ns):
                values: list[Any] = []
                for cell in row.findall("m:c", ns):
                    column = _cell_column(cell.attrib.get("r", "A1"))
                    while len(values) <= column:
                        values.append("")
                    value_node = cell.find("m:v", ns)
                    inline = cell.find("m:is/m:t", ns)
                    value: Any = inline.text if inline is not None else (value_node.text if value_node is not None else "")
                    if cell.attrib.get("t") == "s" and value != "":
                        value = shared[int(value)]
                    elif cell.attrib.get("t") == "b":
                        value = value == "1"
                    values[column] = value
                matrix.append(values)
        
            output.append(_matrix_to_sheet(sheet.attrib["name"], matrix))
        return [sheet for sheet in output if sheet.headers and sheet.rows]


def _matrix_to_sheet(name: str, matrix: list[list[Any]]) -> SheetData:
    header_index = 0
    best = -1
    for index, row in enumerate(matrix[:20]):
        score = sum(bool(str(value).strip()) for value in row)
        if score > best:
            header_index, best = index, score
    if best < 2:
        return SheetData(name, [], [], header_index + 1)
    headers = [str(value).strip() or f"column_{index + 1}" for index, value in enumerate(matrix[header_index])]
    rows: list[dict[str, Any]] = []
    for raw in matrix[header_index + 1:]:
        row = {header: raw[index] if index < len(raw) else "" for index, header in enumerate(headers)}
        if any(str(value).strip() for value in row.values()):
            rows.append(row)
    return SheetData(name, headers, rows, header_index + 1)


def _delimited_sheet(path: Path) -> SheetData:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        if path.suffix.lower() == ".csv":
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
            except csv.Error:
                pass
        reader = csv.DictReader(handle, delimiter=delimiter)
        rows = [dict(row) for row in reader]
        return SheetData(path.stem, list(reader.fieldnames or []), rows, 1)


def _json_sheet(path: Path) -> SheetData:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        payload = payload.get("rows", payload.get("data", [payload]))
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError("JSON performance input must be an object or a list of objects")
    headers = list(dict.fromkeys(key for row in payload for key in row))
    return SheetData(path.stem, headers, payload, 1)


def inspect_file(path: Path, platform: str | None = None) -> ImportPreview:
    path = path.expanduser().resolve()
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported performance file: {suffix}")
    if suffix == ".xls":
        raise ValueError("Legacy .xls requires conversion to .xlsx or .csv; source file was not modified")
    sheets = _xlsx_sheets(path) if suffix == ".xlsx" else ([_json_sheet(path)] if suffix == ".json" else [_delimited_sheet(path)])
    mapping: dict[str, str] = {}
    warnings: list[str] = []
    for sheet in sheets:
        for header in sheet.headers:
            canonical = ALIAS_LOOKUP.get(_clean_header(header))
            if canonical:
                mapping[header] = canonical
    if not any(value in {"video_id", "path", "platform_content_id", "title"} for value in mapping.values()):
        warnings.append("No stable video identifier column was detected")
    if not any(value in METRICS for value in mapping.values()):
        warnings.append("No canonical performance metric was detected")
    detected = (platform or _detect_platform(path, sheets)).lower()
    return ImportPreview(path, _file_hash(path), sheets, mapping, detected, warnings)


def _detect_platform(path: Path, sheets: list[SheetData]) -> str:
    text = " ".join([path.name, *[sheet.name for sheet in sheets]]).lower()
    if "instagram" in text or " ig " in f" {text} ":
        return "instagram"
    if "tiktok" in text:
        return "tiktok"
    if "facebook" in text or "meta" in text:
        return "facebook"
    return "unknown"


def _number(value: Any, integer: bool = False) -> int | float | None:
    if value is None or str(value).strip() in {"", "-", "—", "N/A", "n/a"}:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    try:
        number = float(text)
        return int(round(number)) if integer else number
    except ValueError:
        return None


def _timestamp(value: Any, account_timezone: str) -> tuple[str | None, str | None, str | None]:
    raw = str(value or "").strip()
    if not raw:
        return None, None, None
    parsed: datetime | None = None
    if re.fullmatch(r"\d+(\.\d+)?", raw) and float(raw) > 20_000:
        parsed = datetime(1899, 12, 30) + timedelta(days=float(raw))
    else:
        normal = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normal)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%m/%d/%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    parsed = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
    if parsed is None:
        return None, None, None
    local_zone = ZoneInfo(account_timezone)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=local_zone)
    utc = parsed.astimezone(timezone.utc).isoformat()
    local = parsed.astimezone(local_zone).isoformat()
    return utc, local, parsed.tzname() or account_timezone


def _canonical_row(row: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    return {canonical: row.get(source) for source, canonical in mapping.items()}


def _semantics(value: Any, has_date: bool) -> str:
    text = str(value or "").strip().upper().replace(" ", "_")
    if text in {"DAILY_INCREMENT", "CUMULATIVE", "SNAPSHOT", "UNKNOWN"}:
        return text
    return "DAILY_INCREMENT" if has_date else "SNAPSHOT"


def _match(connection: Any, canonical: dict[str, Any], platform: str) -> tuple[str | None, str, float, list[dict[str, Any]]]:
    video_id = str(canonical.get("video_id") or "").strip()
    if video_id and connection.execute("SELECT 1 FROM videos WHERE id=?", (video_id,)).fetchone():
        return video_id, "EXACT_VIDEO_ID", 1.0, []
    path = str(canonical.get("path") or "").strip()
    if path:
        row = connection.execute("SELECT id FROM videos WHERE path=?", (str(Path(path).expanduser().resolve()),)).fetchone()
        if row:
            return row[0], "EXACT_PATH", 1.0, []
    content_id = str(canonical.get("platform_content_id") or "").strip()
    if content_id:
        row = connection.execute("SELECT video_id FROM platform_content_mappings WHERE platform=? AND platform_content_id=?", (platform, content_id)).fetchone()
        if row:
            return row[0], "EXACT_PLATFORM_ID", 1.0, []
    title = str(canonical.get("title") or "").strip().lower()
    candidates: list[dict[str, Any]] = []
    if title:
        tokens = {token for token in re.findall(r"[a-z0-9]+", title) if len(token) > 2}
        for row in connection.execute("SELECT id,filename,series FROM videos"):
            haystack = f"{row['filename']} {row['series']}".lower()
            overlap = sum(token in haystack for token in tokens)
            score = overlap / max(1, len(tokens))
            if score >= 0.5:
                candidates.append({"video_id": row["id"], "filename": row["filename"], "score": round(score, 3)})
        candidates.sort(key=lambda item: item["score"], reverse=True)
    return None, "TITLE_SUGGESTION" if candidates else "NO_MATCH", candidates[0]["score"] if candidates else 0.0, candidates[:5]


def _iter_files(path: Path) -> Iterable[Path]:
    path = path.expanduser().resolve()
    if path.is_file():
        yield path
    else:
        yield from sorted(item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES)


def import_path(database: Database, path: Path, platform: str | None = None, account_timezone: str = "Europe/London", preview_only: bool = False) -> dict[str, Any]:
    reports = []
    for source in _iter_files(path):
        preview = inspect_file(source, platform)
        if preview_only:
            reports.append({"status": "PREVIEW", **preview.as_dict()})
            continue
        with database.connect() as connection:
            duplicate = connection.execute("SELECT id FROM performance_imports WHERE file_hash=?", (preview.file_hash,)).fetchone()
            if duplicate:
                reports.append({"path": str(source), "status": "ALREADY_IMPORTED", "import_id": duplicate[0]})
                continue
            mapped = unresolved = rejected = conflicts = 0
            quality: list[dict[str, Any]] = [{"severity": "WARNING", "code": "INSPECTION", "message": warning} for warning in preview.warnings]
            cursor = connection.execute(
                """INSERT INTO performance_imports(source_filename,source_path,file_hash,file_size,platform,detected_export_type,
                parser_version,schema_mapping_version,account_timezone,timezone_assumption,sheet_count,row_count,column_mapping_json,
                quality_report_json,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (source.name, str(source), preview.file_hash, source.stat().st_size, preview.platform, source.suffix.lower().lstrip("."),
                 PARSER_VERSION, MAPPING_VERSION, account_timezone, "ACCOUNT_LOCAL_UNLESS_OFFSET_PRESENT", len(preview.sheets),
                 preview.row_count, json.dumps(preview.mapping), "{}", "COMMITTED"),
            )
            import_id = int(cursor.lastrowid)
            for sheet in preview.sheets:
                for offset, raw in enumerate(sheet.rows, start=sheet.header_row + 1):
                    raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
                    row_hash = hashlib.sha256(raw_json.encode()).hexdigest()
                    raw_cursor = connection.execute(
                        "INSERT INTO raw_import_rows(import_id,sheet_name,source_row_number,raw_json,row_hash) VALUES(?,?,?,?,?)",
                        (import_id, sheet.name, offset, raw_json, row_hash),
                    )
                    raw_id = int(raw_cursor.lastrowid)
                    canonical = _canonical_row(raw, preview.mapping)
                    video_id, method, confidence, candidates = _match(connection, canonical, preview.platform)
                    status = "MATCHED" if video_id else ("SUGGESTED" if candidates else "UNRESOLVED")
                    connection.execute(
                        "INSERT INTO import_row_matches(raw_row_id,video_id,match_method,confidence,status,candidates_json) VALUES(?,?,?,?,?,?)",
                        (raw_id, video_id, method, confidence, status, json.dumps(candidates)),
                    )
                    if not video_id:
                        unresolved += 1
                        quality.append({"severity": "WARNING", "code": "UNRESOLVED_VIDEO", "message": f"{sheet.name} row {offset} could not be matched", "raw_row_id": raw_id})
                    publication_utc, publication_local, publication_tz = _timestamp(canonical.get("publication_timestamp"), account_timezone)
                    measurement_value = canonical.get("measurement_timestamp") or canonical.get("measurement_date")
                    measurement_utc, measurement_local, measurement_tz = _timestamp(measurement_value, account_timezone)
                    measurement_date = str(canonical.get("measurement_date") or "").strip() or (measurement_local[:10] if measurement_local else None)
                    semantics = _semantics(canonical.get("metric_semantics"), bool(canonical.get("measurement_date")))
                    values = {metric: _number(canonical.get(metric), integer=metric not in {"average_watch_seconds", "total_watch_seconds", "recommendation_watch_seconds", "recommendation_percentage", "followers_watch_percentage", "nonfollowers_watch_percentage"}) for metric in METRICS}
                    content_id = str(canonical.get("platform_content_id") or "").strip() or None
                    if content_id and video_id:
                        connection.execute("INSERT OR IGNORE INTO platform_content_mappings(platform,platform_content_id,video_id,source) VALUES(?,?,?,'IMPORT')", (preview.platform, content_id, video_id))
                    key = measurement_utc or measurement_date or publication_utc or f"row:{raw_id}"
                    existing = connection.execute(
                        "SELECT * FROM normalised_performance WHERE video_id=? AND platform=? AND COALESCE(measurement_timestamp_utc,measurement_date,publication_timestamp_utc)=? AND metric_semantics=? ORDER BY id LIMIT 1",
                        (video_id, preview.platform, key, semantics),
                    ).fetchone() if video_id else None
                    if existing:
                        for metric, value in values.items():
                            if value is not None and existing[metric] is not None and float(existing[metric]) != float(value):
                                conflicts += 1
                                connection.execute(
                                    """INSERT INTO performance_conflicts(platform,video_id,platform_content_id,measurement_key,metric,
                                    existing_observation_id,incoming_raw_row_id,existing_value,incoming_value) VALUES(?,?,?,?,?,?,?,?,?)""",
                                    (preview.platform, video_id, content_id, key, metric, existing["id"], raw_id, str(existing[metric]), str(value)),
                                )
                    country = canonical.get("country_distribution_json")
                    if country and not str(country).strip().startswith(("{", "[")):
                        country = json.dumps({"raw": str(country)}, ensure_ascii=False)
                    connection.execute(
                        f"""INSERT INTO normalised_performance(source_import_id,source_row_id,platform,platform_content_id,video_id,
                        publication_timestamp_raw,publication_timezone,publication_timestamp_utc,publication_timestamp_local,
                        measurement_timestamp_raw,measurement_timezone,measurement_timestamp_utc,measurement_timestamp_local,
                        measurement_date,metric_semantics,{','.join(METRICS)},country_distribution_json,is_paid)
                        VALUES({','.join('?' for _ in range(15 + len(METRICS) + 2))})""",
                        (import_id, raw_id, preview.platform, content_id, video_id,
                         str(canonical.get("publication_timestamp") or "") or None, publication_tz, publication_utc, publication_local,
                         str(measurement_value or "") or None, measurement_tz, measurement_utc, measurement_local,
                         measurement_date, semantics, *[values[metric] for metric in METRICS], country,
                         int(str(canonical.get("is_paid") or "").strip().lower() in {"1", "true", "yes", "paid"})),
                    )
                    mapped += int(video_id is not None)
            for issue in quality:
                connection.execute(
                    "INSERT INTO import_quality_issues(import_id,raw_row_id,severity,code,message) VALUES(?,?,?,?,?)",
                    (import_id, issue.get("raw_row_id"), issue["severity"], issue["code"], issue["message"]),
                )
            report = {"mapped": mapped, "unresolved": unresolved, "rejected": rejected, "conflicts": conflicts, "warnings": len(quality)}
            connection.execute("UPDATE performance_imports SET quality_report_json=? WHERE id=?", (json.dumps(report), import_id))
            reports.append({"path": str(source), "status": "IMPORTED", "import_id": import_id, **report})
    result: dict[str, Any] = {"files": reports, "file_count": len(reports)}
    if not preview_only and any(report.get("status") == "IMPORTED" for report in reports):
        result["after_import"] = post_import_updates(database)
    return result


def post_import_updates(database: Database) -> dict[str, Any]:
    from .prediction import audit
    from .trajectory import rebuild

    trajectory_result = rebuild(database)
    with database.connect() as connection:
        prediction_ids = [row[0] for row in connection.execute("SELECT id FROM predictions WHERE locked_at IS NOT NULL")]
    audited = 0
    for prediction_id in prediction_ids:
        audited += audit(database, prediction_id)["audited_horizons"]
    with database.connect() as connection:
        new_20k = connection.execute("SELECT COUNT(DISTINCT video_id) FROM performance_trajectories WHERE views>=20000").fetchone()[0]
        unresolved_count = connection.execute("SELECT COUNT(*) FROM import_row_matches WHERE status IN ('UNRESOLVED','SUGGESTED')").fetchone()[0]
    return {
        "trajectory_points_rebuilt": trajectory_result["rebuilt"],
        "prediction_horizons_audited": audited,
        "videos_observed_at_20k_plus": new_20k,
        "unresolved_rows": unresolved_count,
        "model_retraining": "not executed; create an explicit challenger with pompom learn",
    }


def unresolved(database: Database) -> list[dict[str, Any]]:
    with database.connect() as connection:
        return [dict(row) for row in connection.execute(
            """SELECT m.raw_row_id,m.status,m.match_method,m.confidence,m.candidates_json,r.sheet_name,r.source_row_number,
            r.raw_json,i.source_filename,i.platform FROM import_row_matches m JOIN raw_import_rows r ON r.id=m.raw_row_id
            JOIN performance_imports i ON i.id=r.import_id WHERE m.status IN ('UNRESOLVED','SUGGESTED') ORDER BY m.raw_row_id"""
        )]


def resolve_row(database: Database, raw_row_id: int, video_id: str, note: str = "human resolution") -> None:
    with database.connect() as connection:
        if not connection.execute("SELECT 1 FROM videos WHERE id=?", (video_id,)).fetchone():
            raise KeyError(video_id)
        connection.execute(
            "UPDATE import_row_matches SET video_id=?,status='MATCHED',match_method='HUMAN',confidence=1,resolution_note=?,resolved_at=CURRENT_TIMESTAMP WHERE raw_row_id=?",
            (video_id, note, raw_row_id),
        )
        connection.execute("UPDATE normalised_performance SET video_id=? WHERE source_row_id=?", (video_id, raw_row_id))
