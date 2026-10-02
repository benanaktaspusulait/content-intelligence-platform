from __future__ import annotations

import unittest

from pompom_lab.frame_analysis import FrameMetric, VisualMetrics
from pompom_lab.models import Evidence, VideoMetadata
from pompom_lab.scoring import score


def metadata() -> VideoMetadata:
    return VideoMetadata("/tmp/video.mp4", "video.mp4", "Test", 15.0, 24.0, 1080, 1920, 0.5625, "h264", False, None, 100, "a" * 64)


class ScoringTests(unittest.TestCase):
    def test_black_opening_is_not_good(self) -> None:
        frames = [FrameMetric(i * .25, 1.2, .08, .5, 6.0, 0.0) for i in range(61)]
        visual = VisualMetrics(frames, [], [], [], [Evidence(0, .5, "BLACK", "black")], .5, .5, .7, .8)
        result = score(metadata(), visual, {"provider": "local_heuristic", "confidence": .4}, [])
        self.assertIn(result.classification, {"BAD", "AVERAGE/FIXABLE"})
        self.assertTrue(any(issue.code == "BLACK_OPENING" for issue in result.issues))

    def test_no_semantics_cannot_be_winner(self) -> None:
        frames = [FrameMetric(i * .25, 3.0, .12, .5, 6.0, 0.0) for i in range(61)]
        visual = VisualMetrics(frames, [], [], [], [], 12, .25, .95, 1.0)
        result = score(metadata(), visual, {"provider": "local_heuristic", "confidence": .4}, [])
        self.assertNotEqual(result.classification, "WINNER CANDIDATE")


if __name__ == "__main__":
    unittest.main()

