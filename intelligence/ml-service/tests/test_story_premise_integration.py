"""Exercise the real report/workflow boundaries without providers or rendering."""

from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.api.quality import convert_quality_report
from app.assessment.pre_render_assessment import build_pre_render_assessment
from app.config import settings
from app.main import app
from app.parser.prompt_parser import parse_prompt
from app.quality.contracts import ParserMetadata, QualityReport, QualityStatus
from app.rules.rule_engine import RuleEngine
from app.scoring.quality_scorer import QualityScorer
from app.workflow.creative_validity import assess as creative_validity
from app.workflow.review import binding_fingerprint, review_prompt
from app.workflow.story_quality import analyse_story_candidates, evaluate_story_candidate
from test_story_premise_engine import STRONG, WEAK

FROZEN = json.loads(
    (
        Path(__file__).parents[2] / "data/golden/pompom-golden-v1/frozen-semantic/family10/requirements.json"
    ).read_text()
)["assets"]


def canonical(text):
    parsed = parse_prompt(text)
    # Freeze provider construction, not outcomes of the new engine.
    with patch("app.llm.semantic_checks.get_provider", side_effect=ValueError("offline test")):
        report = RuleEngine(str(settings.rules_dir / "RULESET_1.7.yaml")).evaluate(parsed.video_plan_ir)
    return parsed, report


def test_quality_report_adds_revision_gate_without_rewriting_canonical_score_or_rules():
    text = WEAK["garden_guardian"]
    parsed, report = canonical(text)
    before = deepcopy(report)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)
    value = convert_quality_report(enhanced, "1.7", video_plan_ir=parsed.video_plan_ir, source_text=text)
    engine = value.pre_render_assessment.story_premise_engine
    assert engine["status"] == "STORY_REVISION_REQUIRED"
    assert value.overall_score == before.overall_score
    assert report == before
    assert value.pre_render_assessment.story_validation["status"] == "FAIL"
    assert "STORY_PREMISE_ENGINE" in value.pre_render_assessment.render_authorization["creative_failures"]
    assert value.pre_render_assessment.family8["renderAuthorization"]["status"] != "AUTHORIZED"
    assert "passive misunderstanding" in value.pre_render_assessment.verdict
    assert value.model_dump()["pre_render_assessment"]["story_premise_engine"] == engine


def test_existing_15_second_report_is_byte_for_byte_unchanged_with_layer_enabled():
    text = (Path(__file__).parent / "fixtures/luca_sticky_ball_prompt.txt").read_text()
    parsed, report = canonical(text)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)
    enabled = convert_quality_report(
        enhanced, "1.7", video_plan_ir=parsed.video_plan_ir, source_text=text
    ).model_dump_json()
    with patch("app.workflow.story_premise_engine.assess", return_value=None):
        disabled = convert_quality_report(
            enhanced, "1.7", video_plan_ir=parsed.video_plan_ir, source_text=text
        ).model_dump_json()
    assert enabled == disabled
    assert "story_premise_engine" not in enabled


@pytest.mark.parametrize("golden_id", FROZEN)
def test_all_nine_frozen_short_form_projections_are_unchanged_by_the_layer(golden_id):
    ir = deepcopy(FROZEN[golden_id]["videoPlanIR"])
    original = deepcopy(ir)
    report = QualityReport(None, QualityStatus.NEEDS_REVISION, {}, (), "1.7", "READ_ONLY_COMPATIBILITY")
    enhanced = QualityScorer().create_enhanced_report(report, ir, ParserMetadata(1))
    enabled = convert_quality_report(enhanced, "1.7", video_plan_ir=ir).model_dump_json()
    with patch("app.workflow.story_premise_engine.assess", return_value=None):
        disabled = convert_quality_report(enhanced, "1.7", video_plan_ir=ir).model_dump_json()
    assert enabled == disabled
    assert ir == original
    assert "story_premise_engine" not in enabled


def test_long_form_success_cannot_remove_existing_gate_failures():
    text = STRONG["boogeymans_exam"]
    parsed, report = canonical(text)
    value = build_pre_render_assessment(
        parsed.video_plan_ir, parsed.metadata, report, "1.7", source_text=text
    )
    assert value["story_premise_engine"]["status"] in {"PASS", "PASS_WITH_WARNINGS"}
    assert value["render_authorization"]["status"] != "AUTHORIZED"
    assert value["story_validation"]["status"] != "PASS"
    assert value["render_authorization"]["pending_evidence_blockers"]


def test_offline_api_evaluates_concepts_without_constructing_any_provider():
    with (
        patch("app.llm.provider.get_provider", side_effect=AssertionError("No provider")),
        patch(
            "app.workflow.review._run_canonical_evaluation",
            side_effect=AssertionError("Concept-only endpoint"),
        ),
    ):
        client = TestClient(app)
        strong = client.post(
            "/api/v1/workflow/story-premise/evaluate", json={"text": STRONG["boogeymans_exam"]}
        )
        assert strong.status_code == 200
        assert strong.json()["status"] == "PASS_WITH_WARNINGS"
        weak = client.post("/api/v1/workflow/story-premise/evaluate", json={"text": WEAK["garden_guardian"]})
        assert weak.json()["status"] == "STORY_REVISION_REQUIRED"
        short = client.post(
            "/api/v1/workflow/story-premise/evaluate",
            json={"text": WEAK["garden_guardian"], "desiredDuration": 15},
        )
        assert short.json()["status"] == "NOT_APPLICABLE"
        assert (
            client.post(
                "/api/v1/workflow/story-premise/evaluate", json={"text": "x", "desiredDuration": -1}
            ).status_code
            == 422
        )


