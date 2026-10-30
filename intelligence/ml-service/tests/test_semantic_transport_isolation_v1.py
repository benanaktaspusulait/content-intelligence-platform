"""Mock-only ladder; A/B are never concepts for the creative judges."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.workflow import semantic_transport_isolation_v1 as iso

PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl='https://example.invalid',maxOutputTokens=128000,
    responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False)
IDEA=json.loads((Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json').read_text())['cases'][0]['mockV2']
PAYLOADS=dict(A='{"status":"ok"}',B='{"title":"Example","goal":"Sit down","object":"chair"}',C=json.dumps({'ideas':[IDEA]}))


def run(tmp_path,monkeypatch,failed=None,malformed=None):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');calls=[]
    def runner(path,profile,spec):
        level=spec['level'];calls.append(level)
        (path/'response.txt').write_text('invalid' if malformed==level else PAYLOADS[level] if failed!=level else '')
        return dict(status='FAILED' if failed==level else 'COMPLETED',errorClass='ReadTimeout' if failed==level else None,
            usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3})
    path=tmp_path/'ladder';result=iso.execute(path,PROFILE,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    return path,result,calls,runner


@pytest.mark.parametrize('level,label,expected',[
    ('A','FAILURE_BELOW_MODEL_RESPONSE',['A']),('B','STRUCTURED_OUTPUT_PATH_FAILURE',['A','B']),('C','FULL_V2_CONTRACT_FAILURE',['A','B','C'])])
def test_stop_at_first_failed_sdk_level(tmp_path,monkeypatch,level,label,expected):
    path,r,calls,_=run(tmp_path,monkeypatch,failed=level)
    assert calls==expected and r['primaryClassification']==label and r['requestCount']==len(expected)
    for skipped in set('ABC')-set(expected):
        assert not (path/('probe-'+skipped.lower())/'request-started.json').exists()
        assert (path/('probe-'+skipped.lower())/'not-executed.json').exists()


@pytest.mark.parametrize('level,label',[('A','FAILURE_BELOW_MODEL_RESPONSE'),('B','STRUCTURED_OUTPUT_PATH_FAILURE'),('C','FULL_V2_CONTRACT_FAILURE')])
def test_stop_on_response_parser_failure(tmp_path,monkeypatch,level,label):
    _,r,calls,_=run(tmp_path,monkeypatch,malformed=level)
    assert calls[-1]==level and r['primaryClassification']==label


def test_all_pass_hard_cap_three_no_reexecution_or_deepseek(tmp_path,monkeypatch):
    path,r,calls,runner=run(tmp_path,monkeypatch)
    assert calls==['A','B','C'] and r['primaryClassification']=='BATCH_SIZE_OR_OUTPUT_SCALE_FAILURE'
    assert r['requestCount']==3 and r['DeepSeekCalls']==r['fallbacks']==r['retries']==0
    with pytest.raises(FileExistsError):iso.execute(path,PROFILE,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    assert len(calls)==3


def test_metrics_and_model_parameters_differ_only_in_diagnostic_layers():
    specs=iso.plan(PROFILE)
    assert specs['A']['metrics']['schemaCharacters']==0
    assert specs['A']['metrics']['declaredProperties']==0 and specs['B']['metrics']['declaredProperties']==3
    assert specs['C']['metrics']['schemaCharacters']>specs['B']['metrics']['schemaCharacters']
    assert specs['C']['metrics']['arraySchemas']>=2
    for level,s in specs.items():
        assert s['metrics']['maxOutputTokens']==iso.OUTPUT_LIMITS[level]
        assert s['metrics']['totalRequestTextCharacters']==s['metrics']['systemCharacters']+s['metrics']['userCharacters']
        assert s['arguments']['reasoning_effort']=='high' and 'temperature' not in s['arguments']
        assert 'tools' not in s['arguments'] and 'stream' not in s['arguments']
        assert s['timeout']['readSeconds']==90 and s['timeout']['wallSeconds']==180
        assert s['metrics']['localTokenEstimate'] is None


def test_sanitized_snapshots_and_historical_preservation(tmp_path,monkeypatch):
    root=Path(__file__).parents[2]/'docs';previous=root/'semantic-provider-openai-gpt-6-1-sol-probe-5-run-001/benchmark-record.json'
    before=hashlib.sha256(previous.read_bytes()).hexdigest();path,_,_,_=run(tmp_path,monkeypatch,failed='A')
    assert 'mock-secret' not in ''.join(p.read_text() for p in path.rglob('*.json'))
    assert before==hashlib.sha256(previous.read_bytes()).hexdigest()
    for level in ['a','b','c']:assert (path/('probe-'+level)/'metrics-before-execution.json').exists()


def test_a_b_never_enter_creative_pipeline(tmp_path,monkeypatch):
    path,_,_,_=run(tmp_path,monkeypatch,failed='B')
    monkeypatch.setattr(iso,'analyze',lambda *a:pytest.fail('A/B must never reach creative judges'))
    assert iso.validate_c_offline(path)['status']=='NOT_RUN_C_NOT_PASSED'


def test_only_successful_c_one_candidate_enters_unchanged_pipeline(tmp_path,monkeypatch):
    path,_,_,_=run(tmp_path,monkeypatch)
    result=iso.validate_c_offline(path)
    assert result['status']=='COMPLETED_SECONDARY_DIAGNOSTIC' and result['metrics']['normalizedCount']==1


def test_classifier_unresolved_when_evidence_missing():
    assert iso.classification({})=='UNRESOLVED'
    assert iso.classification({'A':{'passed':True}})=='UNRESOLVED'


def test_stable_sdk_path_worker_and_safe_exception_chain(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    calls=[]
    class Provider:
        def __init__(self,profile,tokens,timeout):
            assert tokens==512 and timeout==90
            self.client=SimpleNamespace(max_retries=0)
        def complete(self,prompt,system='',temperature=.7):
            calls.append(1);assert self.response_format=={'type':'text'}
            self.last_usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
            self.last_response_metadata={'finishReason':'stop','requestId':'mock'}
            return PAYLOADS['A']
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Provider)
    iso.worker(tmp_path,PROFILE,iso.plan(PROFILE)['A'])
    r=json.loads((tmp_path/'worker-result.json').read_text())
    assert calls==[1] and r['status']=='COMPLETED' and r['firstUsableContentMs'] is not None


def test_no_unauthorized_or_other_provider(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock')
    with pytest.raises(ValueError):iso.execute(tmp_path/'p',PROFILE)
    with pytest.raises(ValueError):iso.execute(tmp_path/'p',dict(PROFILE,provider='deepseek'),authorization={'file':'test'},tests={'noNewFailures':True})
    assert not (tmp_path/'p').exists()


def test_exception_chain_safe_headers_and_no_secret_values(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    class Provider:
        def __init__(self,*args):self.client=SimpleNamespace(max_retries=0)
        def complete(self,*args,**kwargs):
            try:raise TimeoutError('mock-secret')
            except TimeoutError as cause:raise RuntimeError('mock-secret') from cause
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Provider)
    iso.worker(tmp_path,PROFILE,iso.plan(PROFILE)['A'])
    r=json.loads((tmp_path/'worker-result.json').read_text())
    assert [e['exceptionClass'] for e in r['exceptionChain']]==['RuntimeError','TimeoutError']
    assert 'mock-secret' not in json.dumps(r) and r['safeHeaders']=={}
