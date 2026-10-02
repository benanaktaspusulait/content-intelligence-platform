from __future__ import annotations

import unittest

from pompom_lab.fix_engine import validate_plan


class FixPlanTests(unittest.TestCase):
    def test_combines_safe_trims(self) -> None:
        start, end = validate_plan([
            {"operation": "trim_start", "start": .4},
            {"operation": "remove_black_tail", "end": 14.2},
        ], 15.0)
        self.assertEqual((start, end), (.4, 14.2))

    def test_rejects_unknown_operation(self) -> None:
        with self.assertRaises(ValueError):
            validate_plan([{"operation": "generate_new_scene"}], 15.0)

    def test_rejects_too_short_candidate(self) -> None:
        with self.assertRaises(ValueError):
            validate_plan([{"operation": "trim_start", "start": 14.5}], 15.0)


if __name__ == "__main__":
    unittest.main()

