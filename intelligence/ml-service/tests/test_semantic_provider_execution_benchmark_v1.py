"""Mock-only capability-probe tests. No provider factory/network in tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from app.workflow import semantic_provider_execution_benchmark_v1 as b
from app.workflow.semantic_concept_prompt_v2 import prompt_v2
from app.workflow.short_concept_generation import resolve_cast

PROFILE=dict(provider='deepseek',model='deepseek-v4-pro',baseUrl='https://example.invalid',maxOutputTokens=64000,
    contextTokens=1000000,responseMode='json_object',tokenParameter='max_tokens',temperatureSupported=False,reasoningEffort='high')
IDEA=json.loads((Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json').read_text())['cases'][0]['mockV2']


def run(tmp_path,monkeypatch,success=True,observed=None):
    monkeypatch.setenv('DEEPSEEK_API_KEY','mock-secret');calls=[]
    def runner(path,profile,config,prompt):
        calls.append(1)
        if success:
            ideas=[dict(deepcopy(IDEA),ideaId=f'probe-{i}') for i in range(5)]
            (path/'response.txt').write_text(json.dumps({'ideas':ideas}))
        if observed is not None:(path/'http-observation.json').write_text(json.dumps(observed))
        return dict(status='COMPLETED' if success else 'FAILED',errorClass=None if success else 'ExperimentWallTimeout',
            usage={'prompt_tokens':100,'completion_tokens':200,'total_tokens':300} if success else None,
            providerRequestId='mock-id' if success else None)
    path=tmp_path/'probe';r=b.execute(path,PROFILE,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    return path,r,calls,runner


def test_five_candidate_request_accepted_creative_schema_unchanged():
    cfg,p,args=b.request_for(PROFILE);cast,_=resolve_cast(cfg);accepted=prompt_v2(cfg,cast,40)
    assert p['system']==accepted['system'] and p['version']=='semantic-concept-prompt-v2'
    assert json.loads(p['prompt'])['requestedRawCount']==5
    assert json.loads(p['prompt'])['candidateSchema']==json.loads(accepted['prompt'])['candidateSchema']
    schema=json.loads(args['messages'][0]['content'].split('use catalog IDs exactly:\n')[1])
    assert schema['properties']['ideas']['minItems']==schema['properties']['ideas']['maxItems']==5
    assert args['max_tokens']==16384 and 'stream' not in args


def test_request_cap_one_and_no_fallback(tmp_path,monkeypatch):
    path,record,calls,runner=run(tmp_path,monkeypatch)
    assert record['requestCount']==1 and record['fallbackCalls']==record['automaticRetries']==0
    with pytest.raises(FileExistsError):b.execute(path,PROFILE,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    assert len(calls)==1
    assert 'mock-secret' not in ''.join(p.read_text() for p in path.rglob('*.json'))


def test_zero_byte_failure_and_timeout_metadata(tmp_path,monkeypatch):
    path,r,calls,_=run(tmp_path,monkeypatch,False)
    assert r['responseBytes']==0 and r['usage'] is None and r['firstByteMs'] is None
    assert r['timeout']==b.TIMEOUT and r['timeout']['wallSeconds']==180
    assert r['capabilityClassification']=='UNSUITABLE_FOR_CURRENT_SEMANTIC_V2_EXECUTION_ENVELOPE'
    assert b.analyze_probe(path)['status']=='NOT_RUN_NO_USABLE_RESPONSE' and len(calls)==1


def test_successful_five_response_complete_offline_pipeline(tmp_path,monkeypatch):
    path,record,calls,_=run(tmp_path,monkeypatch)
    r=b.analyze_probe(path)
    assert record['usage']['total_tokens']==300 and record['providerRequestId']=='mock-id'
    assert r['schemaValidCount']==5 and r['normalizedCount']==5
    assert not r['comparisonTo40ConceptExperiments'] and len(calls)==1


def test_first_byte_observed_body_is_unchanged(tmp_path):
    ticks=iter([0.,.1,.2,.3]);observer=b.BodyObserver(tmp_path/'observation.json',clock=lambda:next(ticks))
    class Stream(httpx.SyncByteStream):
        def __iter__(self):yield b' \n';yield b'{"ok":true}'
        def close(self):pass
    response=httpx.Response(200,stream=Stream());observer.on_response(response)
    assert response.read()==b' \n{"ok":true}'
    assert observer.data['firstByteMs']==200 and observer.data['firstNonWhitespaceByteMs']==300
    assert observer.data['responseHeadersMs']==100 and observer.data['httpBodyBytesObserved']==13


def test_first_byte_record_differs_from_application_response_size(tmp_path,monkeypatch):
    _,r,_,_=run(tmp_path,monkeypatch,False,{'firstByteMs':10,'responseHeadersMs':9,'httpBodyBytesObserved':2})
    assert r['responseBytes']==0 and r['firstByteMs']==10 and r['httpBodyBytesObserved']==2


def test_discovery_no_calls_configured_alternative_and_credentials_boolean(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret')
    profiles=dict(profiles={'deepseek-primary':PROFILE,'openai-escalation':dict(PROFILE,provider='openai',model='gpt-6.1-sol',responseMode='json_schema')})
    r=b.discovery(profiles);assert r['alternativeCalls']==0 and not r['modelAvailabilityVerified']
    a=next(p for p in r['configuredSemanticProfiles'] if p['alternative'])
    assert a['model']=='gpt-6.1-sol' and a['credentialsPresent'] is True and a['structuredOutput']=='json_schema'
    assert a['streaming']=='STREAMING_NOT_SUPPORTED' and 'mock-secret' not in json.dumps(r)


def test_previous_attempts_untouched(tmp_path,monkeypatch):
    root=Path(__file__).parents[2]/'docs'
    paths=[root/'semantic-live-v2-count-40-run-001/live-attempt/provider-metadata.json',root/'semantic-live-v2-count-40-run-001-recovery-001/shard-a/provider-metadata.json',root/'semantic-live-v2-count-40-run-001-recovery-001/shard-b/provider-metadata.json']
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    run(tmp_path,monkeypatch,False)
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_bounded_worker_killed_no_restart(tmp_path,monkeypatch):
    events=[]
    class Process:
        alive=True
        def start(self):events.append('start')
        def join(self,timeout):events.append(timeout)
        def is_alive(self):return self.alive
        def terminate(self):events.append('terminate');self.alive=False
    p=Process();monkeypatch.setattr(b.multiprocessing,'get_context',lambda method:SimpleNamespace(Process=lambda **kw:p))
    result=b.bounded(tmp_path,{}, {}, {})
    assert result['errorClass']=='ExperimentWallTimeout' and events==['start',180,'terminate',5]


def test_no_unauthorized_or_different_model_probe(tmp_path,monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','mock')
    with pytest.raises(ValueError):b.execute(tmp_path/'p',PROFILE)
    with pytest.raises(ValueError):b.execute(tmp_path/'p',dict(PROFILE,model='other'),authorization={'file':'test'},tests={'noNewFailures':True})
    assert not (tmp_path/'p').exists()


def test_probe_worker_installs_http_hooks_without_enabling_sse(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    calls=[]
    class Provider:
        def __init__(self,profile,tokens,timeout):
            assert tokens==16384 and timeout==90
            self.client=SimpleNamespace(max_retries=0,_client=SimpleNamespace(event_hooks={'request':[],'response':[]}))
        def complete(self,prompt,system='',temperature=.7):
            calls.append(1)
            assert self.response_format['json_schema']['schema']['properties']['ideas']['maxItems']==5
            for hook in self.client._client.event_hooks['request']:hook(None)
            response=httpx.Response(200,stream=httpx.ByteStream(b' {"ok":true}'))
            for hook in self.client._client.event_hooks['response']:hook(response)
            assert response.read()==b' {"ok":true}'
            self.last_usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
            self.last_response_metadata={'requestId':'mock-id'}
            return json.dumps({'ideas':[IDEA]})
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Provider)
    cfg,p,_=b.request_for(PROFILE);b.worker(tmp_path,PROFILE,cfg.model_dump(),p)
    observed=json.loads((tmp_path/'http-observation.json').read_text());result=json.loads((tmp_path/'worker-result.json').read_text())
    assert observed['firstByteMs'] is not None and observed['httpBodyBytesObserved']==12
    assert len(calls)==1 and result['status']=='COMPLETED' and result['providerRequestId']=='mock-id'
