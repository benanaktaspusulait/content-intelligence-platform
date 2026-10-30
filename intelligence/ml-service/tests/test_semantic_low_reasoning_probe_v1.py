"""Controlled reasoning variable; all request execution uses mocked transports."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Literal

import httpx
import pytest
import protected_integrity as integrity
from app.workflow import semantic_low_reasoning_probe_v1 as probe
from app.workflow import semantic_compact_capability_probe_v1 as previous
from app.workflow.creative_provider_profiles import CreativeCapabilityProvider

ROOT=Path(__file__).resolve().parents[3]
PRIOR=json.loads((ROOT/'intelligence/docs/semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl=PRIOR['baseUrl'],responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False,maxOutputTokens=128000)
DATA=json.loads((Path(__file__).parent/'fixtures/semantic_schema_integrity_full_candidate_v1.json').read_text())
TESTS=dict(noNewFailures=True,schemaIntegrityPassed=True)

@pytest.fixture(scope='module')
def planned():return probe.plan(PROFILE,deepcopy(PRIOR))


def test_discovery_exact_model_intersection_and_lowest_setting():
    d=probe.discover_reasoning()
    assert d['SDKChatCompletionsParameterPresent'] and d['adapterForwardsParameter']
    assert d['supportedSettings']==['low','medium','high','xhigh','max']
    assert 'none' in d['sdkValues'] and 'none' not in d['supportedSettings'] and 'minimal' not in d['supportedSettings']
    assert d['selectedLowest']=='low'
    assert probe.discover_reasoning(sdk_type=Literal['medium','high'])['selectedLowest']=='medium'


@pytest.mark.parametrize('override',[dict(model_contract={}),dict(sdk_parameter=False),dict(adapter_parameter=False),dict(sdk_type=Literal['none','minimal'])])
def test_unsupported_reasoning_no_request_or_claim(override,tmp_path):
    d=probe.discover_reasoning(**override)
    def forbidden(*args):raise AssertionError('No live request when effort not controllable')
    r=probe.execute(tmp_path/'run',PROFILE,PRIOR,discovery=d,runner=forbidden)
    assert r['status']=='REASONING_EFFORT_NOT_CONTROLLABLE' and r['providerCalls']==0
    assert not list(tmp_path.iterdir())


def test_no_lower_level_and_not_explicit_configuration_labels(tmp_path):
    d=probe.discover_reasoning(sdk_type=Literal['high'])
    r=probe.plan(PROFILE,PRIOR,discovery=d)
    assert r['status']=='REASONING_EFFORT_NOT_CONTROLLABLE' and r['previousReasoningEffort']=='high'
    prior=deepcopy(PRIOR);prior['arguments'].pop('reasoning_effort')
    r=probe.plan(PROFILE,prior,discovery=probe.discover_reasoning(model_contract={}))
    assert r['previousReasoningEffort']=='NOT_EXPLICITLY_CONFIGURED'


def test_exact_one_variable_diff_frozen_prompt_schema_tokens_and_timeouts(planned):
    assert planned['requestDiff']==[dict(path='/arguments/reasoning_effort',previous='high',new='low')]
    assert planned['spec']['prompt']['sha256']==previous.PROMPT_HASH
    assert planned['spec']['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']==previous.SCHEMA_HASH
    assert planned['spec']['arguments']['max_completion_tokens']==PRIOR['arguments']['max_completion_tokens']==8192
    assert planned['spec']['arguments']['messages']==PRIOR['arguments']['messages']
    assert planned['spec']['arguments']['response_format']==PRIOR['arguments']['response_format']
    assert planned['spec']['timeout']==PRIOR['timeout']
    assert planned['profile']['reasoningEffort']=='low' and PROFILE['reasoningEffort']=='high'
    assert planned['newRequest']['maxRetries']==0
    assert probe.differences(PRIOR,planned['newRequest'])==planned['requestDiff']
    old=deepcopy(planned['newRequest']);old['arguments']['reasoning_effort']='high';assert old==PRIOR
    actual=json.loads((ROOT/'intelligence/docs/semantic-compact-full-contract-probe-1-run-001/last-mile-sdk-request.json').read_text())
    assert actual==PRIOR['arguments']


@pytest.mark.parametrize('field,value',[('max_completion_tokens',4096),('model','another-model'),('messages',[]),('response_format',{})])
def test_changed_previous_request_cannot_be_silently_reconstructed(field,value):
    prior=deepcopy(PRIOR);prior['arguments'][field]=value
    with pytest.raises(ValueError):probe.plan(PROFILE,prior)


def fake_runner(raw,status='COMPLETED',error=None,calls=None):
    def run(path,profile,spec):
        if calls is not None:calls.append(1)
        assert profile['reasoningEffort']==spec['arguments']['reasoning_effort']=='low'
        (path/'response.txt').write_text(raw)
        return dict(status=status,errorClass=error,exceptionChain=[dict(exceptionClass=error)] if error else [],usage=None,SDKRequestsForwarded=1,HTTPRequestsObserved=1)
    return run


@pytest.mark.parametrize('status,error,raw,classification',[
 ('COMPLETED',None,json.dumps({'ideas':[DATA]}),'LOW_REASONING_FULL_CONTRACT_EXECUTION_PASS'),
 ('FAILED','ReadTimeout','','LOW_REASONING_FULL_CONTRACT_TIMEOUT'),
 ('FAILED','AuthenticationError','','LOW_REASONING_FULL_CONTRACT_PROVIDER_FAILURE'),
 ('COMPLETED',None,'{bad','LOW_REASONING_FULL_CONTRACT_PARSE_FAILURE'),
 ('COMPLETED',None,json.dumps({'ideas':[]}),'LOW_REASONING_FULL_CONTRACT_SCHEMA_FAILURE')])
def test_single_request_result_and_no_retry_fallback(tmp_path,monkeypatch,status,error,raw,classification):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');calls=[];path=tmp_path/'run'
    r=probe.execute(path,PROFILE,PRIOR,authorization={'file':'mock'},tests=TESTS,runner=fake_runner(raw,status,error,calls))
    assert r['executionClassification']==classification
    assert r['logicalRequestCount']==r['maximumLiveRequests']==len(calls)==1
    assert r['retries']==r['fallbacks']==r['DeepSeekCalls']==r['renders']==0
    with pytest.raises(FileExistsError):probe.execute(path,PROFILE,PRIOR,authorization={'file':'mock'},tests=TESTS,runner=fake_runner(raw,calls=calls))
    assert len(calls)==1
    if status=='COMPLETED':
        assert (path/'pre-pipeline-creative-contract.json').exists()
        if classification.endswith('EXECUTION_PASS'):assert (path/'pipeline.json').exists()
    diff=json.loads((path/'pre-request-diff.json').read_text());assert diff['requestDiff']==[dict(path='/arguments/reasoning_effort',previous='high',new='low')]


@pytest.mark.parametrize('classification,expected',[
 ('LOW_REASONING_FULL_CONTRACT_EXECUTION_PASS','REASONING_LATENCY_CONFIRMED_AS_MAJOR_FACTOR'),
 ('LOW_REASONING_FULL_CONTRACT_TIMEOUT','REASONING_REDUCTION_INSUFFICIENT'),
 ('LOW_REASONING_FULL_CONTRACT_SCHEMA_FAILURE','UNRESOLVED')])
def test_interpretation_is_conditional_not_universal_causality(classification,expected):
    assert probe.interpretation(classification)==expected


def test_credential_authorization_and_regression_preconditions(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,PRIOR,authorization={'file':'mock'},tests=TESTS)
    monkeypatch.setenv('OPENAI_API_KEY','mock-only')
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,PRIOR,tests=TESTS)
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,PRIOR,authorization={'file':'mock'},tests={'noNewFailures':False})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('mode',['success','timeout','double'])
def test_same_frozen_sdk_http_path_low_reasoning_exact_request_and_hard_cap(planned,tmp_path,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');wire=[]
    def transport(request):
        wire.append(json.loads(request.content))
        if mode=='timeout':raise httpx.ReadTimeout('mock timeout',request=request)
        return httpx.Response(200,headers={'x-request-id':'mock-http'},json=dict(id='mock-id',object='chat.completion',created=1,model='gpt-6.1-sol',choices=[dict(index=0,message=dict(role='assistant',content=json.dumps({'ideas':[DATA]})),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30,completion_tokens_details=dict(reasoning_tokens=7))))
    class MockProvider(CreativeCapabilityProvider):
        def __init__(self,*args):
            super().__init__(*args);self.client._client.close();self.client._client=httpx.Client(transport=httpx.MockTransport(transport))
        def complete(self,*args,**kwargs):
            raw=super().complete(*args,**kwargs)
            if mode=='double':super().complete(*args,**kwargs)
            return raw
    previous.worker(tmp_path,planned['profile'],planned['spec'],provider_factory=MockProvider)
    result=json.loads((tmp_path/'worker-result.json').read_text())
    assert len(wire)==result['SDKRequestsForwarded']==result['HTTPRequestsObserved']==1
    assert wire[0]==planned['newRequest']['arguments']
    assert probe.differences(PRIOR['arguments'],wire[0])==[dict(path='/reasoning_effort',previous='high',new='low')]
    if mode=='success':assert result['usage']['completion_tokens_details']['reasoning_tokens']==7 and result['status']=='COMPLETED'
    else:assert result['status']=='FAILED'
    assert result['providerReportedCostUsd'] is None


def test_all_accepted_prompt_validator_and_historical_bytes_unchanged():
    before=json.loads((ROOT/'intelligence/docs/semantic-low-reasoning-probe-v1/protected-before.json').read_text())
    integrity.assert_manifest_integrity(ROOT,{p:h for p,h in before.items() if p!='intelligence/ml-service/tests/protected_integrity.py'})
