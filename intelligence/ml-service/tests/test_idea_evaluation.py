"""Source-bound IDEA regressions. Semantic providers are forbidden even if enabled."""
import copy
import json
from pathlib import Path

import pytest

from app.workflow.idea_evaluation import evaluate_idea, payload_hash
from app.rules.rule_engine import RuleEngine

SOURCES = json.loads((Path(__file__).parent / 'fixtures/arda_idea_sources.json').read_text())

@pytest.fixture(autouse=True)
def forbid_providers(monkeypatch):
    import app.llm.semantic_checks as checks
    import app.rules.rule_engine as rules
    def forbidden(*args, **kwargs):
        raise AssertionError('No provider/semantic call is authorized')
    monkeypatch.setattr(checks, 'get_provider', forbidden)
    for name in ('check_goal_is_natural', 'check_opening_problem_legible', 'count_independent_mechanics'):
        monkeypatch.setattr(rules, name, forbidden)


def run(index=0, candidate=None, batch=None, context=None):
    return evaluate_idea(candidate or copy.deepcopy(SOURCES['candidates'][index]),
                         batch or [c['payload'] for c in SOURCES['candidates']],
                         context or SOURCES['context'])

@pytest.mark.parametrize('index', range(3))
def test_real_sources_keep_all_creative_unknowns_but_execute_source_and_canonical_checks(index):
    original = copy.deepcopy(SOURCES['candidates'][index])
    result = run(index)
    assert result['candidateId'] == original['candidateId']
    assert result['sourcePayloadSha256'] == payload_hash(original['payload'])
    assert result['providerCalls'] == result['additionalCostUsd'] == 0
    assert result['eligible'] is False and result['status'] == 'PENDING_EVIDENCE'
    assert result['summary']['creativeOutcomes'] == {'PASS': 0, 'FAIL': 0, 'UNKNOWN': 10, 'NOT_APPLICABLE': 0}
    assert result['summary']['sourceBindingPasses'] == 10
    assert result['summary']['canonicalEvaluatorsInvoked'] == 6
    assert result['summary']['canonicalEvaluatorsCompleted'] == 2
    assert result['summary']['canonicalChecksUnableToComplete'] == 8
    for gate in result['gates']:
        assert gate['sourceCheck']['status'] == 'PASS'
        assert gate['evaluator']['registered']
        assert gate['evaluator']['providerDispatchAllowed'] is False
        for span in gate['sourceSpans']:
            assert original['payload'][span['field']][span['start']:span['end']] == span['quote']
    assert SOURCES['candidates'][index] == original


def test_existing_canonical_risk_and_silhouette_functions_are_really_invoked(monkeypatch):
    calls = []
    for name in ('_evaluate_producibility_003', '_evaluate_engine_silhouette_duplicate'):
        method = getattr(RuleEngine, name)
        def traced(self, ir, rule, method=method, name=name):
            calls.append(name)
            return method(self, ir, rule)
        monkeypatch.setattr(RuleEngine, name, traced)
    run()
    assert calls == ['_evaluate_producibility_003', '_evaluate_engine_silhouette_duplicate']


