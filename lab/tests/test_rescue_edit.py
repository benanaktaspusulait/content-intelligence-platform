from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from pompom_lab.ffmpeg_tools import probe, render_cold_open_candidate


class RescueEditIntegrationTests(unittest.TestCase):
    def test_cold_open_uses_existing_footage_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            output = root / "candidate.mp4"
            subprocess.run([
                "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                "testsrc2=duration=3:size=320x180:rate=12", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True)
            before = source.read_bytes()
            render_cold_open_candidate(source, output, 1.2, 1.7, has_audio=False)
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(output.is_file())
            self.assertGreater(probe(output, root).duration, probe(source, root).duration)


if __name__ == "__main__":
    unittest.main()
