"""Separates authored-plan recognition from input-responsive reconstruction.

The reactive double is a deterministic planning policy, NOT evidence of a real
model's creativity. It never receives a prepared plan or candidate prompt.
"""
from creative_http_test_auth import post_role
import json
from copy import deepcopy
from unittest.mock import patch

from fastapi.testclient import TestClient
from openai.types.chat import ChatCompletion
from app.main import app
from app.workflow.creative_roles import perform_role
from app.workflow.optimization_comparison import assess_comparison
from test_creative_reconstruction_v2 import fixture, plan, response, MockProvider, canonical_review


class DiagnosisDrivenPlanner:
    """Test-only substitute for model decision-making; constructs JSON afresh.

    The objective is a desired quality dimension, not an authored answer. The
    real request's diagnosis supplies the opportunities, IDs, and constraints.
    Compilation of source-specific choreography remains application code.
    """
    def __init__(self, objective_dimension):
        self.objective_dimension = objective_dimension
        self.requests = []
        self.responses = []

    def respond(self, payload):
        self.requests.append(deepcopy(payload))
        diagnosis = payload['creativeDiagnosis']
        eligible = [op for op in diagnosis['opportunities']
                    if op['dimension'] == self.objective_dimension]
        if not eligible:
            value = {'proposals': [], 'noImprovementReason':
                     'No source-grounded diagnosed opportunity supports the requested production objective.'}
        else:
            opportunity = eligible[0]
            # No beat IDs, source names, counts or completed prompts are fixtures.
            intervention = {
                'opportunityId': opportunity['opportunityId'],
                'operation': opportunity['operation'],
                'layout': 'LATERAL' if opportunity['operation'] == 'COUNTABLE_STATE_PATH' else 'DEPTH',
                'camera': 'LOCKED',
                'rationale': opportunity['expectedVisualChange'] + ' Actual visual benefit remains unverified.'}
            reconstruction = {
                'candidateId': 'candidate-a',
                'title': 'Reconstruct ' + opportunity['dimension'].lower().replace('_', ' '),
                'objective': opportunity['proposedImprovement'],
                'interventions': [intervention], 'storyChangeRequested': False}
            value = {'proposals': [{'initial': reconstruction, 'revision': None}],
                     'noImprovementReason': None}
        self.responses.append(deepcopy(value))
        return value

    def complete(self, prompt, **kwargs):
        return json.dumps(self.respond(json.loads(prompt)))


def exercise(source_fixture, dimension):
    planner = DiagnosisDrivenPlanner(dimension)
    result = perform_role('PROMPT_OPTIMIZATION', source_fixture['text'],
                          source_fixture['context'], planner, 'reactive-test-policy-not-a-model')
    for candidate in result['result']['candidates']:
        with patch('app.llm.semantic_checks.get_provider', side_effect=AssertionError('No real providers')):
            candidate['review'] = canonical_review(source_fixture, candidate)
    assessment = assess_comparison(source_fixture['text'], result['result']['candidates'],
                                   source_fixture['context'], source_fixture['baselineScore'])
    return {'planner': planner, 'result': result, 'assessment': assessment}


def test_capability_one_recognizes_an_authored_material_intervention_only():
    f = fixture()
    authored_response = response([plan()])
    result = perform_role('PROMPT_OPTIMIZATION', f['text'], f['context'],
                          MockProvider(authored_response), 'authored-response-fixture')
    candidate = result['result']['candidates'][0]
    with patch('app.llm.semantic_checks.get_provider', side_effect=AssertionError('No real providers')):
        candidate['review'] = canonical_review(f, candidate)
    assessed = assess_comparison(f['text'], [candidate], f['context'], f['baselineScore'])
    value = assessed['candidates'][0]
    assert value['classification'] == 'PLAUSIBLE_IMPROVEMENT_UNVERIFIED'
    assert value['creativeAssessment']['changeContract'][0]['originalExecution'] != value['creativeAssessment']['changeContract'][0]['newExecution']
    assert value['creativeAssessment']['provenBetter'] is False
    # This test controls the answer; it establishes no creative generation claim.
    assert result['rawProviderResult'] == authored_response


