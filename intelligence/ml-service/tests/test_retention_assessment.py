from app.retention_assessment import RetentionAssessmentRequest, assess


def test_retention_assessment_returns_strict_metric_shape_without_platform_data() -> None:
    request = RetentionAssessmentRequest.model_validate(
        {
            "storyboard_frames": [
                {
                    "timestampSeconds": 0.0,
                    "hasChildFace": True,
                    "eyeContact": True,
                    "looksAtCamera": True,
                    "brightness": 145,
                    "saturation": 0.7,
                    "motionDensity": 0.8,
                    "textOverlayAreaRatio": 0.2,
                },
                {
                    "timestampSeconds": 2.0,
                    "looksAtOtherCharacter": True,
                    "brightness": 145,
                    "saturation": 0.7,
                    "motionDensity": 0.5,
                },
            ],
            "transcript_with_timestamps": [{"startSeconds": 1.8, "endSeconds": 2.2, "text": "Again tomorrow."}],
            "audio_analysis": {"silenceGaps": []},
            "existing_metrics": {
                "opening_motion": 0.8,
                "overall_motion": 0.7,
                "motion_density": 0.8,
                "ending_motion": 0.6,
                "first_last_similarity": 0.7969,
            },
        }
    )

    result = assess(request)

    assert set(result) == {
        "motion_score", "hook_face", "stillness_punchline", "text_overlay", "eye_line",
        "audio_silence", "color_brightness", "loop_sequel", "final_score", "prediction", "fix_1", "fix_2",
    }
    assert result["hook_face"]["score"] == 100
    assert result["text_overlay"]["score"] == 100
    assert result["loop_sequel"]["has_sequel_hook"] is True
    assert 0 <= result["final_score"] <= 100


def test_full_motion_density_is_penalized_without_using_platform_performance() -> None:
    request = RetentionAssessmentRequest.model_validate(
        {
            "storyboard_frames": [{"timestampSeconds": 0.0}],
            "existing_metrics": {
                "opening_motion": 1.0,
                "overall_motion": 1.0,
                "motion_density": 1.0,
                "ending_motion": 1.0,
                "first_last_similarity": 0.8,
            },
        }
    )
    assert assess(request)["motion_score"] == 80.0
