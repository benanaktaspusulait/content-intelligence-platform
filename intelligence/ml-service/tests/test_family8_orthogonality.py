"""RED Task 1 contract tests for Family 8 orthogonal projections."""

from __future__ import annotations

from app.assessment.family8_projection import project_family8, render_admission_allowed


def facts(
    *,
    creative_score: float | None = 92.0,
    creative_grade: str | None = "A",
    evidence_status: str = "COMPLETE",
    evaluation_coverage: float | None = 1.0,
    family_scores: dict[str, float | None] | None = None,
    legacy_readiness: str | None = "READY_TO_RENDER",
    reasons: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "creativeQuality": {
            "creativeScore": creative_score,
            "creativeGrade": creative_grade,
            "familyScores": family_scores or {"concept_strength": creative_score},
        },
        "evidenceCompleteness": {
            "status": evidence_status,
            "evaluationCoverage": evaluation_coverage,
            "aggregation": {"scoredCount": 2, "denominator": 2},
        },
        "legacy": {"readiness": legacy_readiness},
        "authorizationReasons": reasons or [],
    }


def reason(code: str, source: str = "TEST") -> dict[str, object]:
    return {"code": code, "source": source, "message": code, "references": []}


def test_complete_evidence_and_valid_creative_quality_are_authorized() -> None:
    result = project_family8(facts())
    assert result["creativeQuality"]["creativeGrade"] == "A"
    assert result["evidenceCompleteness"]["status"] == "COMPLETE"
    assert result["renderAuthorization"]["status"] == "AUTHORIZED"
    assert result["renderAuthorization"]["reasons"] == []


def test_partial_evidence_blocks_pending_without_degrading_creative_grade() -> None:
    result = project_family8(
        facts(
            evidence_status="PARTIAL",
            evaluation_coverage=0.5,
            reasons=[reason("REQUIRED_EVIDENCE_MISSING")],
        )
    )
    assert result["creativeQuality"]["creativeGrade"] == "A"
    assert result["evidenceCompleteness"]["status"] == "PARTIAL"
    assert result["renderAuthorization"]["status"] == "BLOCKED_PENDING_EVIDENCE"


def test_parser_or_service_failure_blocks_technical_without_creative_failure() -> None:
    result = project_family8(
        facts(
            evidence_status="INCOMPLETE",
            reasons=[reason("PARSER_TIMEOUT", "PARSER")],
        )
    )
    assert result["creativeQuality"]["creativeGrade"] == "A"
    assert result["renderAuthorization"]["status"] == "BLOCKED_TECHNICAL_FAILURE"


def test_creative_failure_with_complete_evidence_blocks_creative() -> None:
    result = project_family8(
        facts(
            creative_score=40.0,
            creative_grade="F",
            reasons=[reason("CREATIVE_BLOCKER", "RULE_ENGINE")],
        )
    )
    assert result["evidenceCompleteness"]["status"] == "COMPLETE"
    assert result["renderAuthorization"]["status"] == "BLOCKED_CREATIVE_FAILURE"


def test_creative_and_pending_reasons_are_both_preserved() -> None:
    result = project_family8(
        facts(
            creative_score=40.0,
            creative_grade="F",
            evidence_status="PARTIAL",
            reasons=[reason("CREATIVE_BLOCKER"), reason("REQUIRED_EVIDENCE_MISSING")],
        )
    )
    assert [item["code"] for item in result["renderAuthorization"]["reasons"]] == [
        "CREATIVE_BLOCKER",
        "REQUIRED_EVIDENCE_MISSING",
    ]
    assert result["renderAuthorization"]["status"] == "BLOCKED_CREATIVE_FAILURE"


def test_technical_reason_has_highest_primary_status_but_keeps_all_reasons() -> None:
    result = project_family8(
        facts(
            creative_score=40.0,
            creative_grade="F",
            evidence_status="INCOMPLETE",
            reasons=[
                reason("CREATIVE_BLOCKER"),
                reason("REQUIRED_EVIDENCE_MISSING"),
                reason("ASSESSMENT_TECHNICAL_FAILURE"),
            ],
        )
    )
    assert {item["code"] for item in result["renderAuthorization"]["reasons"]} == {
        "CREATIVE_BLOCKER",
        "REQUIRED_EVIDENCE_MISSING",
        "ASSESSMENT_TECHNICAL_FAILURE",
    }
    assert result["renderAuthorization"]["status"] == "BLOCKED_TECHNICAL_FAILURE"


def test_null_creative_score_stays_null() -> None:
    result = project_family8(
        facts(
            creative_score=None,
            creative_grade=None,
            evidence_status="INCOMPLETE",
            evaluation_coverage=0.0,
        )
    )
    assert result["creativeQuality"]["creativeScore"] is None
    assert result["creativeQuality"]["creativeGrade"] is None


def test_null_family_score_remains_visible_with_reason() -> None:
    result = project_family8(
        facts(
            family_scores={"producibility": None},
            evidence_status="INCOMPLETE",
            evaluation_coverage=0.0,
            reasons=[reason("NO_SCORED_ITEMS")],
        )
    )
    assert "producibility" in result["creativeQuality"]["familyScores"]
    assert result["creativeQuality"]["familyScores"]["producibility"] is None
    assert result["evidenceCompleteness"]["aggregation"]["scoredCount"] == 2


def test_legacy_ready_does_not_authorize_when_render_is_blocked() -> None:
    result = project_family8(
        facts(
            evidence_status="PARTIAL",
            legacy_readiness="READY_TO_RENDER",
            reasons=[reason("REQUIRED_EVIDENCE_MISSING")],
        )
    )
    assert result["legacy"]["readiness"] == "READY_TO_RENDER"
    assert result["renderAuthorization"]["status"] == "BLOCKED_PENDING_EVIDENCE"
    assert render_admission_allowed(result["renderAuthorization"]) is False


def test_missing_null_or_unknown_authorization_fails_closed() -> None:
    assert render_admission_allowed(None) is False
    assert render_admission_allowed({}) is False
    assert render_admission_allowed({"status": None}) is False
    assert render_admission_allowed({"status": "UNKNOWN"}) is False
    assert render_admission_allowed({"status": "BLOCKED_PENDING_EVIDENCE"}) is False
    assert render_admission_allowed({"status": "AUTHORIZED"}) is True
