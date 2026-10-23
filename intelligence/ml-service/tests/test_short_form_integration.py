"""Opt-in boundaries, frozen compatibility, CPQ and independent long-form reports."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.api.quality import convert_quality_report
from app.main import app
from app.quality.contracts import ParserMetadata, QualityReport, QualityStatus
from app.scoring.quality_scorer import QualityScorer
from app.workflow.creative_prompt_quality import assess as cpq
from app.workflow.creative_validity import assess as creative_validity
from app.workflow.review import binding_fingerprint, review_prompt
from app.workflow.story_quality import analyse_story_candidates, evaluate_story_candidate
from test_short_form_engine import CASES, ROOT, WINNER, OPT_IN, OLD_CASES, evaluate
from test_story_premise_integration import canonical, FROZEN


@pytest.mark.parametrize('golden_id', FROZEN)
def test_all_nine_frozen_reports_remain_byte_identical_when_not_opted_in(golden_id):
    ir = deepcopy(FROZEN[golden_id]['videoPlanIR'])
    original = deepcopy(ir)
    report = QualityReport(None, QualityStatus.NEEDS_REVISION, {}, (), '1.7', 'READ_ONLY_COMPATIBILITY')
    enhanced = QualityScorer().create_enhanced_report(report, ir, ParserMetadata(1))
    value = convert_quality_report(enhanced, '1.7', video_plan_ir=ir).model_dump_json()
    with patch('app.workflow.short_form_engine.assess', return_value=None):
        disabled = convert_quality_report(enhanced, '1.7', video_plan_ir=ir).model_dump_json()
    assert value == disabled
    assert 'short_form_engine' not in value
    assert ir == original


def test_opt_in_prompt_projection_adds_only_independent_report():
    ir = deepcopy(FROZEN['upside-chair-01']['videoPlanIR'])
    report = QualityReport(None, QualityStatus.NEEDS_REVISION, {}, (), '1.7', 'READ_ONLY_COMPATIBILITY')
    before = deepcopy(report)
    enhanced = QualityScorer().create_enhanced_report(report, ir, ParserMetadata(1))
    baseline = convert_quality_report(enhanced, '1.7', video_plan_ir=ir, source_text=WINNER).model_dump()
    opted = convert_quality_report(enhanced, '1.7', video_plan_ir=ir,
                                 source_text=WINNER, story_context=OPT_IN).model_dump()
    short = opted['pre_render_assessment'].pop('short_form_engine')
    assert short == evaluate(WINNER)
    assert opted == baseline
    assert report == before


def test_same_source_can_return_both_engines_without_one_rewriting_the_other():
    text = OLD_CASES['strong']['boogeymans_exam']
    parsed, report = canonical(text)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)
    baseline = convert_quality_report(enhanced, '1.7', video_plan_ir=parsed.video_plan_ir, source_text=text).model_dump()
    opted = convert_quality_report(enhanced, '1.7', video_plan_ir=parsed.video_plan_ir, source_text=text, story_context=OPT_IN).model_dump()
    assert opted['pre_render_assessment']['story_premise_engine'] == baseline['pre_render_assessment']['story_premise_engine']
    assert opted['pre_render_assessment']['story_premise_engine']['score'] == 91
    assert opted['pre_render_assessment']['short_form_engine']['status'] in {'REJECT', 'REVISION_REQUIRED'}


def test_concept_endpoint_never_constructs_provider_or_runs_canonical_engine():
    with patch('app.llm.provider.get_provider', side_effect=AssertionError('No providers')), patch(
        'app.workflow.review._run_canonical_evaluation', side_effect=AssertionError('No canonical run')):
        client = TestClient(app)
        response = client.post('/api/v1/workflow/short-form/evaluate', json={'text': WINNER})
        assert response.status_code == 200
        assert response.json() == evaluate(WINNER)
        assert client.post('/api/v1/workflow/short-form/evaluate', json={'text': 'x', 'desiredDuration': -1}).status_code == 422
        assert client.post('/api/v1/workflow/short-form/evaluate', json={'text': 'x', 'inventedScore': 100}).status_code == 422


def test_cpq_reports_independent_original_candidate_without_activating_uncalibrated_grades():
    payload = {'originalPrompt': CASES['activity_without_progress'], 'candidatePrompt': CASES['structurally_different'], 'durationSeconds': 15}
    baseline = cpq(payload)
    opted = cpq({**payload, **OPT_IN})
    short = opted.pop('shortFormEngine')
    assert opted == baseline
    assert short['original']['status'] == 'REVISION_REQUIRED'
    assert short['candidate']['status'] == 'PASS'
    assert opted['absoluteQuality']['aggregateScore'] is None
    assert not opted['renderAuthorized']
    response = TestClient(app).post('/api/v1/workflow/creative-prompt-quality/assess', json={**payload, **OPT_IN})
    assert response.status_code == 200
    assert response.json()['shortFormEngine'] == short


def test_candidates_and_creative_validity_share_report_without_regrading_canonical():
    text = CASES['activity_without_progress']
    candidate = evaluate_story_candidate(text, OPT_IN, 'busy')
    validity = creative_validity(text, {'score': 99, 'grade': 'A'}, context=OPT_IN)
    assert candidate['shortFormEngine'] == validity['shortFormEngine'] == evaluate(text)
    assert any(r['dimension'] == 'shortForm' and r['severity'] == 'BLOCKING' for r in candidate['risks'])
    assert validity['canonicalScore'] == 99
    assert not validity['realProviderCapabilityClaimAllowed']


def test_short_form_collection_compares_causal_plans_not_long_arcs_or_motion():
    result = analyse_story_candidates([{'candidateId': 'busy', 'text': CASES['activity_without_progress']},
                                       {'candidateId': 'clear', 'text': CASES['structurally_different']}], OPT_IN)
    assert result['candidates'][0]['assessment']['shortFormEngine']['status'] == 'REVISION_REQUIRED'
    assert result['recommendation']['bestCandidateId'] == 'clear'
    assert result['recommendation']['editorialOnly']
    assert not result['recommendation']['renderAuthorized']


def test_workflow_addition_never_clears_canonical_gates():
    request = {'prompt': WINNER, 'sourceId': 'fixture', 'sourceVersion': '1', 'profile': 'post-family-v1',
               'contentProfile': 'ABSURD_PHYSICS', 'desiredDuration': 17, 'generator': 'AUTO',
               'settings': {}, 'references': [], 'canonicalRulesetVersion': '1.7'}
    canonical_result = {'status': 'EVALUATED', 'score': 35, 'grade': 'F', 'rulesetVersion': '1.7',
                        'passedRules': [], 'failedRules': [{'ruleId': 'EXISTING_FAILURE', 'outcome': 'FAIL'}],
                        'unknownRules': [], 'notApplicableRules': []}
    with patch('app.workflow.review._run_canonical_evaluation', return_value=deepcopy(canonical_result)):
        before = review_prompt(request, {})
        opted = review_prompt({**request, **OPT_IN}, {})
    assert opted['shortFormEngine']['status'] == 'PASS_WITH_WARNINGS'
    assert opted['canonicalRuleEvaluation'] == before['canonicalRuleEvaluation']
    assert opted['family8']['renderAuthorization'] == before['family8']['renderAuthorization']
    assert any(r['label'] == 'SHORT FORM' for r in opted['operatorReport'])


def test_opt_in_is_bound_and_absence_preserves_legacy_binding():
    base = {'prompt': WINNER, 'canonicalRulesetVersion': '1.7'}
    assert binding_fingerprint(base) == binding_fingerprint({**base, 'shortFormEvaluation': None})
    assert binding_fingerprint(base) == binding_fingerprint({**base, 'shortFormEvaluation': False})
    assert binding_fingerprint(base) != binding_fingerprint({**base, **OPT_IN})


def test_accepted_long_engine_and_all_historical_evidence_files_keep_pre_change_hashes():
    before = json.loads((ROOT / 'docs/short-form-engine-v1/immutable-before.json').read_text())
    workspace = Path(__file__).parents[3]
    assert set(before) == {str(p.relative_to(workspace)) for root in (ROOT / "data/golden", ROOT / "docs/story-premise-engine-v1") for p in root.rglob("*") if p.is_file()} | {"intelligence/ml-service/app/workflow/story_premise_engine.py"}
    for path, sha in before.items():
        assert hashlib.sha256((workspace / path).read_bytes()).hexdigest() == sha, path
