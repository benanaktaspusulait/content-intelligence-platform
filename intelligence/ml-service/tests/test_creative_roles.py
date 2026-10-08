import json
import pytest
from app.workflow.creative_roles import perform_role, run_paid_role, role_readiness

class FixtureProvider:
    def __init__(self, result): self.result = result; self.calls = []
    def complete(self, prompt, system='', temperature=0, image=None):
        self.calls.append((json.loads(prompt), system))
        return json.dumps(self.result)

@pytest.mark.parametrize('role,result,provider_name', [
    ('STORY', {'alternatives': ['A grounded story']}, 'deepseek'),
    ('BUILD_PROMPT', {'prompt': 'A grounded prompt'}, 'openai'),
    ('MINIMAL_REPAIR', {'patches': [{'start': 0, 'end': 3, 'sourceQuote': 'CUT', 'replacement': 'Hold'}]}, 'openai'),
])
def test_roles_route_explicitly_and_never_self_validate(role, result, provider_name):
    provider = FixtureProvider(result)
    response = perform_role(role, 'CUT at end', {'retrievedLessons': [{'recordId': 'verified'}]}, provider, 'configured-model')
    assert response['provider'] == provider_name
    assert response['validationStatus'] == 'NOT_VALIDATED'
    assert response['visualInspected'] is False
    assert len(provider.calls) == 1
    assert provider.calls[0][0]['context']['retrievedLessons'][0]['recordId'] == 'verified'

def test_invalid_patch_quote_is_rejected():
    provider = FixtureProvider({'patches': [{'start': 0, 'end': 3, 'sourceQuote': 'wrong', 'replacement': 'Hold'}]})
    with pytest.raises(ValueError): perform_role('MINIMAL_REPAIR', 'CUT', {}, provider, 'configured')

def test_paid_roles_require_explicit_server_enablement(monkeypatch):
    monkeypatch.delenv('WORKFLOW_CREATIVE_ROLES_ENABLED', raising=False)
    assert role_readiness()['enabled'] is False
    with pytest.raises(ValueError, match='disabled'): run_paid_role('STORY', 'Idea', {}, 1)

def test_visual_input_is_rejected_before_any_provider_call():
    provider = FixtureProvider({'prompt': 'text'})
    with pytest.raises(ValueError, match='text-only'): perform_role('BUILD_PROMPT', 'Story', {'video': 'clip'}, provider, 'configured')
    assert not provider.calls


def test_cost_ceiling_is_checked_before_constructing_paid_provider(monkeypatch):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_INPUT_USD_PER_MILLION', '1000')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_OUTPUT_USD_PER_MILLION', '1000')
    with pytest.raises(ValueError, match='cost ceiling'):
        run_paid_role('BUILD_PROMPT', 'Story', {}, 0.001)
