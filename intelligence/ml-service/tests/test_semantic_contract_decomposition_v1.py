"""Mock-only D/E cross-cases. No creative judge,provider fallback or retry."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.workflow import semantic_contract_decomposition_v1 as d

ROOT=Path(__file__).parents[2]/'docs'
C_PATH=ROOT/'semantic-provider-transport-isolation-v1-run-001/probe-c/request.json'
C=json.loads(C_PATH.read_text())
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl='https://example.invalid',maxOutputTokens=128000,
    responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False)
IDEA=json.loads((Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json').read_text())['cases'][0]['mockV2']
SMALL={key:IDEA[key] for key in d.SMALL_FIELDS}


def run(tmp_path,monkeypatch,failures=()):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');calls=[]
    def runner(path,profile,spec):
        level=spec['level'];calls.append(level)
        if level=='D':assert (path.parent/'probe-e/request.json').exists()
        raw='' if level in failures else json.dumps(SMALL if level=='D' else {'ideas':[IDEA]})
        (path/'response.txt').write_text(raw)
        return dict(status='FAILED' if level in failures else 'COMPLETED',errorClass='ReadTimeout' if level in failures else None,usage=None)
    path=tmp_path/'experiment';result=d.execute(path,PROFILE,C,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    return path,result,calls,runner


def test_d_exact_full_prompt_and_flat_small_native_schema():
    specs,_=d.plan(C);spec=specs['D']
    assert spec['arguments']['messages']==C['arguments']['messages']
    assert spec['promptTextHash']==d.digest(C['arguments']['messages'])
    schema=spec['format']['json_schema']['schema'];assert set(schema['properties'])==set(d.SMALL_FIELDS)
    assert spec['metrics']['arraySchemas']==0 and spec['metrics']['declaredProperties']==6
    assert spec['arguments']['max_completion_tokens']==4096
    assert 'candidateSchema' in json.loads(spec['prompt'])


def test_e_minimal_prompt_full_schema_hash_identity():
    specs,_=d.plan(C);spec=specs['E']
    assert spec['format']==C['arguments']['response_format']
    assert spec['schemaHash']==d.digest(C['arguments']['response_format']['json_schema']['schema'])
    assert len(spec['system'])+len(spec['prompt'])<150
    assert 'RULE IMMUTABILITY' not in spec['system']
    assert spec['arguments']['max_completion_tokens']==C['arguments']['max_completion_tokens']==8192


@pytest.mark.parametrize('failures,classification',[
    (('D',),'UNRESOLVED_CONTRACT_FAILURE'),(('E',),'SCHEMA_COMPLEXITY_FAILURE'),
    (('D','E'),'PROMPT_AND_SCHEMA_COMPLEXITY_FAILURE'),((),'UNRESOLVED_CONTRACT_FAILURE')])
def test_both_planned_requests_and_result_matrix(tmp_path,monkeypatch,failures,classification):
    _,r,calls,_=run(tmp_path,monkeypatch,failures)
    assert calls==['D','E'] and r['primaryClassification']==classification and r['requestCount']==2
    assert r['SDKRetries']==r['DeepSeekCalls']==r['fallbacks']==r['creativePipelineCalls']==0
    assert not r['HUMAN_REVIEW_SET_CREATED']


def test_hard_cap_no_reexecution_and_sanitized_requests(tmp_path,monkeypatch):
    path,r,calls,runner=run(tmp_path,monkeypatch)
    with pytest.raises(FileExistsError):d.execute(path,PROFILE,C,authorization={'file':'test'},tests={'noNewFailures':True},runner=runner)
    assert calls==['D','E'] and 'mock-secret' not in ''.join(p.read_text() for p in path.rglob('*.json'))


def test_static_structural_metrics_and_unchanged_model_params():
    specs,structure=d.plan(C)
    for s in specs.values():
        assert s['arguments']['model']==C['arguments']['model']=='gpt-6.1-sol'
        assert s['arguments']['reasoning_effort']=='high' and 'temperature' not in s['arguments']
        assert 'tools' not in s['arguments'] and 'stream' not in s['arguments']
        assert s['timeout']==C['timeout']
        assert s['metrics']['requiredFieldOccurrences']>0 and s['metrics']['localTokenEstimate'] is None
    assert structure['prompt']['characters']==len(specs['D']['system'])
    assert structure['prompt']['explicitMustDoNotOccurrences']>0
    assert structure['schema']['arrays']==2 and structure['schema']['descriptionTextCharacters']>=0
    assert structure['schema']['enumCount']>0


def test_no_creative_pipeline_or_pydantic_content_judgment(tmp_path,monkeypatch):
    # Diagnostic E is native JSON Schema only; production cross-field validators are not run.
    idea=deepcopy(IDEA);idea['finalPayoff']='A different source payoff sentence.'
    schema=d.plan(C)[0]['E']['format']['json_schema']['schema']
    checked=d.check(json.dumps({'ideas':[idea]}),schema)
    assert checked['passed'] is None and checked['parseable']
    assert checked['reason']=='UNCHANGED_SCHEMA_REFERENCE_UNRESOLVABLE'
    assert not d.check('malformed',schema)['passed']
    assert d.classification(None,True)=='UNRESOLVED_CONTRACT_FAILURE'


@pytest.mark.parametrize('pair,result',[
    ((False,True),'PROMPT_COMPLEXITY_FAILURE'),((True,False),'SCHEMA_COMPLEXITY_FAILURE'),
    ((False,False),'PROMPT_AND_SCHEMA_COMPLEXITY_FAILURE'),((True,True),'PROMPT_SCHEMA_INTERACTION_FAILURE')])
def test_boolean_matrix_mapping_without_unknown_contract_evidence(pair,result):
    assert d.classification(*pair)==result


def test_worker_uses_existing_native_sdk_path_and_timeout(tmp_path,monkeypatch):
    from app.workflow import creative_provider_profiles
    calls=[]
    class Provider:
        def __init__(self,profile,tokens,timeout):
            assert tokens==4096 and timeout==90
            self.client=SimpleNamespace(max_retries=0)
        def complete(self,prompt,system='',temperature=.7):
            calls.append(1);assert set(self.response_format['json_schema']['schema']['properties'])==set(d.SMALL_FIELDS)
            self.last_usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}
            self.last_response_metadata={'finishReason':'stop','requestId':'mock'}
            return json.dumps(SMALL)
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',Provider)
    d.worker(tmp_path,PROFILE,d.plan(C)[0]['D'])
    r=json.loads((tmp_path/'worker-result.json').read_text());assert calls==[1] and r['status']=='COMPLETED'


def test_historical_prompt_schema_preserved(tmp_path,monkeypatch):
    before=hashlib.sha256(C_PATH.read_bytes()).hexdigest();run(tmp_path,monkeypatch,('D',))
    assert before==hashlib.sha256(C_PATH.read_bytes()).hexdigest()
    assert d.plan(C)[0]['E']['format']==C['arguments']['response_format']


def test_no_unauthorized_or_parameter_tuning(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock')
    with pytest.raises(ValueError):d.execute(tmp_path/'p',PROFILE,C)
    with pytest.raises(ValueError):d.execute(tmp_path/'p',dict(PROFILE,reasoningEffort='low'),C,authorization={'file':'test'},tests={'noNewFailures':True})
    assert not (tmp_path/'p').exists()
