from fastapi.testclient import TestClient

from app.main import app
from app.workflow.creative_prompt_quality import assess, fingerprint, validate_calibration


def test_canonical_b_does_not_become_creative_grade_and_visual_evidence_is_not_required():
    result = assess({
        "originalPrompt": "Mimi reaches for the cabinet and a note sticks to her finger.",
        "candidatePrompt": "At 0s, Mimi reaches for the cabinet. The note visibly sticks to her finger, then doubles after each pull. End on Mimi collecting toys.",
        "contentProfile": "ABSURD_PHYSICS", "generator": "SEEDANCE_2_0_MINI", "durationSeconds": 15,
        "canonicalFindings": {"rulesetVersion": "1.11", "grade": "B", "score": 88.4},
    })
    assert result["absoluteQuality"]["grade"] is None
    assert result["gradingStatus"] == "CALIBRATION_INCOMPLETE"
    assert result["sourceFidelity"]["decision"] == "UNKNOWN"
    assert result["visualAdherence"] == "UNVERIFIED"
    assert result["audienceEffect"] == "UNMEASURED"
    assert result["renderAuthorized"] is False
    assert result["canonicalValidation"]["grade"] == "B"
    assert len(result["dimensions"]) == 6
    assert all(d["calibratedScore"] is None for d in result["dimensions"])


def test_verbosity_does_not_create_material_improvement_or_grade():
    original = "Mimi reaches for the note."
    candidate = original + " " + "Carefully beautifully clearly visibly" * 30
    result = assess({"originalPrompt": original, "candidatePrompt": candidate})
    assert result["relativeImprovement"]["promptFingerprintChanged"] is True
    assert result["relativeImprovement"]["classification"] == "UNVERIFIED"
    assert "do not establish material improvement" in result["relativeImprovement"]["note"]
    assert result["absoluteQuality"]["grade"] is None


def test_calibration_readiness_rejects_missing_independent_reviews_and_bad_fingerprint():
    records = [{
        "exampleId": "x", "promptText": "Approved prompt", "promptSha256": fingerprint("tampered"),
        "sourceStoryId": "story", "sourceRevision": "rev", "contentProfile": "ABSURD_PHYSICS",
        "generator": "SEEDANCE_2_0_MINI", "durationSeconds": 15, "reviewerJudgments": [],
        "sourceFidelityEvidence": {"decision": "UNKNOWN"}, "reviewerProvenance": {"reviewerId": "r1"},
        "reviewMethodVersion": "v1", "reviewedAt": "2026-10-15T00:00:00Z", "split": "CALIBRATION",
    }]
    report = validate_calibration(records)
    assert report["state"] == "CALIBRATION_INCOMPLETE"
    assert report["activated"] is False
    assert report["gradeThresholdsJustified"] is False
    assert any("fingerprint mismatch" in p for p in report["problems"])
    assert any("Independent source-fidelity decision unavailable" in p for p in report["problems"])
    assert any("Fewer than two distinct reviewers" in p for p in report["problems"])


def test_assess_endpoint_rejects_client_supplied_fidelity_or_grade():
    client = TestClient(app)
    response = client.post("/api/v1/workflow/creative-prompt-quality/assess", json={
        "originalPrompt": "original", "candidatePrompt": "candidate", "independentFidelity": {"decision": "PASS"}, "grade": "A"
    })
    assert response.status_code == 422


def test_assess_endpoint_returns_preview_without_grade_activation():
    client = TestClient(app)
    response = client.post("/api/v1/workflow/creative-prompt-quality/assess", json={
        "originalPrompt": "original", "candidatePrompt": "candidate", "canonicalFindings": {"grade": "A", "score": 92}
    })
    assert response.status_code == 200
    assert response.json()["gradingStatus"] == "CALIBRATION_INCOMPLETE"
    assert response.json()["absoluteQuality"]["grade"] is None
