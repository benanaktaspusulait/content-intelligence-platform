from __future__ import annotations

import unittest
from unittest.mock import patch

from pompom_lab.ffmpeg_tools import MediaToolError, require_tools


class ToolTests(unittest.TestCase):
    def test_missing_ffmpeg_has_clear_error(self) -> None:
        with patch("pompom_lab.ffmpeg_tools.shutil.which", return_value=None):
            with self.assertRaisesRegex(MediaToolError, "ffmpeg"):
                require_tools()


if __name__ == "__main__":
    unittest.main()
