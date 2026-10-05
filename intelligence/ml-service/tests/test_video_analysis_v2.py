import numpy as np

from app.video import SampledFrame, _dark_candidates, _intervals


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
