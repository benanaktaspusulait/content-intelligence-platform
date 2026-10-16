"""Offline transports and exact saved Mimi bindings; never real source judgments."""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from app.workflow import owner_machine_pilot as pilot
from app.workflow.creative_provider_profiles import CreativeCapabilityProvider, profile

ROOT = Path(__file__).resolve().parents[3]
REAL = ROOT / 'intelligence/docs/cpq-first-real-ai-experiment-evidence'
OFFLINE = ROOT / 'intelligence/docs/cpq-source-fidelity-output-budget-evidence'


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv('POMPOM_DATA_ROOT', str(ROOT / 'intelligence/data'))
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-transport-fixture-not-a-real-key')
    monkeypatch.delenv('CPQ_SOURCE_FIDELITY_REASONING_EFFORT', raising=False)
    monkeypatch.setenv('CPQ_PILOT_REAL_ENABLED', 'false')


def body():
    saved = json.loads((REAL / 'source-fidelity-durable-request.json').read_text())
    auth = copy.deepcopy(saved['authorization_payload'])
    auth['reasoningEffort'] = 'low'
    auth['idempotencyKey'] = 'NEW_OFFLINE_TEST_ONLY_AUTHORIZATION'
    return {'requestId': 'NEW_OFFLINE_TEST_ONLY_REQUEST', 'authorization': auth, 'input': saved['input']}


def response_fixture():
    return json.loads((OFFLINE / 'representative-unknown-response.MOCK.json').read_text())


def sdk_response(text, finish='stop', usage=None):
    if usage is None:
        usage = {'prompt_tokens': 6161, 'completion_tokens': 3147,
                 'completion_tokens_details': {'reasoning_tokens': 100}}
    return SimpleNamespace(id='MOCK_TRANSPORT_NOT_A_REAL_PROVIDER_REQUEST', model='gpt-6.1-sol',
        usage=SimpleNamespace(model_dump=lambda: usage),
        choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=text))])


def execute_mock(response):
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value = response
        result = pilot.execute(body())
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries'] == 0
        args = sdk.return_value.chat.completions.create.call_args.kwargs
        assert args['model'] == 'gpt-6.1-sol' and args['reasoning_effort'] == 'low'
        assert args['max_completion_tokens'] == 4000
        assert args['response_format']['json_schema']['strict'] is True
        return result, args


def test_source_low_is_scoped_and_critics_and_optimization_stay_high():
    before = {p: profile(p) for p in ('openai-escalation', 'deepseek-primary')}
    cfg = pilot.source_profile('openai-escalation')
    assert cfg['reasoningEffort'] == 'low'
    assert before == {p: profile(p) for p in before}
    assert all(c['reasoningEffort'] == 'high' for c in before.values())
    caps = pilot.capabilities()
    assert caps['sourceFidelityConfiguration']['openai-escalation']['supportedReasoningEfforts'] == ['low', 'medium', 'high', 'xhigh', 'max']
    assert caps['officialGrading'] == 'INACTIVE' and caps['realEnabled'] is False


@pytest.mark.parametrize('effort', ['none', 'minimal', 'unsupported', 'LOW'])
def test_unsupported_effort_fails_before_sdk_construction(monkeypatch, effort):
    monkeypatch.setenv('CPQ_SOURCE_FIDELITY_REASONING_EFFORT', effort)
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        with pytest.raises(ValueError, match='Unsupported reasoning effort'):
            pilot.execute(body())
        cfg = profile('openai-escalation'); cfg['reasoningEffort'] = effort
        with pytest.raises(ValueError, match='Unsupported reasoning effort'):
            CreativeCapabilityProvider(cfg, 4000, 5)
        sdk.assert_not_called()


def test_unknown_model_cannot_inherit_an_assumed_effort(monkeypatch):
    monkeypatch.setattr(pilot, 'profile', lambda _: {'provider': 'openai', 'model': 'unknown-future-model'})
    with pytest.raises(ValueError, match='capabilities unverified'):
        pilot.source_profile('anything')


@pytest.mark.parametrize('effort', ['low', 'medium', 'high', 'xhigh', 'max'])
def test_documented_efforts_are_validated_explicitly(monkeypatch, effort):
    monkeypatch.setenv('CPQ_SOURCE_FIDELITY_REASONING_EFFORT', effort)
    assert pilot.source_profile('openai-escalation')['reasoningEffort'] == effort


@pytest.mark.parametrize('effort', [None, 'high', 'minimal'])
def test_new_authorization_must_bind_source_effort(effort):
    req = body()
    if effort is None:
        req['authorization'].pop('reasoningEffort')
    else:
        req['authorization']['reasoningEffort'] = effort
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        with pytest.raises(ValueError, match='Fresh source authorization'):
            pilot.execute(req)
        sdk.assert_not_called()


def test_real_four_fingerprints_and_source_settings_remain_exact():
    saved = json.loads((REAL / 'prepared-pilot.json').read_text())['snapshot']['subjects']
    by_hash = {s['promptSha256']: s for s in saved}
    req = body()
    assert len(req['input']['packets']) == len(by_hash) == 4
    for p in req['input']['packets']:
        assert hashlib.sha256(p['prompt'].encode()).hexdigest() == p['promptSha256']
        subject = by_hash[p['promptSha256']]
        assert p['approvedStory'] == subject['approvedStory']['text']
        assert p['productionSettings'] == subject['productionSettings']
        assert p['changedBeats'] == subject['changedBeats']
        assert hashlib.sha256(p['approvedStory'].encode()).hexdigest() == 'df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b'


