from app.video import _temporal_profile


def _interval(start: float, end: float, motion: float, rate: float = 0.05) -> dict:
    return {
        "startTime": start,
        "endTime": end,
        "deltaTSeconds": end - start,
        "visualChangeRate": rate,
        "normalizedMotionIntensity": motion,
    }


def test_profile_is_duration_aware_and_stable_for_equal_motion() -> None:
    profile = _temporal_profile([_interval(0, 1, 0.8), _interval(1, 3, 0.8)], 3)

    assert len(profile["segments"]) >= 4
    assert profile["variation"] == "STEADY"
    assert profile["activityDrops"] == []


def test_profile_locates_a_mid_video_drop_with_timestamps() -> None:
    intervals = [
        _interval(0, 1, 0.9),
        _interval(1, 2, 0.9),
        _interval(2, 3, 0.2),
        _interval(3, 4, 0.9),
    ]

    drops = _temporal_profile(intervals, 4)["activityDrops"]

    assert drops
    assert drops[0]["startSeconds"] >= 2.0
    assert drops[0]["endSeconds"] > drops[0]["startSeconds"]
    assert drops[0]["classification"] == "UNMAPPED_DROP"


def test_profile_does_not_use_global_opening_difference_as_a_drop() -> None:
    profile = _temporal_profile([_interval(0, 1, 0.9), _interval(1, 4, 0.4)], 4)

    assert all(drop["startSeconds"] > 0 for drop in profile["activityDrops"])


def test_profile_exposes_duration_aware_segment_measurements_and_spikes() -> None:
    intervals = [_interval(index, index + 1, value) for index, value in enumerate([0.2, 0.2, 0.8, 0.8, 0.2])]

    profile = _temporal_profile(intervals, 5)
    segment = profile["segments"][0]

    assert profile["version"] == "temporal-motion-profile-v2"
    assert {"peakMotion", "minimumMotion", "motionVariability", "coverage", "validIntervalCount"} <= segment.keys()
    assert profile["activitySpikes"]
    assert profile["activitySpikes"][0]["durationSeconds"] > 0


def test_profile_ignores_gradual_trend_and_short_noise() -> None:
    gradual = _temporal_profile([_interval(index, index + 1, value) for index, value in enumerate([0.9, 0.8, 0.7, 0.6, 0.5])], 5)
    noise = _temporal_profile([_interval(index, index + 1, value) for index, value in enumerate([0.9, 0.9, 0.2, 0.9, 0.9])], 5)

    assert gradual["activityDrops"] == []
    assert noise["activityDrops"] == []
