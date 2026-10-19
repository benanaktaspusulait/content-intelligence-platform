import pytest

from app.workflow.creative_roles import (
    CreativeRoleFailure,
    _parse_role_json_response,
    run_paid_role,
)


class ProviderReceipt:
    last_response_metadata = {'finishReason': 'stop'}
    last_usage = {'prompt_tokens': 37, 'completion_tokens': 19, 'total_tokens': 56}


@pytest.mark.parametrize('raw', [
    '{"alternatives": []}',
    '```json\n{"alternatives": []}\n```',
    '```\n{"alternatives": []}\n```',
])
def test_story_json_response_accepts_object_and_complete_markdown_fences(raw):
    provider = ProviderReceipt()
    assert _parse_role_json_response(raw, 'STORY', provider) == {'alternatives': []}
    assert provider.last_raw_response == raw
    assert provider.last_usage == {'prompt_tokens': 37, 'completion_tokens': 19, 'total_tokens': 56}


def test_story_json_response_rejects_truncated_json_and_keeps_provider_receipt():
    provider = ProviderReceipt()
    provider.last_response_metadata = {'finishReason': 'length'}
    raw = '{"alternatives":[{"candidateId":"candidate-1"'

    with pytest.raises(ValueError, match='truncated.*finish_reason=length'):
        _parse_role_json_response(raw, 'STORY', provider)

    assert provider.last_raw_response == raw
    assert provider.last_response_metadata['finishReason'] == 'length'
    assert provider.last_usage['completion_tokens'] == 19


@pytest.mark.parametrize('raw', [
    'Here is the JSON: {"alternatives": []}',
    '{"alternatives": [}',
    '```json\n{"alternatives": []}',
])
def test_story_json_response_rejects_invalid_or_unfenced_surrounding_text(raw):
    provider = ProviderReceipt()
    with pytest.raises(ValueError, match='invalid JSON'):
        _parse_role_json_response(raw, 'STORY', provider)
    assert provider.last_raw_response == raw


def test_story_json_response_rejects_duplicate_story_plan_after_candidate_without_repair():
    provider = ProviderReceipt()
    raw = '{"alternatives":[{"candidateId":"candidate-1","storyPlan":{"recommendedRuntimeSeconds":22}},"storyPlan":{"recommendedRuntimeSeconds":22}}]}'

    with pytest.raises(ValueError, match='invalid JSON'):
        _parse_role_json_response(raw, 'STORY', provider)

    assert provider.last_raw_response == raw


def test_story_json_response_recovers_only_one_redundant_candidate_closer_and_keeps_raw():
    provider = ProviderReceipt()
    raw = '{"alternatives":[{"candidateId":"candidate-1","storyPlan":{"recommendedRuntimeSeconds":22}}}]}'
    parsed = _parse_role_json_response(raw, 'STORY', provider)
    assert parsed == {'alternatives': [{'candidateId': 'candidate-1', 'storyPlan': {'recommendedRuntimeSeconds': 22}}]}
    assert provider.last_raw_response == raw
    assert provider.last_json_recovery['status'] == 'RECOVERED_ONE_REDUNDANT_CANDIDATE_CLOSER'
    assert provider.last_json_recovery['rawPreserved'] is True
    offset = provider.last_json_recovery['removedCharacterOffset']
    assert raw[offset] == '}'
    assert provider.last_json_recovery['correctedDocumentStrictlyParsed'] is True


def test_story_json_response_does_not_recover_duplicate_keys_or_extra_trailing_content():
    duplicate = ProviderReceipt()
    with pytest.raises(ValueError, match='invalid JSON'):
        _parse_role_json_response('{"alternatives":[{"candidateId":"a","candidateId":"b"}]}', 'STORY', duplicate)
    assert duplicate.last_raw_response == '{"alternatives":[{"candidateId":"a","candidateId":"b"}]}'

    trailing = ProviderReceipt()
    raw = '{"alternatives":[{"candidateId":"a"}]}} trailing'
    with pytest.raises(ValueError, match='invalid JSON'):
        _parse_role_json_response(raw, 'STORY', trailing)
    assert trailing.last_raw_response == raw


def test_story_parse_failure_returns_raw_response_usage_and_finish_reason(monkeypatch):
    import app.workflow.creative_roles as roles

    class DeepSeekFixture(ProviderReceipt):
        last_request_started = False
        last_provider_response = {'id': 'request-123'}
        last_response_metadata = {'requestId': 'request-123', 'model': 'deepseek-chat', 'finishReason': 'stop'}
        last_raw_response = '{"alternatives":'

        def __init__(self, model):
            self.model = model

    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
    monkeypatch.setenv('WORKFLOW_STORY_MODEL', 'deepseek-chat')
    monkeypatch.setenv('WORKFLOW_STORY_INPUT_USD_PER_MILLION', '0.3')
    monkeypatch.setenv('WORKFLOW_STORY_OUTPUT_USD_PER_MILLION', '1.2')
    monkeypatch.setattr(roles, 'DeepSeekTextProvider', DeepSeekFixture)

    original_perform_role = roles.perform_role

    def reject_after_response(*args, **kwargs):
        if args[4] == 'PREVIEW_ONLY_NO_PROVIDER':
            return original_perform_role(*args, **kwargs)
        provider = args[3]
        provider.last_request_started = True
        raise ValueError('Story returned invalid JSON')

    monkeypatch.setattr(roles, 'perform_role', reject_after_response)
    with pytest.raises(CreativeRoleFailure) as failure:
        run_paid_role('STORY', 'Write a story.', {'attemptId': 'attempt-1'}, 0.2)

    receipt = failure.value.diagnostics
    assert receipt['providerDispatched'] is True
    assert receipt['providerResponseReturned'] is True
    assert receipt['rawProviderResponse'] == '{"alternatives":'
    assert receipt['finishReason'] == 'stop'
    assert receipt['usage']['completion_tokens'] == 19
    assert receipt['actualCostUsd'] is not None