def test_candidate_stage_and_creative_validity_use_the_same_layer():
    text = WEAK["garden_guardian"]
    candidate = evaluate_story_candidate(text, {"targetDuration": 60}, "garden")
    validity = creative_validity(text, {"score": 99, "grade": "A", "status": "EVALUATED"})
    assert candidate["storyPremiseEngine"] == validity["storyPremiseEngine"]
    assert any(r["dimension"] == "storyPremise" and r["outcome"] == "FAIL" for r in candidate["risks"])
    assert validity["canonicalScore"] == 99 and validity["canonicalGrade"] == "A"
    assert not validity["realProviderCapabilityClaimAllowed"]
    assert "storyPremiseEngine" not in creative_validity("Pip runs.", {"score": 99})


def test_workflow_blocks_weak_long_form_without_changing_canonical_result():
    request = {
        "prompt": WEAK["garden_guardian"],
        "sourceId": "test",
        "sourceVersion": "1",
        "profile": "post-family-v1",
        "contentProfile": "CURIOSITY_ADVENTURE",
        "desiredDuration": 60,
        "generator": "AUTO",
        "settings": {},
        "references": [],
        "canonicalRulesetVersion": "1.7",
    }
    frozen = {
        "status": "EVALUATED",
        "score": 99,
        "grade": "A",
        "passedRules": [],
        "failedRules": [],
        "unknownRules": [],
        "notApplicableRules": [],
        "rulesetVersion": "1.7",
    }
    with patch("app.workflow.review._run_canonical_evaluation", return_value=deepcopy(frozen)):
        value = review_prompt(request, {})
    assert value["canonicalRuleEvaluation"] == {**frozen, "contentProfile": "CURIOSITY_ADVENTURE"}
    assert value["storyPremiseEngine"]["status"] == "STORY_REVISION_REQUIRED"
    assert any(
        r["source"] == "STORY_PREMISE_ENGINE" for r in value["family8"]["renderAuthorization"]["reasons"]
    )
    assert any("STORY_REVISION_REQUIRED" in r["text"] for r in value["operatorReport"])
    assert value["family8"]["renderAuthorization"]["status"] != "AUTHORIZED"


def test_story_mode_is_bound_but_absent_mode_preserves_existing_fingerprint():
    request = {"prompt": "Text.", "canonicalRulesetVersion": "1.7"}
    assert binding_fingerprint(request) == binding_fingerprint({**request, "storyType": None})
    assert binding_fingerprint(request) != binding_fingerprint({**request, "storyType": "POMPOM_STORIES"})


def test_actual_story_collection_exposes_engine_and_prefers_active_arc():
    result = analyse_story_candidates(
        [
            {"candidateId": "garden", "text": WEAK["garden_guardian"]},
            {"candidateId": "exam", "text": STRONG["boogeymans_exam"]},
        ],
        {"targetDuration": 60},
    )
    assert result["candidates"][0]["assessment"]["storyPremiseEngine"]["status"] == "STORY_REVISION_REQUIRED"
    assert result["recommendation"]["bestCandidateId"] == "exam"
    assert result["recommendation"]["editorialOnly"] and not result["recommendation"]["renderAuthorized"]


def test_story_review_cannot_recommend_passive_story_even_if_all_canonical_rows_pass():
    from app.workflow.creative_roles import perform_role

    required = (
        "reviewId",
        "sourceRequestId",
        "sourceFingerprint",
        "reviewModel",
        "reviewModelVersion",
        "reviewPolicyVersion",
        "reviewTimestamp",
        "diversityAssessment",
        "comparativeFindings",
        "recommendationReason",
        "overallConcerns",
        "usageAndCost",
        "evidenceLimitations",
        "revisionComparison",
    )
    response = {k: "fixture" for k in required}
    response.update(
        reviewStatus="COMPLETED",
        candidateReviews=[{"candidateId": "garden"}],
        recommendedCandidateId="garden",
    )

    class FixtureProvider:
        def complete(self, *args, **kwargs):
            return json.dumps(response)

    rules = (
        "GOAL_001",
        "MINI_STORY_LOCK",
        "GOAL_VISIBLE_EARLY",
        "CONCEPT_007",
        "CONCEPT_008",
        "PROGRESSION_006",
        "ESCALATION_005",
        "PAYOFF_001",
    )
    canonical_pass = {"status": "EVALUATED", "passedRules": [{"ruleId": k, "outcome": "PASS"} for k in rules]}
    with patch("app.workflow.review._run_canonical_evaluation", return_value=canonical_pass):
        result = perform_role(
            "STORY_REVIEW",
            "Fixture collection",
            {
                "targetDuration": 60,
                "candidates": [{"candidateId": "garden", "text": WEAK["garden_guardian"]}],
            },
            FixtureProvider(),
            "offline-fixture",
        )["result"]
    assert result["recommendedCandidateId"] is None
    assert result["mandatoryStoryGate"][0]["status"] == "FAIL"
    assert set(result["mandatoryStoryGate"][0]["rules"].values()) == {"PASS"}
