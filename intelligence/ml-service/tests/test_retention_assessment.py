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
        "assessment_scope", "policy_decision", "motion_evidence", "hook_face", "stillness_punchline",
        "text_overlay", "eye_line", "audio_silence", "color_brightness", "loop_sequel",
    }
    assert result["assessment_scope"] == "EXPERIMENT_ONLY"
    assert result["policy_decision"] == "NOT_APPLICABLE"
    assert result["hook_face"]["early_eye_contact"] is True
    assert result["text_overlay"]["opening_text_present"] is True
    assert result["loop_sequel"]["sequel_words_observed"] is True


def test_motion_evidence_is_returned_without_a_combined_score() -> None:
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
    result = assess(request)
    assert result["motion_evidence"]["motion_density"] == 1.0
    assert "final_score" not in result
