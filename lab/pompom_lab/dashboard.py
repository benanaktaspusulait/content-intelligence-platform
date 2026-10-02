from __future__ import annotations

import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .config import Settings
from .database import Database
from .spreadsheet_ingest import import_path, resolve_row
from .trajectory import rebuild as rebuild_trajectories


class Dashboard:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def serve(self) -> None:
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "PompomCreativeLab/0.1"
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if parsed.path == "/":
                    return self.file(dashboard.settings.project_dir / "web" / "index.html")
                if parsed.path == "/app.css":
                    return self.file(dashboard.settings.project_dir / "web" / "app.css")
                if parsed.path == "/rescue.css":
                    return self.file(dashboard.settings.project_dir / "web" / "rescue.css")
                if parsed.path == "/lab.css":
                    return self.file(dashboard.settings.project_dir / "web" / "lab.css")
                if parsed.path == "/app.js":
                    return self.file(dashboard.settings.project_dir / "web" / "app.js")
                if parsed.path == "/api/videos":
                    return self.json(dashboard.database.list_videos())
                if parsed.path == "/api/series":
                    return self.json(dashboard.database.series_summary())
                if parsed.path == "/api/lab":
                    return self.json(dashboard.database.lab_overview())
                if parsed.path == "/api/video":
                    video_id = query.get("id", [""])[0]
                    detail = dashboard.database.detail(video_id)
                    return self.json(detail or {"error": "not found"}, 200 if detail else 404)
                if parsed.path == "/media":
                    return self.media(query.get("id", [""])[0])
                if parsed.path == "/artifact":
                    return self.artifact(query.get("id", [""])[0], query.get("name", [""])[0])
                if parsed.path == "/rescue-artifact":
                    return self.rescue_artifact(query.get("id", [""])[0], query.get("name", [""])[0])
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                payload = self.body_json()
                video_id = str(payload.pop("video_id", ""))
                if parsed.path == "/api/review" and dashboard.database.detail(video_id):
                    dashboard.database.save_review(video_id, payload)
                    return self.json({"ok": True})
                if parsed.path == "/api/performance" and dashboard.database.detail(video_id):
                    dashboard.database.save_performance(video_id, payload)
                    return self.json({"ok": True})
                if parsed.path == "/api/rescue-review" and dashboard.database.detail(video_id):
                    dashboard.database.save_rescue_review(video_id, payload)
                    return self.json({"ok": True})
                if parsed.path == "/api/import-performance":
                    source = Path(str(payload.get("path", ""))).expanduser().resolve()
                    allowed = dashboard.settings.input_dir == source or dashboard.settings.input_dir in source.parents
                    if not allowed:
                        return self.json({"error": "Import path must stay inside configured new14092026 scope"}, 403)
                    try:
                        result = import_path(dashboard.database, source, payload.get("platform"), payload.get("timezone", "Europe/London"), bool(payload.get("preview", True)))
                        return self.json(result)
                    except (ValueError, OSError) as error:
                        return self.json({"error": str(error)}, 400)
                if parsed.path == "/api/resolve-import":
                    try:
                        resolve_row(dashboard.database, int(payload["raw_row_id"]), str(payload["resolved_video_id"]), str(payload.get("note", "dashboard resolution")))
                        return self.json({"ok": True})
                    except (KeyError, ValueError) as error:
                        return self.json({"error": str(error)}, 400)
                if parsed.path == "/api/rebuild-trajectories":
                    return self.json(rebuild_trajectories(dashboard.database))
                self.json({"error": "invalid request"}, 400)

            def body_json(self) -> dict:
                length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
                try:
                    return json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    return {}

            def json(self, payload: object, status: int = 200) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def file(self, path: Path) -> None:
                if not path.is_file():
                    return self.send_error(404)
                data = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def media(self, video_id: str) -> None:
                detail = dashboard.database.detail(video_id)
                if not detail:
                    return self.send_error(404)
                path = Path(detail["path"]).resolve()
                if not path.is_file() or dashboard.settings.input_dir not in path.parents:
                    return self.send_error(403)
                size = path.stat().st_size
                start, end = 0, size - 1
                range_header = self.headers.get("Range")
                status = 200
                if range_header:
                    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
                    if match:
                        start = int(match.group(1) or 0)
                        end = min(int(match.group(2) or size - 1), size - 1)
                        status = 206
                length = max(0, end - start + 1)
                self.send_response(status)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "video/mp4")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(length))
                if status == 206:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.end_headers()
                with path.open("rb") as handle:
                    handle.seek(start)
                    remaining = length
                    while remaining:
                        chunk = handle.read(min(1024 * 256, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)

            def artifact(self, video_id: str, name: str) -> None:
                if name not in {"storyboard.jpg", "report.md", "analysis.json", "fix_plan.md"}:
                    return self.send_error(400)
                detail = dashboard.database.detail(video_id)
                if not detail:
                    return self.send_error(404)
                root = Path(detail["artifact_dir"]).resolve()
                path = (root / name).resolve()
                if root not in path.parents or not path.is_file():
                    return self.send_error(404)
                return self.file(path)

            def rescue_artifact(self, video_id: str, name: str) -> None:
                if name not in {"rescue_report.md", "rescue_analysis.json"}:
                    return self.send_error(400)
                detail = dashboard.database.detail(video_id)
                if not detail or not detail.get("rescue_artifact_dir"):
                    return self.send_error(404)
                root = Path(detail["rescue_artifact_dir"]).resolve()
                path = (root / name).resolve()
                if root not in path.parents or not path.is_file():
                    return self.send_error(404)
                return self.file(path)

            def log_message(self, format: str, *args: object) -> None:
                print(f"dashboard: {format % args}")

        class LocalServer(ThreadingHTTPServer):
            allow_reuse_address = True

        server = LocalServer((self.settings.host, self.settings.port), Handler)
        print(f"Pompom Creative Lab: http://{self.settings.host}:{self.settings.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
