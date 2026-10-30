"""Offline prompt intent, retained policy, unchanged judges and capped transport."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import httpx
import pytest
import protected_integrity as integrity
from app.workflow import semantic_compact_1_probe_v1 as probe
from app.workflow import semantic_low_reasoning_probe_v1 as low
from app.workflow.semantic_concept_prompt_v2_compact import CompactPromptRequest,compact_prompt,size_metrics
from app.workflow.semantic_concept_prompt_v2_compact_1 import Compact1PromptRequest,compact1_prompt,construct_native_request,inspect_response
from app.workflow.semantic_concept_generation import GenerationRequest
from app.workflow.semantic_prompt_v2_experiment import analyze
from app.workflow.creative_provider_profiles import CreativeCapabilityProvider
from app.workflow.semantic_native_schema_integrity_v1 import native_response_format

ROOT=Path(__file__).resolve().parents[3];DOCS=ROOT/'intelligence/docs';FIX=Path(__file__).parent/'fixtures'
HIGH=json.loads((DOCS/'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
LOW=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl=LOW['baseUrl'],responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False,maxOutputTokens=128000)
POLICY=json.loads((FIX/'semantic_prompt_v2_compact_1_policy.json').read_text())
MOCKS=json.loads((FIX/'semantic_prompt_v2_compact_1_mocks.json').read_text())['cases']
TESTS=dict(noNewFailures=True,schemaIntegrityPassed=True)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('External calls forbidden in tests')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket,'getaddrinfo',forbidden)


@pytest.fixture(scope='module')
def spec():return probe.plan(PROFILE,HIGH,LOW)[0]


def test_explicit_additive_opt_in_and_prompt_size(spec):
    cfg=Compact1PromptRequest.model_validate(spec['configuration'])
    assert cfg.semanticConceptPromptVersion=='v2-compact.1'
    assert GenerationRequest().semanticConceptPromptVersion=='v1'
    assert CompactPromptRequest().semanticConceptPromptVersion=='v2-compact'
    with pytest.raises(ValueError):GenerationRequest(semanticConceptPromptVersion='v2-compact.1')
    old=low.plan(PROFILE,HIGH)['spec']['prompt'];new=spec['prompt']
    assert old['sha256']==low.previous.PROMPT_HASH
    assert new['version']=='semantic-concept-prompt-v2-compact.1' and old['sha256']!=new['sha256']
    for part in ('system','prompt'):
        assert size_metrics(new[part])['characters']<=1.15*size_metrics(old[part])['characters']
    assert len(new['system']+'\n'+new['prompt'])<=1.15*len(old['system']+'\n'+old['prompt'])
    assert new['system'].count('FINAL SELF-CHECK (PRIVATE)')==1
    assert new['system'].count('\nOPENING\n')==1
    assert sum(line.startswith('CORE RULE INVARIANT:') for line in new['system'].splitlines())==1
    assert 'normal world→action→magic' in new['system']
    assert 'PAUSE FRAME TEST' in new['system']
    with pytest.raises(ValueError):compact1_prompt(CompactPromptRequest(),spec['cast'],1)


@pytest.mark.parametrize('row',POLICY['requirements'],ids=lambda r:r['id'])
def test_every_old_policy_retained(row,spec):
    old=low.plan(PROFILE,HIGH)['spec']['prompt']['system']
    assert row['oldEvidence'] in old and row['newEvidence'] in spec['prompt']['system'] and row['preserved']
    assert set(row['refinements'])<=set(POLICY['refinedPolicies'])


def test_exact_schema_and_accepted_profile_only_messages_differ(spec):
    assert spec['arguments']['response_format']==LOW['arguments']['response_format']==native_response_format(1)
    assert spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']==low.previous.SCHEMA_HASH
    assert spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['unresolvedReferences']==0
    assert spec['semanticEquivalence']['candidateLogicalSchemaIdentical']
    assert {r['path'] for r in spec['requestDiff']}=={'/messages/0/content','/messages/1/content'}
    assert spec['arguments']['reasoning_effort']=='low' and spec['arguments']['max_completion_tokens']==8192
    assert spec['timeout']==LOW['timeout'] and spec['streamingMode']=='NON_STREAMING'
    assert spec['maximumLiveRequests']==1 and spec['SDKMaxRetries']==0
    assert spec['providerCalls']==0 and 'temperature' not in spec['arguments']
    cfg=Compact1PromptRequest.model_validate(spec['configuration'])
    with pytest.raises(ValueError):construct_native_request(cfg,spec['cast'],1,{**PROFILE,'responseMode':'json_object'})
    bad=deepcopy(LOW);bad['arguments']['reasoning_effort']='high'
    with pytest.raises(ValueError):probe.plan(PROFILE,HIGH,bad)


@pytest.fixture(scope='module')
def replay(spec):
    cfg=Compact1PromptRequest.model_validate(spec['configuration']);oldcfg=CompactPromptRequest.model_validate({**spec['configuration'],'semanticConceptPromptVersion':'v2-compact'})
    oldprompt=compact_prompt(oldcfg,spec['cast'],1)
    results={}
    for case in MOCKS:
        raw=json.dumps({'ideas':[case['raw']]});a=analyze(raw,oldcfg,oldprompt);b=analyze(raw,cfg,spec['prompt'])
        x=a['allRawIdeas'][0]['record'];y=b['allRawIdeas'][0]['record']
        assert x and y
        for field in ('validation','admission','productionBlockers'):
            assert x[field]==y[field]
        results[case['case']]=b
    return results


@pytest.mark.parametrize('case',MOCKS,ids=lambda c:c['case']+'-'+c['purpose'])
def test_adversarial_policy_intent_with_unchanged_judges(case,replay,spec):
    r=replay[case['case']]['allRawIdeas'][0]['record'];o=r['observation'];id=case['case'];s=spec['prompt']['system']
    if id in 'ABC':
        assert case['editorialIntent']=='REJECT'
        assert o['openingScore']<60 and not o['frameZeroSupported']
        assert 'abnormal target state already physically blocking that goal' in s
    if id=='D':
        assert case['editorialIntent']=='ACCEPTABLE'
        assert o['openingScore']>=60 and o['frameZeroSupported']
    if id=='E':
        assert case['editorialIntent']=='REJECT' and case['raw']['impossibleRule']=='The hammer behaves backwards.'
        assert 'WHEN [specific visible action/contact]' in s and 'No "behaves backwards"' in s
    if id=='F':
        assert case['editorialIntent']=='ACCEPTABLE' and o['sameRuleEscalation']
    if id in 'GH':
        assert case['editorialIntent']=='REJECT' and o['ruleConsistency']['status']=='CONTRADICTION_DETECTED'
        if id=='G':assert any(f.get('beatNumber')==3 for f in o['ruleConsistency']['sourceFindings'])
        else:assert not o['payoffRuleLinked']
    if id in 'IJ':
        assert case['editorialIntent']=='ACCEPTABLE' and o['sameRuleEscalation'] and o['payoffRuleLinked']
    assert replay[id]['providerCallsDuringAnalysis']==0


def test_inspection_preserves_actual_version_and_judges(spec,replay):
    raw=json.dumps({'ideas':[MOCKS[3]['raw']]});r=inspect_response(raw,spec)
    assert r['nativeSchemaValid'] and r['normalization'] and r['pipelineRan']
    assert r['pipeline']['semanticConceptPromptVersion']=='v2-compact.1'
    assert r['pipeline']['promptVersion']=='semantic-concept-prompt-v2-compact.1'
    a=r['pipeline']['allRawIdeas'][0]['record'];b=replay['D']['allRawIdeas'][0]['record']
    assert a['validation']==b['validation'] and a['admission']==b['admission']


@pytest.mark.parametrize('mode',['success','timeout','double'])
def test_wire_profile_and_one_http_cap(spec,tmp_path,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');wire=[]
    def transport(request):
        wire.append(json.loads(request.content))
        if mode=='timeout':raise httpx.ReadTimeout('mock',request=request)
        return httpx.Response(200,headers={'x-request-id':'mock'},json=dict(id='mock',object='chat.completion',created=1,model='gpt-6.1-sol',choices=[dict(index=0,message=dict(role='assistant',content=json.dumps({'ideas':[MOCKS[3]['raw']]})),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30)))
    class MockProvider(CreativeCapabilityProvider):
        def __init__(self,*args):
            super().__init__(*args);self.client._client.close();self.client._client=httpx.Client(transport=httpx.MockTransport(transport))
        def complete(self,*args,**kwargs):
            raw=super().complete(*args,**kwargs)
            if mode=='double':super().complete(*args,**kwargs)
            return raw
    probe.worker(tmp_path,{**PROFILE,'reasoningEffort':'low'},spec,provider_factory=MockProvider)
    r=json.loads((tmp_path/'worker-result.json').read_text())
    assert wire==[spec['arguments']] and r['SDKRequestsForwarded']==r['HTTPRequestsObserved']==1
    receipt=json.loads((tmp_path/'sdk-request-forwarded.json').read_text())
    assert receipt['promptHash']==spec['prompt']['sha256'] and receipt['schemaHash']==low.previous.SCHEMA_HASH
    assert r['status']==('COMPLETED' if mode=='success' else 'FAILED')


@pytest.mark.parametrize('mode',['success','timeout','malformed'])
def test_execute_no_retry_no_second_request(spec,tmp_path,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');calls=[]
    def fake(path,profile,request):
        calls.append(request['arguments']);assert profile['reasoningEffort']=='low'
        (path/'response.txt').write_text(json.dumps({'ideas':[MOCKS[3]['raw']]}) if mode=='success' else '{bad' if mode=='malformed' else '')
        return dict(status='FAILED' if mode=='timeout' else 'COMPLETED',usage=None)
    path=tmp_path/'run';r=probe.execute(path,PROFILE,HIGH,LOW,authorization={'mock':True},tests=TESTS,runner=fake)
    assert len(calls)==r['logicalRequestCount']==r['maximumLiveRequests']==1
    assert r['retries']==r['fallbacks']==r['DeepSeekCalls']==r['renders']==0
    with pytest.raises(FileExistsError):probe.execute(path,PROFILE,HIGH,LOW,authorization={'mock':True},tests=TESTS,runner=fake)
    assert len(calls)==1


def test_preconditions_no_execution(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,HIGH,LOW,authorization={'mock':True},tests=TESTS)
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,HIGH,LOW,authorization={},tests=TESTS)
    assert not list(tmp_path.iterdir())


def test_all_prior_bytes_immutable():
    before=json.loads((DOCS/'semantic-prompt-v2-compact-1-v1/protected-before.json').read_text())
    integrity.assert_manifest_integrity(ROOT,{p:h for p,h in before.items() if p!='intelligence/ml-service/tests/protected_integrity.py'})
