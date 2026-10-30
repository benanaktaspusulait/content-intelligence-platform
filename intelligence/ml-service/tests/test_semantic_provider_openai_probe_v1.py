"""Mock-only one-request OpenAI capability boundary and unchanged pipeline."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.workflow import semantic_provider_openai_probe_v1 as probe
from app.workflow.semantic_provider_execution_benchmark_v1 import request_for

PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl='https://example.invalid',maxOutputTokens=128000,
    responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False)
IDEA=json.loads((Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json').read_text())['cases'][0]['mockV2']


def run(tmp_path,monkeypatch,raw=None,status='COMPLETED'):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');calls=[]
    if raw is None:raw=json.dumps({'ideas':[dict(deepcopy(IDEA),ideaId=f'openai-{i}') for i in range(5)]})
    def runner(path,profile,config,prompt):
        calls.append(profile['provider']);(path/'response.txt').write_text(raw)
        return dict(status=status,usage={'prompt_tokens':100,'completion_tokens':200,'total_tokens':300},
            providerRequestId='mock-completion-id',finishReason='stop',firstUsableContentMs=10)
    path=tmp_path/'probe';record=probe.execute(path,PROFILE,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    return path,record,calls,runner


def test_openai_five_native_schema_request_uses_accepted_creative_content():
    cfg,p,args=request_for(PROFILE)
    assert args['model']=='gpt-6.1-sol' and args['response_format']['type']=='json_schema'
    schema=args['response_format']['json_schema'];assert schema['strict'] is False
    assert schema['schema']['properties']['ideas']['minItems']==schema['schema']['properties']['ideas']['maxItems']==5
    assert args['max_completion_tokens']==16384 and args['reasoning_effort']=='high'
    assert 'stream' not in args and 'temperature' not in args
    assert json.loads(p['prompt'])['requestedRawCount']==5


def test_one_request_cap_no_retry_no_deepseek_fallback(tmp_path,monkeypatch):
    path,r,calls,runner=run(tmp_path,monkeypatch)
    assert r['requestCount']==1 and r['automaticRetries']==r['DeepSeekCalls']==r['fallbackCalls']==0
    with pytest.raises(FileExistsError):probe.execute(path,PROFILE,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    assert calls==['openai']
    assert 'mock-secret' not in ''.join(p.read_text() for p in path.rglob('*.json'))


def test_success_response_schema_normalization_and_pipeline(tmp_path,monkeypatch):
    path,record,calls,_=run(tmp_path,monkeypatch)
    assert record['capability']['status']=='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_PASS'
    assert record['usage']['total_tokens']==300 and record['firstUsableContentMs']==10
    result=probe.analyze_stored(path)
    assert result['schemaValidCount']==5 and result['normalizedCount']==5 and not result['statisticalComparison']
    assert calls==['openai']


@pytest.mark.parametrize('raw,reason',[('', 'EMPTY_CONTENT'),('not json','MALFORMED_RESPONSE'),('{"ideas":[]}','EMPTY_IDEAS_ARRAY')])
def test_empty_or_malformed_response_no_repair(tmp_path,monkeypatch,raw,reason):
    path,r,calls,_=run(tmp_path,monkeypatch,raw)
    assert r['capability']['status']=='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_FAILED'
    assert r['capability']['reason']==reason and calls==['openai']
    assert probe.analyze_stored(path)['status']=='NOT_RUN_NO_USABLE_PARSED_CORPUS'


def test_capability_pass_does_not_require_schema_valid_or_creative_scores():
    r=probe.capability('{"ideas":[{"ideaId":"incomplete"}]}')
    assert r['status']=='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_PASS' and r['schemaValidCount']==0
    assert r['candidatesReachedSchema']==1 and r['schemaRejectedCount']==1


def test_usable_content_with_termination_warning_still_reaches_schema(tmp_path,monkeypatch):
    _,r,calls,_=run(tmp_path,monkeypatch,status='FAILED')
    assert r['capability']['status']=='OPENAI_GPT_6_1_SOL_CAPABILITY_PROBE_PASS' and calls==['openai']


def test_worker_uses_stable_complete_without_body_hooks_or_sse(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    calls=[]
    class Provider:
        def __init__(self,profile,tokens,timeout):
            assert profile['provider']=='openai' and tokens==16384 and timeout==90
            self.client=SimpleNamespace(max_retries=0)
        def complete(self,prompt,system='',temperature=.7):
            calls.append(1)
            assert self.response_format['json_schema']['schema']['properties']['ideas']['maxItems']==5
            self.last_usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
            self.last_response_metadata={'requestId':'mock-completion-id','finishReason':'stop','apiStatus':'COMPLETED'}
            return json.dumps({'ideas':[IDEA]})
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Provider)
    cfg,p,_=request_for(PROFILE);probe.worker(tmp_path,PROFILE,cfg.model_dump(),p)
    r=json.loads((tmp_path/'worker-result.json').read_text())
    assert calls==[1] and r['status']=='COMPLETED'
    assert r['responseHeadersMs'] is None and r['firstTokenMs'] is None and r['firstUsableContentMs'] is not None
    assert r['providerRequestId']=='mock-completion-id'


def test_failed_sdk_call_safe_trace_no_secret_no_retry(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    calls=[]
    class Failure:
        def __init__(self,*args):self.client=SimpleNamespace(max_retries=0)
        def complete(self,*args,**kw):calls.append(1);raise RuntimeError('mock-secret not to persist')
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Failure)
    cfg,p,_=request_for(PROFILE);probe.worker(tmp_path,PROFILE,cfg.model_dump(),p)
    r=json.loads((tmp_path/'worker-result.json').read_text())
    assert r['errorClass']=='RuntimeError' and r['safeTrace'] and len(calls)==1
    assert 'mock-secret' not in json.dumps(r)


def test_historical_benchmarks_unchanged(tmp_path,monkeypatch):
    root=Path(__file__).parents[2]/'docs'
    paths=[root/'semantic-provider-execution-benchmark-v1/probe-deepseek-5-run-001/benchmark-record.json',root/'semantic-live-v2-count-40-run-001/live-attempt/provider-metadata.json',root/'semantic-live-v2-count-40-run-001-recovery-001/transport-summary.json']
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};run(tmp_path,monkeypatch)
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_explicit_authorization_and_exact_model_only(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock')
    with pytest.raises(ValueError):probe.execute(tmp_path/'p',PROFILE)
    with pytest.raises(ValueError):probe.execute(tmp_path/'p',dict(PROFILE,provider='deepseek'),authorization={'file':'test'},tests={'noNewFailures':True})
    assert not (tmp_path/'p').exists()