def test_reconstruction_changes_with_objective_without_a_prepared_answer():
    f = fixture()
    opening = exercise(f, 'VISUAL_STORYTELLING')
    progression = exercise(f, 'CAUSAL_PROGRESSION')
    first = opening['result']['result']['candidates'][0]
    second = progression['result']['result']['candidates'][0]
    assert first['prompt'] != second['prompt']
    assert first['reconstructionPlan']['interventions'][0]['operation'] == 'CONTACT_PLANE'
    assert second['reconstructionPlan']['interventions'][0]['operation'] == 'COUNTABLE_STATE_PATH'
    for run in (opening, progression):
        assert len(run['planner'].requests) == 1
        raw = run['planner'].responses[0]['proposals'][0]['initial']
        assert 'prompt' not in raw and 'changes' not in raw
        candidate = run['result']['result']['candidates'][0]
        assert all(anchor in candidate['prompt'] for anchor in f['context']['essentialEvents'])
        assert candidate['sourceEventCoverage']['semanticFidelity'] == 'UNKNOWN'
        assert candidate['review']['canonicalRuleEvaluation']['rulesetVersion'] == '1.11'
        assert candidate['creativeAssessment']['provenBetter'] is False


def test_reconstruction_binds_new_runtime_source_states_instead_of_replaying_mimi_answer():
    actual = fixture()
    changed = deepcopy(actual)
    # Synthetic ephemeral source; the saved Prompt 10 and approved story are untouched.
    changed['text'] = changed['text'].replace('multiply from two to four to eight',
                                             'multiply from three to six to twelve')
    before = exercise(actual, 'CAUSAL_PROGRESSION')
    after = exercise(changed, 'CAUSAL_PROGRESSION')
    a = before['result']['result']['candidates'][0]
    b = after['result']['result']['candidates'][0]
    assert 'two → four → eight' in a['prompt']
    assert 'three → six → twelve' in b['prompt'] and 'two → four → eight' not in b['prompt']
    assert a['planValidation']['sourcePromptSha256'] != b['planValidation']['sourcePromptSha256']
    assert b['sourceEventCoverage']['semanticFidelity'] == 'UNKNOWN'
    assert b['planValidation']['preservedStorySha256'] == a['planValidation']['preservedStorySha256']


def test_unavailable_objective_returns_no_plan_not_the_previous_prepared_answer():
    f = fixture()
    f['context']['openingStrategy'] = 'CURIOSITY_DISCOVERY'
    run = exercise(f, 'VISUAL_STORYTELLING')
    assert run['planner'].requests[0]['creativeDiagnosis']['openingStrategy'] == 'CURIOSITY_DISCOVERY'
    assert run['result']['result']['candidates'] == []
    assert run['result']['result']['outcome'] == 'NO_JUSTIFIED_IMPROVEMENT'
    assert run['assessment']['recommendation'] == 'KEEP_ORIGINAL'


def test_reactive_planner_through_real_role_http_adapter_uses_one_mock_sdk_call(monkeypatch):
    for key, value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true',
                       'WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'mock-reactive-policy',
                       'WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'.15',
                       'WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'.6',
                       'OPENAI_API_KEY':'mock-only'}.items():
        monkeypatch.setenv(key, value)
    f = fixture()
    planner = DiagnosisDrivenPlanner('VISUAL_STORYTELLING')
    def respond_to_sdk(**kwargs):
        payload = json.loads(kwargs['messages'][-1]['content'])
        generated = planner.respond(payload)
        return ChatCompletion.model_validate({
            'id':'mock-reactive-policy-result', 'object':'chat.completion', 'created':1,
            'model':'mock-reactive-policy',
            'choices':[{'index':0, 'message':{'role':'assistant','content':json.dumps(generated)}, 'finish_reason':'stop'}],
            'usage':{'prompt_tokens':3000,'completion_tokens':1500,'total_tokens':4500}})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.side_effect = respond_to_sdk
        client = TestClient(app)
        result = post_role(client, {
            'role':'PROMPT_OPTIMIZATION', 'text':f['text'], 'context':f['context'], 'maxCostUsd':.1}, monkeypatch)
        assert result.status_code == 200, result.text
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries'] == 0
    candidate = result.json()['result']['candidates'][0]
    with patch('app.llm.semantic_checks.get_provider', side_effect=AssertionError('No real providers')):
        candidate['review'] = canonical_review(f, candidate)
    assessment = client.post('/api/v1/workflow/optimization-assessment', json={
        'text':f['text'], 'context':f['context'], 'candidates':[candidate], 'baselineScore':f['baselineScore']})
    assert assessment.status_code == 200
    value = assessment.json()['candidates'][0]
    assert value['classification'] == 'PLAUSIBLE_IMPROVEMENT_UNVERIFIED'
    assert value['creativeAssessment']['provenBetter'] is False