def test_complete_representative_json_and_all_event_evidence_survive_transport():
    fixture = response_fixture()
    out, args = execute_mock(sdk_response(json.dumps(fixture, ensure_ascii=False, separators=(',', ':'))))
    assert out['executionStatus'] == 'COMPLETED' and out['usageAccountingStatus'] == 'COMPLETE'
    assert out['effectiveRequestConfiguration'] == {'reasoningEffort': 'low', 'maxOutputTokens': 4000, 'automaticRetries': False}
    assert out['costUsd'] == pytest.approx(.0468725)
    assert out['evidenceType'] == 'MACHINE_REVIEW' and 'grade' not in out
    assert json.loads(args['messages'][1]['content']) == body()['input']
    assert 'compact JSON' in args['messages'][0]['content']
    for result in out['results']:
        assert result['decision'] == 'UNKNOWN' and result['omissions']
        assert len(result['mappings']) == {'Q01': 12, 'Q03': 13, 'Q02': 12, 'Q04': 11}[result['neutralId']]
        assert {m['anchor'] for m in result['mappings']} == set(pilot.ANCHORS)
        assert {m['beatId'] for m in result['mappings']} == {f'beat_0{i}' for i in range(1, 6)}
        assert 'MOCK' in result['rationale']
    assert all(k not in out for k in ('renderAuthorized', 'promptVersion', 'ownerDecision'))


def test_representative_visible_json_fits_bounded_envelope():
    # Optional diagnostic tool only; no application dependency or token-count API.
    tiktoken = pytest.importorskip('tiktoken')
    compact = json.dumps(response_fixture(), ensure_ascii=False, separators=(',', ':'))
    count = len(tiktoken.get_encoding('o200k_base').encode(compact))
    assert count == 3047 and count + 100 < 4000
    # This tokenizer proxy and mocked reasoning allocation do not predict the real model.


@pytest.mark.parametrize('text,finish,reasoning,category', [
    ('', 'length', 4000, 'REASONING_BUDGET_EXHAUSTED'),
    ('{"results":[', 'length', 3000, 'VISIBLE_OUTPUT_TRUNCATED'),
    ('', 'length', None, 'OUTPUT_BUDGET_EXHAUSTED_VISIBLE_EMPTY'),
    ('', 'stop', 10, 'EMPTY_VISIBLE_OUTPUT'),
    ('{"results":[', 'stop', 10, 'PROVIDER_OR_RESPONSE_CONTRACT_FAILED'),
])
def test_empty_truncated_or_partial_outputs_are_rejected_once_and_accounted(text, finish, reasoning, category):
    usage = {'prompt_tokens': 6161, 'completion_tokens': 4000,
             'completion_tokens_details': {'reasoning_tokens': reasoning}}
    out, _ = execute_mock(sdk_response(text, finish, usage))
    assert out['executionStatus'] == 'FAILED_OR_AMBIGUOUS' and out['results'] == []
    assert out['rawResponse'] == text and out['failureCategory'] == category
    assert out['usage'] == usage and out['costUsd'] == pytest.approx(.0554025)
    assert out['usageAccountingStatus'] == 'COMPLETE'


@pytest.mark.parametrize('usage', [{}, {'prompt_tokens': 100}, {'prompt_tokens': True, 'completion_tokens': 100}])
def test_incomplete_or_invalid_usage_is_not_zero_cost(usage):
    out, _ = execute_mock(sdk_response(json.dumps(response_fixture()), usage=usage))
    assert out['executionStatus'] == 'FAILED_OR_AMBIGUOUS'
    assert out['costUsd'] is None and out['usageAccountingStatus'] == 'INCOMPLETE'
    assert out['failureCategory'] == 'USAGE_ACCOUNTING_INCOMPLETE'


def test_provider_usage_cannot_exceed_the_authorized_token_limit():
    out, _ = execute_mock(sdk_response(json.dumps(response_fixture()), usage={'prompt_tokens': 6161, 'completion_tokens': 4001}))
    assert out['executionStatus'] == 'FAILED_OR_AMBIGUOUS' and not out['results']


def test_transport_failure_is_not_claimed_as_reasoning_exhaustion_or_zero_cost():
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.side_effect = TimeoutError('Offline simulated transport failure')
        out = pilot.execute(body())
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries'] == 0
    assert out['executionStatus'] == 'FAILED_OR_AMBIGUOUS'
    assert out['failureCategory'] == 'PROVIDER_RESPONSE_UNAVAILABLE'
    assert out['usageAccountingStatus'] == 'INCOMPLETE' and out['costUsd'] is None


@pytest.mark.parametrize('defect', ['missing_anchor', 'changed_beat', 'conflict', 'addition', 'omission', 'bad_source_quote', 'bad_prompt_quote'])
def test_fidelity_gates_remain_strict(defect):
    req = body(); fixture = response_fixture(); row = fixture['results'][0]
    row.update(decision='PASS', omissions=[])
    if defect == 'missing_anchor':row['mappings'] = [m for m in row['mappings'] if m['anchor'] != 'PHYSICAL_RULE']
    if defect == 'changed_beat':
        for m in row['mappings']:m['beatId'] = 'beat_05'
    if defect == 'conflict':row['conflict'] = True
    if defect == 'addition':row['additions'] = ['MOCK unsupported new event']
    if defect == 'omission':row['omissions'] = ['MOCK missing approved note text']
    if defect == 'bad_source_quote':row['mappings'][0]['sourceQuote'] = 'INVENTED SOURCE'
    if defect == 'bad_prompt_quote':row['mappings'][0]['promptQuote'] = 'INVENTED PROMPT'
    if defect.startswith('bad_'):
        with pytest.raises(ValueError, match='citations differ'):
            pilot.validate(fixture, req['input'])
    else:
        assert pilot.validate(fixture, req['input'])[0]['decision'] == 'UNKNOWN'
