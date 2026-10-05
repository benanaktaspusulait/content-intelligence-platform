import numpy as np

from app.video import (
    MOTION_SCORE_WEIGHTS,
    SampledFrame,
    _dark_candidates,
    _intervals,
    calculate_motion_heuristic_score,
    normalize_motion_intensity,
)


def _frame(value: int, requested: float, actual: float | None = None) -> SampledFrame:
    image = np.full((8, 8, 3), value, dtype=np.uint8)
    return SampledFrame(image, requested, actual)


def test_intervals_use_decoder_timestamps_and_normalize_change_rate() -> None:
    intervals = _intervals([
        _frame(0, 0.0, 0.0),
        _frame(255, 0.5, 1.0),
    ])

    assert intervals[0]["deltaTSeconds"] == 1.0
    assert intervals[0]["rawFrameDifference"] == 1.0
    assert intervals[0]["visualChangeRate"] == 1.0
    assert intervals[0]["normalizedMotionIntensityPreClamp"] == 8.333333333333334
    assert intervals[0]["normalizedMotionIntensity"] == 1.0
    assert intervals[0]["normalizationSaturated"] is True


def test_v3_motion_weights_are_normalized_and_similarity_is_not_an_input() -> None:
    assert sum(MOTION_SCORE_WEIGHTS.values()) == 1.0
    baseline = calculate_motion_heuristic_score(0.4, 0.2, 0.3, 0.1)
    assert baseline == 28.89
    assert calculate_motion_heuristic_score(0.5, 0.2, 0.3, 0.1) > baseline
    assert calculate_motion_heuristic_score(0.4, 0.3, 0.3, 0.1) > baseline
    assert calculate_motion_heuristic_score(0.4, 0.2, 0.4, 0.1) > baseline
    assert calculate_motion_heuristic_score(0.4, 0.2, 0.3, 0.2) > baseline


def test_motion_normalization_is_bounded_monotonic_and_non_saturating_below_reference() -> None:
    values = [normalize_motion_intensity(rate)[1] for rate in (0.0, 0.012, 0.035, 0.08, 0.12, 0.3)]
    assert values == sorted(values)
    assert values[:4] == [0.0, 0.1, 0.2916666666666667, 0.6666666666666667]
    assert values[-2:] == [1.0, 1.0]
    assert all(0.0 <= value <= 1.0 for value in values)


def test_dark_candidates_distinguish_near_black_from_dark() -> None:
    candidates = _dark_candidates([
        _frame(0, 0.0, 0.0),
        _frame(30, 0.5, 0.5),
        _frame(100, 1.0, 1.0),
    ])

    assert [candidate["kind"] for candidate in candidates] == [
        "NEAR_BLACK_FRAME",
        "DARK_FRAME_CANDIDATE",
    ]


def test_decode_failure_is_not_encoded_as_a_dark_frame() -> None:
    candidates = _dark_candidates([_frame(100, 0.0, None)])

    assert candidates == []
