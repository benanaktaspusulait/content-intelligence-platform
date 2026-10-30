"""Zero-network frame-first prompt intent, schema identity and single-call guards."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import httpx
import pytest
import protected_integrity as integrity
from app.workflow import semantic_compact_2_probe_v1 as probe
from app.workflow import semantic_low_reasoning_probe_v1 as low
from app.workflow.semantic_concept_prompt_v2_compact_1 import Compact1PromptRequest
from app.workflow.semantic_concept_prompt_v2_compact_2 import Compact2PromptRequest,construct_native_request,inspect_response
from app.workflow.semantic_concept_generation import GenerationRequest
from app.workflow.semantic_native_schema_integrity_v1 import native_response_format
from app.workflow.semantic_prompt_v2_experiment import analyze
from app.workflow.creative_provider_profiles import CreativeCapabilityProvider

ROOT=Path(__file__).resolve().parents[3];DOCS=ROOT/'intelligence/docs';FIX=Path(__file__).parent/'fixtures'
HIGH=json.loads((DOCS/'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
LOW=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
C1=json.loads((DOCS/'semantic-compact-1-low-probe-1-run-001/request-before-sdk.json').read_text())
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl=LOW['baseUrl'],responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False,maxOutputTokens=128000)
POLICY=json.loads((FIX/'semantic_prompt_v2_compact_2_policy.json').read_text())
MOCKS=json.loads((FIX/'semantic_prompt_v2_compact_2_mocks.json').read_text())['cases']
TESTS=dict(noNewFailures=True,schemaIntegrityPassed=True)


@pytest.fixture(autouse=True)
def no_external_calls(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('External calls forbidden during tests')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(socket,'getaddrinfo',forbidden)


@pytest.fixture(scope='module')
def spec():return probe.plan(PROFILE,HIGH,LOW,C1)[0]


def test_additive_version_size_and_exact_mechanical_rule_retention(spec):
    old=probe.prior.plan(PROFILE,HIGH,LOW)[0]['prompt'];new=spec['prompt']
    assert old['sha256']=='122a65a43c084c77a0bff466a89461da4f7d7cc701aa3ae8fd5709829ec3d417'
    assert new['semanticConceptPromptVersion']=='v2-compact.2'
    assert GenerationRequest().semanticConceptPromptVersion=='v1'
    assert Compact1PromptRequest().semanticConceptPromptVersion=='v2-compact.1'
    with pytest.raises(ValueError):GenerationRequest(semanticConceptPromptVersion='v2-compact.2')
    with pytest.raises(ValueError):construct_native_request(Compact1PromptRequest(),spec['cast'],1,PROFILE)
    for part in ('system','prompt'):assert len(new[part])<=1.10*len(old[part])
    assert len(new['system']+'\n'+new['prompt'])<=1.10*len(old['system']+'\n'+old['prompt'])
    rule=lambda p:next(line for line in p['system'].splitlines() if line.startswith('CORE RULE INVARIANT:'))
    assert rule(old)==rule(new)
    assert new['system'].count('\nOPENING\n')==1 and new['system'].count('FINAL SELF-CHECK (PRIVATE)')==1
    for section in ('DIVERSITY','PRODUCTION','OUTPUT CONTRACT'):
        block=lambda p:p['system'].split(section+'\n')[1].split('\n\n')[0]
        assert block(old)==block(new)
    assert new['system'].index('BEFORE rule→goal→beats→payoff')<new['system'].index('\nBEATS\n')


@pytest.mark.parametrize('row',POLICY['requirements'],ids=lambda r:r['id'])
def test_policy_equivalence(row,spec):
    old=probe.prior.plan(PROFILE,HIGH,LOW)[0]['prompt']['system']
    assert row['oldEvidence'] in old and row['newEvidence'] in spec['prompt']['system'] and row['preserved']


@pytest.mark.parametrize('row',POLICY['refinements'],ids=lambda r:r['id'])
def test_only_five_deliberate_policy_refinements(row,spec):
    assert row['evidence'] in spec['prompt']['system']
    assert row['id'] in {'FRAME_ZERO_FIRST_IDEATION','ACTIVE_OPENING_CONFLICT','STILL_FRAME_CAUSAL_LEGIBILITY','OPENING_BEAT_CONTINUITY','PAYOFF_DIRECTIONALITY'}


def test_exact_schema_profile_and_cast_history(spec):
    assert spec['arguments']['response_format']==C1['arguments']['response_format']==native_response_format(1)
    assert spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']==low.previous.SCHEMA_HASH
    assert spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['unresolvedReferences']==0
    assert spec['semanticEquivalence']['candidateLogicalSchemaIdentical']
    assert {d['path'] for d in spec['requestDiff']}=={'/messages/0/content','/messages/1/content'}
    assert spec['arguments']['reasoning_effort']=='low' and spec['arguments']['max_completion_tokens']==8192
    assert spec['timeout']==C1['timeout'] and spec['streamingMode']=='NON_STREAMING'
    assert spec['maximumLiveRequests']==1 and spec['SDKMaxRetries']==0 and spec['providerCalls']==0
    old=json.loads(C1['arguments']['messages'][1]['content']);new=json.loads(spec['arguments']['messages'][1]['content'])
    for p in (old,new):p.pop('promptVersion');p.pop('semanticConceptPromptVersion')
    assert old==new and new['requestedRawCount']==1
    assert probe.worker is probe.prior.worker and probe.bounded is probe.prior.bounded
    bad=deepcopy(C1);bad['arguments']['reasoning_effort']='high'
    with pytest.raises(ValueError):probe.plan(PROFILE,HIGH,LOW,bad)
    cfg=Compact2PromptRequest.model_validate(spec['configuration'])
    with pytest.raises(ValueError):construct_native_request(cfg,spec['cast'],1,{**PROFILE,'responseMode':'json_object'})


@pytest.fixture(scope='module')
def replay(spec):
    oldspec=probe.prior.plan(PROFILE,HIGH,LOW)[0]
    oldcfg=Compact1PromptRequest.model_validate(oldspec['configuration']);newcfg=Compact2PromptRequest.model_validate(spec['configuration']);out={}
    for case in MOCKS:
        raw=json.dumps({'ideas':[case['raw']]});old=analyze(raw,oldcfg,oldspec['prompt']);new=analyze(raw,newcfg,spec['prompt'])
        a=old['allRawIdeas'][0]['record'];b=new['allRawIdeas'][0]['record'];assert a and b
        for key in ('validation','admission','productionBlockers'):assert a[key]==b[key]
        assert new['providerCallsDuringAnalysis']==0
        out[case['case']]=new
    return out


@pytest.mark.parametrize('case',MOCKS,ids=lambda c:c['case']+'-'+c['purpose'])
def test_opening_and_directional_payoff_intent(case,spec,replay):
    id=case['case'];s=spec['prompt']['system'];raw=case['raw'];r=replay[id]['allRawIdeas'][0]['record']
    # Intent annotations are hand-authored counterexamples, not a new runtime judge.
    # Replays independently establish that the SAME accepted judges still score them.
    assert case['editorialIntent']==('REJECT' if id in 'ABCDEFKL' else 'ACCEPTABLE')
    if id in 'ABC':assert r['observation']['openingScore']<60 and not r['observation']['frameZeroSupported']
    if id=='A':assert 'normal hammer' in raw['frameZeroDescription'] and 'No normal preparation' in s
    if id=='B':assert 'shocked' in raw['frameZeroDescription'] and 'reaction-led/off-screen cause' in s
    if id=='C':assert 'whose arms hang at his sides' in raw['frameZeroDescription'] and 'could frame zero alone show the task' in s
    if id=='D':assert 'off-screen' in raw['frameZeroDescription'] and 'never remote' in s
    if id=='E':assert 'unrelated floating' in raw['frameZeroDescription'] and 'unrelated floating object' in s
    if id=='F':assert 'a moment later' in raw['frameZeroDescription'] and 'never temporal narration' in s
    if id in 'GHI':assert r['observation']['frameZeroSupported'] and r['observation']['openingScore']>=60
    if id=='I':assert r['observation']['sameRuleEscalation'] and 'This state instantiates the exact rule' in s
    if id=='J':assert 'same visibly bent nail' in raw['beats'][0]['strategy'] and 'no hidden reset' in s and r['observation']['sameRuleEscalation']
    if id=='K':assert 'switches the property' in raw['finalPayoff'] and 'no ambiguous source/destination' in s
    if id=='L':assert 'reverse orientation' in raw['finalPayoff'] and 'orientation or reverse outcome' in s
    if id=='M':assert r['observation']['payoffRuleLinked'] and r['observation']['sameRuleEscalation'] and 'BEFORE STATE→SAME RULE ACTIVATES→AFTER STATE' in s


def test_pipeline_real_version_and_inspection_unchanged(spec,replay):
    result=inspect_response(json.dumps({'ideas':[MOCKS[6]['raw']]}),spec)
    assert result['nativeSchemaValid'] and result['normalization'] and result['pipelineRan']
    assert result['pipeline']['semanticConceptPromptVersion']=='v2-compact.2'
    assert result['pipeline']['promptVersion']=='semantic-concept-prompt-v2-compact.2'
    r=result['pipeline']['allRawIdeas'][0]['record'];expected=replay['G']['allRawIdeas'][0]['record']
    assert r['validation']==expected['validation'] and r['admission']==expected['admission']


@pytest.mark.parametrize('mode',['success','timeout','double'])
def test_exact_sdk_http_body_and_hard_one_call_cap(spec,tmp_path,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');wire=[]
    def transport(request):
        wire.append(json.loads(request.content))
        if mode=='timeout':raise httpx.ReadTimeout('mock',request=request)
        return httpx.Response(200,headers={'x-request-id':'mock'},json=dict(id='mock',object='chat.completion',created=1,model='gpt-6.1-sol',choices=[dict(index=0,message=dict(role='assistant',content=json.dumps({'ideas':[MOCKS[6]['raw']]})),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30)))
    class MockProvider(CreativeCapabilityProvider):
        def __init__(self,*args):
            super().__init__(*args);self.client._client.close();self.client._client=httpx.Client(transport=httpx.MockTransport(transport))
        def complete(self,*args,**kwargs):
            raw=super().complete(*args,**kwargs)
            if mode=='double':super().complete(*args,**kwargs)
            return raw
    probe.worker(tmp_path,{**PROFILE,'reasoningEffort':'low'},spec,provider_factory=MockProvider)
    result=json.loads((tmp_path/'worker-result.json').read_text())
    assert wire==[spec['arguments']] and result['SDKRequestsForwarded']==result['HTTPRequestsObserved']==1
    assert result['status']==('COMPLETED' if mode=='success' else 'FAILED')
    assert json.loads((tmp_path/'sdk-request-forwarded.json').read_text())['promptHash']==spec['prompt']['sha256']


@pytest.mark.parametrize('mode',['success','timeout','malformed'])
def test_execute_no_retry_no_second_call(spec,tmp_path,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');calls=[]
    def fake(path,profile,request):
        calls.append(request['arguments']);assert profile['reasoningEffort']=='low'
        (path/'response.txt').write_text(json.dumps({'ideas':[MOCKS[6]['raw']]}) if mode=='success' else '{bad' if mode=='malformed' else '')
        return dict(status='FAILED' if mode=='timeout' else 'COMPLETED',usage=None)
    path=tmp_path/'run';result=probe.execute(path,PROFILE,HIGH,LOW,C1,authorization={'mock':True},tests=TESTS,runner=fake)
    assert len(calls)==result['logicalRequestCount']==result['maximumLiveRequests']==1
    assert result['retries']==result['fallbacks']==result['DeepSeekCalls']==result['renders']==0
    with pytest.raises(FileExistsError):probe.execute(path,PROFILE,HIGH,LOW,C1,authorization={'mock':True},tests=TESTS,runner=fake)
    assert len(calls)==1


def test_missing_auth_or_credentials_makes_no_call(tmp_path,monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,HIGH,LOW,C1,authorization={'mock':True},tests=TESTS)
    with pytest.raises(ValueError):probe.execute(tmp_path/'run',PROFILE,HIGH,LOW,C1,authorization={},tests=TESTS)
    assert not list(tmp_path.iterdir())


def test_all_existing_prompt_judge_taxonomy_and_historical_bytes_unchanged():
    before=json.loads((DOCS/'semantic-prompt-v2-compact-2-v1/protected-before.json').read_text())
    integrity.assert_manifest_integrity(ROOT,{p:h for p,h in before.items() if p!='intelligence/ml-service/tests/protected_integrity.py'})
