"""Deterministic IDEA contract tests: no provider/network adapter is constructed."""
import json
import pytest
from app.workflow.creative_roles import perform_role

class Provider:
    def __init__(self, response):
        self.response = response
        self.calls = 0
    def complete(self, *args, **kwargs):
        self.calls += 1
        return json.dumps(self.response)

def candidate(index):
    return {key: f'{key} fixture {index}' for key in (
        'candidateId', 'title', 'concept', 'firstStaticFrame', 'viewerQuestion',
        'discovery', 'payoff', 'productionRisk', 'everydayGoal', 'frameZeroProblem',
        'impossibleRule', 'proposedProgression')}

def test_one_response_retains_three_independent_structured_ideas():
    expected = {'candidates': [candidate(i) for i in range(3)]}
    provider = Provider(expected)
    result = perform_role('IDEA', 'Arda fixture brief', {'requestedAlternativeCount': 3}, provider, 'fixture')
    assert result['role'] == 'IDEA'
    assert result['result'] == expected
    assert provider.calls == 1
    assert 'alternatives' not in result['result']

@pytest.mark.parametrize('response', [{}, {'candidates': []}, {'candidates': [candidate(0)]},
    {'candidates': [candidate(0), candidate(1), {}]}, {'candidates': 'invalid'}])
def test_incomplete_response_is_rejected_without_retry(response):
    provider = Provider(response)
    with pytest.raises(ValueError):
        perform_role('IDEA', 'Arda fixture brief', {'requestedAlternativeCount': 3}, provider, 'fixture')
    assert provider.calls == 1

def test_single_idea_contract_remains_compatible():
    expected = candidate(1)
    for field in ('everydayGoal', 'frameZeroProblem', 'impossibleRule', 'proposedProgression'):
        del expected[field]
    provider = Provider(expected)
    assert perform_role('IDEA', 'brief', {'requestedAlternativeCount': 1}, provider, 'fixture')['result'] == expected
    assert provider.calls == 1


def test_batch_requires_explicit_goal_trouble_rule_and_progression():
    for field in ('everydayGoal', 'frameZeroProblem', 'impossibleRule', 'proposedProgression'):
        incomplete = candidate(1)
        del incomplete[field]
        provider = Provider({'candidates': [candidate(0), incomplete, candidate(2)]})
        with pytest.raises(ValueError):
            perform_role('IDEA', 'brief', {'requestedAlternativeCount': 3}, provider, 'fixture')
        assert provider.calls == 1
