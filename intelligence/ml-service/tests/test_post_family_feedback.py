import pytest

from app.workflow.feedback import compare_cohort, match_publication, measure_observation, review_render


def test_qa_identifies_missing_planned_event_with_grounded_dense_observation():
    plan = {
        "bindingHash": "plan",
        "events": [{"id": "ending", "start": 4, "end": 6, "description": "Box opens"}],
    }
    observed = {
        "bindingHash": "plan",
        "assetHash": "a" * 64,
        "duration": 6,
        "coverage": [4, 6],
        "events": [
            {
                "id": "ending",
                "state": "ABSENT",
                "start": 4,
                "end": 6,
                "evidenceBasis": "HUMAN_REVIEWED_CLIP",
                "reference": "clip:4-6",
            }
        ],
    }
    qa = review_render(plan, observed)
    assert (
        qa["status"] == "UNKNOWN"
    )  # Unclassified intent / missing actual-effect evidence is not an automatic repair.
    assert qa["editorialRecommendation"] == "INSUFFICIENT_EVIDENCE"
    assert qa["events"][0]["eventId"] == "ending"
    assert qa["events"][0]["start"] == 4


def test_sparse_stills_cannot_prove_motion_or_loop_and_stale_plan_is_rejected():
    plan = {"bindingHash": "plan", "events": [{"id": "move", "start": 0, "end": 6, "requiresMotion": True}]}
    observed = {
        "bindingHash": "plan",
        "assetHash": "a" * 64,
        "duration": 6,
        "coverage": [0, 6],
        "events": [
            {"id": "move", "state": "PRESENT", "start": 0, "end": 6, "evidenceBasis": "SAMPLED_STILLS"}
        ],
    }
    assert review_render(plan, observed)["status"] == "UNKNOWN"
    with pytest.raises(ValueError, match="stale"):
        review_render(plan, {**observed, "bindingHash": "old"})


def test_platform_ids_are_lossless_and_ambiguous_associations_are_not_guessed():
    rows = [
        {"platform": "INSTAGRAM", "platformContentId": "99999999999999999999", "videoId": "a"},
        {"platform": "INSTAGRAM", "platformContentId": "99999999999999999999", "videoId": "b"},
    ]
    assert match_publication("INSTAGRAM", "99999999999999999999", rows)["status"] == "AMBIGUOUS"
    assert match_publication("INSTAGRAM", "99999999999999999998", rows)["status"] == "UNMATCHED"
    assert match_publication("INSTAGRAM", "99999999999999999999", rows[:1])["videoId"] == "a"
    with pytest.raises(ValueError):
        match_publication("INSTAGRAM", 9.99999999999999e19, rows)


def test_reach_views_ratio_and_paid_distribution_are_separate():
    result = measure_observation(
        {
            "durationSeconds": 6,
            "reach": 100,
            "views": 200,
            "averageWatchSeconds": 8,
            "paidReach": 20,
            "paidWatchTimeShare": 0.8,
            "window": "LIFETIME",
            "observedAt": "2026-10-08",
            "sourceHash": "a" * 64,
            "threeSecondUniqueViewers": 70,
        }
    )
    assert result["outcome"]["reach"]["value"] == 100
    assert result["outcome"]["views"]["value"] == 200
    assert result["audience"]["averageWatchDurationRatio"]["value"] == pytest.approx(8 / 6)
    assert result["audience"]["averageWatchDurationRatio"]["definition"] != "intentional replay rate"
    assert result["audience"]["initialSwipeAwayRate"]["value"] is None
    assert result["distribution"]["paidReachShare"]["value"] == 0.2
    assert result["distribution"]["paidWatchTimeShare"]["value"] == 0.8
    assert result["horizon"] == "LIFETIME"
    assert result["fixedHorizonSnapshot"] is None


def test_lifetime_observations_are_not_fixed_horizon_comparisons():
    records = [{"window": "LIFETIME", "reach": 100}, {"window": "24H", "reach": 100}]
    assert compare_cohort(records, "24H")["included"] == 1
    assert compare_cohort(records, "24H")["excluded"] == 1
