import numpy as np

from app.video import (
    V4SampledFrame,
    _v4_low_motion_candidates,
    _v4_target_times,
    _v4_visual_novelty,
)


def _interval(start: float, end: float, motion: float) -> dict:
    return {"startTime": start, "endTime": end, "smoothedMotion": motion}


def test_v4_targets_are_uniform_and_include_duration_endpoint() -> None:
    targets = _v4_target_times(1.17)

    assert targets[0] == 0.0
    assert targets[-1] == 1.17
    assert all(abs(second - first - 0.25) < 1e-6 for first, second in zip(targets, targets[1:-1], strict=False))


def test_v4_low_motion_uses_hysteresis_and_merges_short_gap() -> None:
    intervals = [
        _interval(0.0, 0.25, 0.4),
        _interval(0.25, 0.5, 0.1),
        _interval(0.5, 0.75, 0.1),
        _interval(0.75, 1.0, 0.25),
        _interval(1.0, 1.25, 0.1),
    ]

    candidates = _v4_low_motion_candidates(intervals)

    assert len(candidates) == 1
    assert candidates[0]["mergedGapCount"] == 1
    assert candidates[0]["entryThreshold"] < candidates[0]["exitThreshold"]


def test_v4_novelty_separates_identical_and_changed_states() -> None:
    base = np.zeros((32, 32, 3), dtype=np.uint8)
    changed = base.copy()
    changed[8:24, 8:24] = 255
    samples = [
        V4SampledFrame(base, 0.0, 0.0, 0.0),
        V4SampledFrame(base, 1.25, 1.25, 0.0),
        V4SampledFrame(changed, 2.5, 2.5, 0.0),
    ]

    novelty = _v4_visual_novelty(samples, 2.5)

    assert novelty["status"] == "AVAILABLE"
    assert novelty["points"][0]["novelty"] < novelty["points"][1]["novelty"]
