"""Every request here is mocked; real networking forbidden by offline harness."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.workflow import semantic_v2_sharded_recovery as r
from app.workflow.semantic_concept_prompt_v2 import prompt_v2
from app.workflow.short_concept_generation import resolve_cast

PROFILE=dict(provider='deepseek',model='deepseek-v4-pro',baseUrl='https://example.invalid',maxOutputTokens=64000,
    contextTokens=1000000,responseMode='json_object',tokenParameter='max_tokens',temperatureSupported=False,reasoningEffort='high')
IDEA=json.loads((Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json').read_text())['cases'][0]['mockV2']


def run(tmp_path,monkeypatch,statuses=('REQUEST_COMPLETED','REQUEST_COMPLETED'),items=None):
    monkeypatch.setenv('DEEPSEEK_API_KEY','mock-secret');calls=[]
    def runner(path,profile,config,prompt):
        ordinal=len(calls);calls.append(deepcopy(prompt))
        if statuses[ordinal]=='RAISE':raise RuntimeError('mock-secret')
        success=statuses[ordinal]=='REQUEST_COMPLETED'
        raw=json.dumps({'ideas':deepcopy(items if items is not None else [IDEA])}) if success else ''
        (path/'response.txt').write_text(raw)
        return dict(status=statuses[ordinal],usage={'prompt_tokens':10,'completion_tokens':20,'total_tokens':30} if success else None,
            providerCostUsd=None,providerRequestId='mock-request-'+str(ordinal),sdkMaxRetries=0)
    path=tmp_path/'run';result=r.execute_two(path,PROFILE,authorization={'file':'test'},test_evidence={'noNewFailures':True},runner=runner)
    return path,result,calls,runner


def test_exactly_two_independent_requests_and_no_reexecution(tmp_path,monkeypatch):
    path,results,calls,runner=run(tmp_path,monkeypatch)
    assert len(calls)==2 and len(results)==2
    a,b=[json.loads(p['prompt']) for p in calls]
    assert a.pop('shardMetadata')['shardId']=='A' and b.pop('shardMetadata')['shardId']=='B'
    assert a==b and calls[0]['system']==calls[1]['system']
    assert a['requestedRawCount']==20 and a['limits']['maxOutputTokens']==32768
    assert 'mock-A' not in calls[1]['prompt']
    with pytest.raises(FileExistsError):
        r.execute_two(path,PROFILE,authorization={'file':'test'},test_evidence={'noNewFailures':True},runner=runner)
    assert len(calls)==2
    assert 'mock-secret' not in ''.join(p.read_text() for p in path.rglob('*.json'))


@pytest.mark.parametrize('statuses',[
    ('REQUEST_FAILED','REQUEST_COMPLETED'),('REQUEST_COMPLETED','REQUEST_FAILED'),('RAISE','REQUEST_COMPLETED')])
def test_partial_success_always_runs_second_planned_shard(tmp_path,monkeypatch,statuses):
    path,results,calls,_=run(tmp_path,monkeypatch,statuses)
    assert len(calls)==2
    result=r.analyze_combined(path)
    assert result['rawCount']==1 and result['metrics']['normalizedCount']==1
    assert len(result['allRawIdeas'])==1
    assert sum(s['status']=='REQUEST_COMPLETED' for s in results)==1


def test_both_failed_no_fabricated_metrics_or_third_call(tmp_path,monkeypatch):
    path,results,calls,_=run(tmp_path,monkeypatch,('REQUEST_FAILED','REQUEST_FAILED'))
    result=r.analyze_combined(path)
    assert len(calls)==2 and result['status']=='NO_USABLE_SHARD_RESPONSE'
    assert result['creativeMetrics'] is None and result['HUMAN_REVIEW_SET'] is None


def test_ids_provenance_combined_normalization_and_cross_shard_duplicates(tmp_path,monkeypatch):
    path,_,_,_=run(tmp_path,monkeypatch,items=[IDEA,IDEA])
    corpus,provenance,_=r.combine(path)
    assert [i['ideaId'] for i in corpus['ideas']]==['v2-a-001','v2-a-002','v2-b-001','v2-b-002']
    assert all(p['providerOriginalIdeaId']=='mock-A' for p in provenance)
    result=r.analyze_combined(path)
    assert result['metrics']['normalizedCount']==4
    assert len(result['crossShardComparisons'])==4
    assert all(d['exactStructuralFingerprint'] for d in result['crossShardComparisons'])
    assert all(d['exactShapeHash'] for d in result['crossShardComparisons'])
    for row in result['allRawIdeas']:
        c=row['record']['candidate'];p=row['sourceProvenance']
        assert c['generationSource']=='SEMANTIC_V2' and c['provenance']['generationSource']=='SEMANTIC_V2'
        assert c['shardId']==p['shardId'] and c['providerRequestId']==p['providerRequestId']
        assert c['provenance']['providerPromptSha256']==p['providerPromptSha256']
        assert c['candidateOrdinalWithinShard']==p['candidateOrdinalWithinShard']
        assert c['providerPromptVersion']=='v2' and c['experimentId']==r.EXPERIMENT_ID


def test_usage_aggregation_missing_is_not_zero():
    rows=[dict(usage={'prompt_tokens':10,'completion_tokens':20,'total_tokens':30},providerCostUsd=.1),dict(usage={'prompt_tokens':3,'completion_tokens':4,'total_tokens':7},providerCostUsd=.2)]
    t=r.aggregate_usage(rows);assert (t['inputTokens'],t['outputTokens'],t['totalTokens'])==(13,24,37)
    assert t['providerCostUsd']==pytest.approx(.3)
    rows[1]['usage']=None;rows[1]['providerCostUsd']=None
    t=r.aggregate_usage(rows);assert t['totalTokens'] is None and t['providerCostUsd'] is None
    assert t['reportedSubsetTotals']['totalTokens']==30 and not t['completeUsageReported']


def test_accepted_creative_prompt_unchanged_and_only_batch_metadata_differs():
    cfg=r.configuration_for(PROFILE);cast,_=resolve_cast(cfg);base=prompt_v2(cfg,cast,40)
    cfg.semanticProvider.maxOutputTokens=r.OUTPUT_TOKENS;p=r.shard_prompt(cfg,cast,'A')
    assert p['system']==base['system'] and p['version']==base['version']
    a=json.loads(base['prompt']);b=json.loads(p['prompt'])
    a['requestedRawCount']=b['requestedRawCount'];a['limits']=b['limits'];a['batchInstructions']['count']=b['batchInstructions']['count'];b.pop('shardMetadata')
    assert a==b
    with pytest.raises(ValueError):r.shard_prompt(cfg,cast,'C')


def test_stored_response_replay_deterministic_and_no_transport(tmp_path,monkeypatch):
    path,_,calls,_=run(tmp_path,monkeypatch)
    first=r.analyze_combined(path)
    # Replay corpus/source provenance is deterministic; the exclusive analysis output cannot be overwritten.
    assert r.combine(path)==r.combine(path)
    with pytest.raises(FileExistsError):r.analyze_combined(path)
    assert len(calls)==2 and first['providerCallsDuringAnalysis']==0 and first['renders']==0


def test_request_schema_count_and_bounds_match_worker(tmp_path,monkeypatch):
    path,_,_,_=run(tmp_path,monkeypatch)
    for shard in ['a','b']:
        request=json.loads((path/('shard-'+shard)/'request.json').read_text())
        schema=json.loads(request['arguments']['messages'][0]['content'].split('use catalog IDs exactly:\n')[1])
        assert schema['properties']['ideas']['minItems']==schema['properties']['ideas']['maxItems']==20
        assert request['arguments']['max_tokens']==32768 and request['maxRetries']==0
        assert request['timeout']['wallSeconds']==300


def test_wall_deadline_terminates_worker_without_restart(tmp_path,monkeypatch):
    events=[]
    class Process:
        alive=True
        def start(self):events.append('start')
        def join(self,timeout):events.append(('join',timeout))
        def is_alive(self):return self.alive
        def terminate(self):events.append('terminate');self.alive=False
    process=Process()
    monkeypatch.setattr(r.multiprocessing,'get_context',lambda method:SimpleNamespace(Process=lambda **kw:process))
    result=r.bounded_request(tmp_path,{}, {}, {})
    assert result['errorType']=='ExperimentWallTimeout'
    assert events==['start',('join',300),'terminate',('join',5)]


def test_authorization_tests_and_model_required_before_any_request(tmp_path,monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','mock')
    with pytest.raises(ValueError):r.execute_two(tmp_path/'r',PROFILE)
    with pytest.raises(ValueError):r.execute_two(tmp_path/'r',{**PROFILE,'model':'different'},authorization={'file':'test'},test_evidence={'noNewFailures':True})
    assert not (tmp_path/'r').exists()


def test_duplicate_json_keys_not_silently_repaired(tmp_path,monkeypatch):
    path,_,_,_=run(tmp_path,monkeypatch)
    (path/'shard-a/response.txt').write_text('{"ideas": [], "ideas": []}')
    corpus,_,envelopes=r.combine(path)
    assert len(corpus['ideas'])==1 and envelopes[0]['status']=='NO_USABLE_JSON_ENVELOPE'


def test_worker_one_sdk_call_exact_schema_and_disabled_retries(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    calls=[]
    class Provider:
        def __init__(self,profile,tokens,timeout):
            assert tokens==32768 and timeout==120
            self.client=SimpleNamespace(max_retries=0)
        def complete(self,prompt,system='',temperature=.7):
            calls.append((prompt,system))
            assert self.response_format['json_schema']['schema']['properties']['ideas']['maxItems']==20
            self.last_usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
            self.last_response_metadata={'requestId':'mock-id'}
            return json.dumps({'ideas':[IDEA]})
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Provider)
    cfg=r.configuration_for(PROFILE);cast,_=resolve_cast(cfg);p=r.shard_prompt(cfg,cast,'A')
    r._worker(tmp_path,PROFILE,cfg.model_dump(),p)
    result=json.loads((tmp_path/'worker-result.json').read_text())
    assert len(calls)==1 and result['status']=='REQUEST_COMPLETED' and result['providerRequestId']=='mock-id'
    assert result['sdkMaxRetries']==0 and result['providerCostUsd'] is None


def test_schema_rejections_retained_and_partial_raw_not_lost(tmp_path,monkeypatch):
    bad=deepcopy(IDEA);bad['score']=100
    path,_,_,_=run(tmp_path,monkeypatch,items=[IDEA,bad])
    result=r.analyze_combined(path)
    assert result['rawCount']==4 and result['metrics']['normalizedCount']==2
    assert sum(row['schemaResult']=='INVALID' for row in result['allRawIdeas'])==2
    assert all(row['raw'].get('score')==100 for row in result['allRawIdeas'] if row['schemaResult']=='INVALID')
