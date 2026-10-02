from __future__ import annotations

import unittest

from pompom_lab.frame_analysis import FrameMetric, VisualMetrics
from pompom_lab.models import Evidence
from pompom_lab.rescue import build_rescue


def visual() -> VisualMetrics:
    frames = [FrameMetric(index * .25, 1.5, .08, .5, 6.0, 0.0) for index in range(61)]
    return VisualMetrics(frames, [], [], [], [], 3.5, .25, .82, .84)


def base() -> dict:
    return {
        "scores": {"first_frame_hook": 5.5, "final_twist": 5.8},
        "issues": [], "confidence": .51,
    }


def heuristic() -> dict:
    return {
        "provider": "local_heuristic", "model": "opencv+ffmpeg", "confidence": .38,
        "creative_engines": ["UNVERIFIED"], "viewer_keeps_watching_because": "Unverified.",
        "main_problem": "Needs semantic review.", "do_not_change": [], "alternative_pattern": "Preserve alternatives.",
        "opening_assessment": "Unverified opening.", "final_three_seconds": "Unverified ending.",
        "cta_assessment": "Unverified CTA.",
        "reveal_spoiled_by_cold_open": None, "new_footage_needed": False, "new_footage_prompt": None,
    }


class RescueTests(unittest.TestCase):
    def test_observed_winner_is_preserved_as_is(self) -> None:
        result = build_rescue("video.mp4", "abc", 15.0, visual(), heuristic(), base(), [{"platform": "Facebook", "views": 60000}])
        self.assertEqual(result.classification, "A")
        self.assertEqual(result.fix_first, [])
        self.assertTrue(result.performance_override)

    def test_no_semantic_engine_does_not_claim_prime(self) -> None:
        result = build_rescue("video.mp4", "abc", 15.0, visual(), heuristic(), base(), [])
        self.assertNotEqual(result.classification, "A")
        self.assertTrue(any(edit.variant == "cold_open" and edit.semantic_risk for edit in result.fix_first))

    def test_fatal_issue_holds_even_with_motion(self) -> None:
        bad = base()
        bad["issues"] = [{"severity": "fatal"}]
        result = build_rescue("video.mp4", "abc", 15.0, visual(), heuristic(), bad, [])
        self.assertEqual(result.classification, "E")
        self.assertEqual(result.publishing_use, "HOLD")


if __name__ == "__main__":
    unittest.main()
