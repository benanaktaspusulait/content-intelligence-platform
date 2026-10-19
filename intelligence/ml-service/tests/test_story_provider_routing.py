"""Native STORY dispatch: real adapters over mocked HTTP, no paid requests."""
import json
import httpx
import pytest
from openai import OpenAI
from app.llm.openai_provider import OpenAIProvider
from app.workflow import creative_roles as roles


def setup(monkeypatch, *, finish='stop', body=None, fail=False):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('WORKFLOW_STORY_MODEL', 'existing-deepseek')
    monkeypatch.setenv('WORKFLOW_STORY_INPUT_USD_PER_MILLION', '.28')
    monkeypatch.setenv('WORKFLOW_STORY_OUTPUT_USD_PER_MILLION', '.42')
    monkeypatch.setattr(roles, 'analyse_story_candidates', lambda *args: {'candidates': []})
    requests = []
    candidate = {'candidateId': 'candidate-1', 'title': 'Seat', 'protagonistCharacterId': 'arda-id',
                 'text': 'Arda prepares a giant picnic place. DURATION: 15 seconds. 0.0-15.0 SEC: Arda welcomes a supporting tortoise.'}
    def handler(request):
        requests.append(json.loads(request.content))
        if fail:
            raise httpx.ReadTimeout('mock timeout', request=request)
        return httpx.Response(200, json={'id': 'completion-1', 'model': 'gpt-6-sol',
            'choices': [{'index': 0, 'finish_reason': finish, 'message': {'role': 'assistant', 'content': body if body is not None else json.dumps({'alternatives': [candidate]})}}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}})
    provider = OpenAIProvider(api_key='test-key', model='gpt-6-sol')
    provider.client = OpenAI(api_key='test-key', max_retries=0,
                            http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(roles, 'OpenAIProvider', lambda **kwargs: provider)
    context = {'storyProvider': 'OPENAI', 'requestedAlternativeCount': 1,
               'targetConfiguration': {'duration': 15}, 'sourceIdeaDraftId': 'idea-1', 'sourceIdeaRevision': 1,
               'characterRecord': {'id': 'arda-id', 'name': 'Arda'},
               'canonicalCharacterRegistry': [{'id': 'arda-id', 'name': 'Arda'}]}
    return provider, requests, context


def test_openai_native_short_story_retains_contract_receipt_and_source(monkeypatch):
    provider, requests, context = setup(monkeypatch)
    result = roles.run_paid_role('STORY', 'The original saved picnic idea', context, .10)
    assert len(requests) == 1
    wire = requests[0]
    assert wire['model'] == 'gpt-6-sol' and wire['reasoning_effort'] == 'none'
    assert wire['max_completion_tokens'] == 4000
    assert 'temperature' not in wire and 'max_tokens' not in wire
    assert roles._LONG_FORM_STORY_CONTRACT not in wire['messages'][0]['content']
    assert json.loads(wire['messages'][1]['content'])['context']['targetConfiguration']['duration'] == 15
    assert result['provider'] == 'openai'
    assert result['requestedModel'] == result['returnedModel'] == 'gpt-6-sol'
    assert result['providerRequest']['messages'] == wire['messages']
    assert result['providerApiResponse']['id'] == 'completion-1'
    assert result['usage']['total_tokens'] == 150
    assert result['actualCostUsd'] == pytest.approx(.00075)
    assert result['storyRevisions'][0]['sourceIdeaDraftId'] == 'idea-1'
    assert len(result['storyRevisions'][0]['textSha256']) == 64
    assert result['result']['canonicalIdentityValidation'][0]['status'] == 'REGISTRY_PASS'
    assert result['validationStatus'] == 'NOT_VALIDATED'


@pytest.mark.parametrize('options', [{'finish': 'length'}, {'body': '{broken'}])
def test_rejected_openai_response_preserves_real_provenance_no_retry(monkeypatch, options):
    _, requests, context = setup(monkeypatch, **options)
    with pytest.raises(roles.CreativeRoleFailure) as caught:
        roles.run_paid_role('STORY', 'Picnic', context, .1)
    diag = caught.value.diagnostics
    assert len(requests) == 1 and diag['provider'] == 'openai'
    assert diag['providerResponseReturned'] and diag['rawProviderResponse']
    assert diag['providerRequest']['model'] == 'gpt-6-sol'
    assert diag['usage']['total_tokens'] == 150 and diag['actualCostUsd'] > 0


def test_timeout_is_unknown_usage_without_retry_or_fallback(monkeypatch):
    _, requests, context = setup(monkeypatch, fail=True)
    with pytest.raises(roles.CreativeRoleFailure) as caught:
        roles.run_paid_role('STORY', 'Picnic', context, .1)
    diag = caught.value.diagnostics
    assert len(requests) == 1 and diag['providerDispatched']
    assert diag['usage'] is None and diag['actualCostUsd'] is None
    assert diag['providerRequest']['model'] == 'gpt-6-sol'
    assert not diag['retrySafe']


def test_bad_provider_and_insufficient_budget_never_dispatch(monkeypatch):
    _, requests, context = setup(monkeypatch)
    with pytest.raises(ValueError, match='provider'):
        roles.run_paid_role('STORY', 'Picnic', {**context, 'storyProvider': 'OTHER'}, .1)
    with pytest.raises(ValueError, match='ceiling'):
        roles.run_paid_role('STORY', 'Picnic', context, .000001)
    assert requests == []


def test_default_still_constructs_deepseek_adapter(monkeypatch):
    provider, requests, context = setup(monkeypatch)
    del context['storyProvider']
    selected = []
    def factory(model):
        selected.append(model)
        return provider
    monkeypatch.setattr(roles, 'DeepSeekTextProvider', factory)
    result = roles.run_paid_role('STORY', 'Picnic', context, .1)
    assert selected == ['existing-deepseek'] and result['provider'] == 'deepseek'
    assert len(requests) == 1
