from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from pompom_lab.config import Settings
from pompom_lab.database import Database
from pompom_lab.ffmpeg_tools import MediaToolError, probe
from pompom_lab.pipeline import AlreadyAnalysed, Pipeline


class PipelineIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = Path(__file__).resolve().parent.parent
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / ".data"
        self.settings = Settings(
            project_dir=self.project,
            input_dir=self.root,
            data_dir=self.data,
            database=self.data / "library.sqlite3",
            sample_fps=4.0,
            max_analysis_width=320,
        )
        self.database = Database(self.settings.database, self.project / "migrations")
        self.pipeline = Pipeline(self.settings, self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fixture(self, name: str = "şort video.mp4") -> Path:
        path = self.root / name
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=duration=3:size=320x180:rate=12", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)],
            check=True,
        )
        return path

    def test_unicode_landscape_no_audio_end_to_end(self) -> None:
        path = self.fixture()
        result = self.pipeline.analyse_one(path)
        self.assertFalse(result.metadata.has_audio)
        self.assertGreater(result.metadata.aspect_ratio, 1.0)
        artifact = self.data / "output" / "analyses" / result.video_id
        for name in ("analysis.json", "report.md", "storyboard.jpg", "timeline.json", "fix_plan.json"):
            self.assertTrue((artifact / name).is_file(), name)

    def test_duplicate_is_cached(self) -> None:
        path = self.fixture("duplicate.mp4")
        self.pipeline.analyse_one(path)
        with self.assertRaises(AlreadyAnalysed):
            self.pipeline.analyse_one(path)

    def test_corrupted_video_is_rejected(self) -> None:
        path = self.root / "corrupt.mp4"
        path.write_bytes(b"not a video")
        with self.assertRaises(MediaToolError):
            probe(path, self.root)


if __name__ == "__main__":
    unittest.main()