def test_story_measurements_are_not_run_on_empty_default_beats(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('IDEA source cannot be graded as empty STORY evidence')
    for name in ('_evaluate_progression_006', '_evaluate_concept_006', '_evaluate_payoff_004', '_evaluate_payoff_006'):
        monkeypatch.setattr(RuleEngine, name, forbidden)
    result = run()
    deferred = [g for g in result['gates'] if g['reasonCode'] == 'STORY_CONTRACT_NOT_IDEA_EVIDENCE']
    assert len(deferred) == 4
    assert all(not g['evaluator']['invoked'] and g['status'] == 'UNKNOWN' for g in deferred)


def test_missing_source_is_specific_not_a_creative_failure():
    c = copy.deepcopy(SOURCES['candidates'][1]); del c['payload']['everydayGoal']
    result = run(candidate=c)
    gate = next(g for g in result['gates'] if g['gate'] == 'VISIBLE_EVERYDAY_GOAL')
    assert gate['reasonCode'] == 'SOURCE_FIELDS_MISSING'
    assert gate['sourceCheck']['missingFields'] == ['everydayGoal']
    assert gate['status'] == 'UNKNOWN' and not gate['evaluator']['invoked']
    assert result['rejectionReasons'] == []


def test_heuristic_fragile_tags_do_not_become_hard_creative_failures():
    result = run()
    gate = next(g for g in result['gates'] if g['gate'] == 'PRODUCTION_FEASIBILITY')
    assert gate['evaluator']['outcome'] == 'FAIL'
    assert gate['status'] == 'UNKNOWN'
    assert gate['concerns']
    assert all(c['kind'] == 'HEURISTIC_CONCERN' for c in gate['concerns'])
    assert result['summary']['creativeOutcomes']['FAIL'] == 0


def test_equal_rule_strings_are_not_silhouette_duplicate_proof():
    c = copy.deepcopy(SOURCES['candidates'][0]); rule = c['payload']['impossibleRule']
    result = run(candidate=c, batch=[{'impossibleRule': rule}, {'impossibleRule': rule}])
    gate = next(g for g in result['gates'] if g['gate'] == 'ORIGINALITY_DUPLICATE_ENGINE')
    assert gate['status'] == 'UNKNOWN'
    assert any('Exact rule text repeats' in c['reason'] for c in gate['concerns'])
    assert gate['evaluator']['outcome'] == 'UNKNOWN'


@pytest.mark.parametrize('profile', ['CURIOSITY_ADVENTURE', 'EDUCATIONAL'])
def test_existing_profile_exclusions_remain_not_applicable(profile):
    ctx = copy.deepcopy(SOURCES['context']); ctx['targetConfiguration']['contentProfile'] = profile
    result = run(context=ctx)
    for rule in ('GOAL_001', 'HOOK_004'):
        gates = [g for g in result['gates'] if g['policy'] == rule]
        assert all(g['status'] == 'NOT_APPLICABLE' and g['applicability']['policyExcluded'] for g in gates)
    assert result['eligible'] is False


def test_provider_self_claims_are_not_verified_visual_or_semantic_evidence():
    c = copy.deepcopy(SOURCES['candidates'][0])
    c['payload']['visualEvidence'] = {'silhouette': {'status': 'PASS'}}
    c['payload']['semanticVerdict'] = {'status': 'PASS'}
    result = run(candidate=c)
    assert result['eligible'] is False
    assert result['summary']['creativeOutcomes']['PASS'] == 0


def test_unicode_and_whitespace_quotes_use_exact_field_offsets():
    c = copy.deepcopy(SOURCES['candidates'][0]); c['payload']['productionRisk'] = '  İ🐻 thread the fabric — e\u0301.  '
    result = run(candidate=c)
    for gate in result['gates']:
        for span in gate['sourceSpans']:
            assert c['payload'][span['field']][span['start']:span['end']] == span['quote']
        for concern in gate['concerns']:
            for span in concern.get('sourceSpans', []):
                assert c['payload'][span['field']][span['start']:span['end']] == span['quote']
    assert c['payload']['productionRisk'].endswith('  ')


def test_local_http_contract_has_no_generation_or_paid_evaluation_options():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.workflow.api import router
    app = FastAPI(); app.include_router(router)
    body = {'candidate': SOURCES['candidates'][0], 'batch': [c['payload'] for c in SOURCES['candidates']], 'context': SOURCES['context']}
    with TestClient(app) as client:
        response = client.post('/api/v1/workflow/idea-evaluation', json=body)
        assert response.status_code == 200
        assert response.json()['providerCalls'] == 0
        assert client.post('/api/v1/workflow/idea-evaluation', json={**body, 'generationAuthorized': True}).status_code == 422


def test_opening_dispatch_does_not_discard_goal_or_problem_fields(monkeypatch):
    from app.workflow.idea_evaluation import _LocalIdeaRules
    captured = []
    original = _LocalIdeaRules._semantic_check
    def traced(self, check, *args, **kwargs):
        captured.append(args)
        return original(self, check, *args, **kwargs)
    monkeypatch.setattr(_LocalIdeaRules, '_semantic_check', traced)
    run(1)
    payload = SOURCES['candidates'][1]['payload']
    opening_calls = [args for args in captured if args[0] == payload['frameZeroProblem']]
    assert len(opening_calls) == 2
    for args in opening_calls:
        assert payload['everydayGoal'] in str(args)
        assert payload['firstStaticFrame'] in str(args)
