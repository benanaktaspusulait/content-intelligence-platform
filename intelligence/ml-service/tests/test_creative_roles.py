import json
import pytest
from app.workflow.creative_roles import perform_role, run_paid_role, role_readiness

class FixtureProvider:
    def __init__(self, result): self.result = result; self.calls = []
    def complete(self, prompt, system='', temperature=0, image=None):
        self.calls.append((json.loads(prompt), system))
        return json.dumps(self.result)


def test_creative_role_accepts_json_fenced_by_configured_text_endpoint():
    provider = FixtureProvider({'alternatives': ['A grounded story']})
    provider.complete = lambda prompt, system='', temperature=0, image=None: '```json\n{"alternatives":["A grounded story"]}\n```'
    response = perform_role('STORY', 'Idea', {}, provider, 'configured-model')
    assert response['result']['alternatives'] == ['A grounded story']


def test_creative_role_reports_empty_provider_response():
    provider = FixtureProvider({})
    provider.complete = lambda prompt, system='', temperature=0, image=None: ''
    with pytest.raises(ValueError, match='empty JSON response'):
        perform_role('STORY', 'Idea', {}, provider, 'configured-model')


def test_story_candidates_are_bounded_when_provider_overproduces():
    provider = FixtureProvider({'alternatives': ['one', 'two', 'three', 'four']})
    response = perform_role('STORY', 'Idea', {}, provider, 'configured-model')
    assert len(response['result']['alternatives']) == 3

@pytest.mark.parametrize('role,result,provider_name', [
    ('STORY', {'alternatives': ['A grounded story']}, 'deepseek'),
    ('BUILD_PROMPT', {'prompt': 'TITLE / FORMAT 15 seconds 9:16.\n\nVISUAL STYLE grounded.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera close shot; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO and sound.\n\nNEGATIVE CONSTRAINTS.\n\nFINAL CUT hard cut.', 'productionPlan': {'sourceIdentity': {'storyRevisionId': 'fixture'}, 'creativeObjective': 'Make the note movement readable.', 'characterBindings': [{'name': 'Mimi', 'status': 'supplied'}], 'visualExecution': {'openingState': 'Mimi is visible.', 'beats': [{'time': '0-3s', 'framing': 'close shot', 'action': 'Mimi holds a note.', 'staging': 'cabinet behind her.', 'consequence': 'setup visible.'}, {'time': '3-6s', 'framing': 'medium shot', 'action': 'note flips.', 'staging': 'in front of cabinet.', 'consequence': 'note reaches face.'}, {'time': '6-10s', 'framing': 'medium shot', 'action': 'Mimi reacts.', 'staging': 'center frame.', 'consequence': 'escalation.'}, {'time': '10-13s', 'framing': 'wide shot', 'action': 'notes multiply.', 'staging': 'around Mimi.', 'consequence': 'coverage grows.'}, {'time': '13-15s', 'framing': 'wide shot', 'action': 'Mimi is covered.', 'staging': 'cabinet behind her.', 'consequence': 'hard cut.'}], 'mechanism': 'Notes move visibly.', 'continuity': 'Mimi remains visible.', 'endingState': 'Hard cut.'}, 'productionConstraints': {'duration': 15, 'aspectRatio': '9:16'}, 'intentClassification': {'status': 'PRESERVE'}, 'evidenceLimitations': [], 'generatorRisks': [], 'referencePlan': {'status': 'NO_REFERENCE_SUPPLIED'}}}, 'openai'),
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


def test_build_prompt_canonicalizes_provider_prompt_alias():
    result = {
        'productionPrompt': 'TITLE / FORMAT 15 seconds 9:16.\n\nVISUAL STYLE bright.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera close shot; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO playful sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.',
        'productionPlan': {
            'sourceIdentity': {}, 'creativeObjective': 'Make the action readable.',
            'characterBindings': [], 'visualExecution': {
                'openingState': 'Mimi is visible.', 'mechanism': 'Notes move visibly.',
                'continuity': 'Mimi remains visible.', 'endingState': 'Hard cut.',
                'beats': [{'time': time, 'framing': 'medium shot', 'action': 'Action.', 'staging': 'Center frame.', 'consequence': 'The beat advances.'}
                          for time in ('0-3s', '3-6s', '6-10s', '10-13s', '13-15s')]
            },
            'productionConstraints': {}, 'intentClassification': {}, 'evidenceLimitations': ['No visual reference supplied'],
            'generatorRisks': ['Keep the notes readable.'], 'referencePlan': {}
        }
    }
    response = perform_role('BUILD_PROMPT', 'Mimi opens a box.', {}, FixtureProvider(result), 'configured-model')
    assert response['result']['prompt'].startswith('TITLE / FORMAT')


def test_build_prompt_rejects_conflicting_confirmed_aspect_ratio():
    result = {
        'prompt': 'TITLE / FORMAT 15 seconds 16:9.\n\nVISUAL STYLE bright.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO playful sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.',
        'productionPlan': {'sourceIdentity': {}, 'creativeObjective': 'x', 'characterBindings': [], 'visualExecution': {'openingState': 'x', 'mechanism': 'x', 'continuity': 'x', 'endingState': 'x', 'beats': [{'time': t, 'framing': 'x', 'action': 'x', 'staging': 'x', 'consequence': 'x'} for t in ('0-3s','3-6s','6-10s','10-13s','13-15s')]}, 'productionConstraints': {'aspectRatio': '16:9'}, 'intentClassification': {}, 'evidenceLimitations': ['x'], 'generatorRisks': ['x'], 'referencePlan': {}}
    }
    with pytest.raises(ValueError, match='confirmed settings'):
        perform_role('BUILD_PROMPT', 'Mimi story', {'targetConfiguration': {'aspectRatio': '9:16'}}, FixtureProvider(result), 'configured')

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


def test_paid_repair_enforces_json_at_provider_boundary(monkeypatch):
    from unittest.mock import MagicMock, patch
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-key')
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_MINIMAL_REPAIR_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_MINIMAL_REPAIR_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_MINIMAL_REPAIR_OUTPUT_USD_PER_MILLION', '0.6')
    content = json.dumps({'patches': [{'start': 0, 'end': 3, 'sourceQuote': 'CUT', 'replacement': 'Hold'}]})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        client = sdk.return_value
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))], usage=None)
        result = run_paid_role('MINIMAL_REPAIR', 'CUT at end', {}, 0.01)
        request = client.chat.completions.create.call_args.kwargs
        assert request['response_format'] == {'type': 'json_object'}
        assert request['max_tokens'] == 2000
        client.chat.completions.create.assert_called_once()
        assert result['result']['patches'][0]['sourceQuote'] == 'CUT'
        assert result['validationStatus'] == 'NOT_VALIDATED'
