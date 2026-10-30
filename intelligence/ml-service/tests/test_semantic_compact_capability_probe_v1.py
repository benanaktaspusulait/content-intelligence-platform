"""Only mocked transports; live task authorization is never exercised here."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import httpx
import pytest
import protected_integrity as integrity
from app.workflow import semantic_compact_capability_probe_v1 as probe
from app.workflow.concept_fingerprint import digest
from app.workflow.creative_provider_profiles import CreativeCapabilityProvider
from app.workflow.semantic_native_schema_integrity_v1 import native_response_format

ROOT=Path(__file__).resolve().parents[3]
FIX=Path(__file__).parent/'fixtures'
DATA=json.loads((FIX/'semantic_schema_integrity_full_candidate_v1.json').read_text())
MOCKS=json.loads((FIX/'semantic_prompt_v2_compact_mocks_v1.json').read_text())['cases']
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl='https://example.invalid',responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False,maxOutputTokens=128000)
TESTS=dict(noNewFailures=True,schemaIntegrityPassed=True)

@pytest.fixture(scope='module')
def spec():return probe.plan(PROFILE)


def test_compact_prompt_schema_identity_and_single_candidate(spec):
    accepted=json.loads((ROOT/'intelligence/docs/semantic-prompt-v2-compact-v1/compact-prompt.json').read_text())
    assert spec['prompt']==accepted
    assert spec['arguments']['response_format']==native_response_format(1)
    assert spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['unresolvedReferences']==0
    assert spec['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']==probe.SCHEMA_HASH
    assert spec['semanticEquivalence']['candidateLogicalSchemaIdentical']
    assert spec['arguments']['response_format']['json_schema']['schema']['properties']['ideas']['minItems']==1
    assert json.loads(spec['prompt']['prompt'])['requestedRawCount']==spec['configuration']['semanticRawCount']==1
    assert spec['timeout']==dict(connectSeconds=15,readSeconds=90,writeSeconds=60,poolSeconds=15,wallSeconds=180)
    assert spec['maxOutputTokens']==8192 and spec['SDKMaxRetries']==0
    assert spec['arguments']['reasoning_effort']=='high' and 'temperature' not in spec['arguments']
    assert 'stream' not in spec['arguments'] and spec['streamingMode']=='NON_STREAMING'


@pytest.mark.parametrize('change',[dict(provider='deepseek'),dict(model='another-model'),dict(responseMode='json_object'),dict(reasoningEffort='low'),dict(temperatureSupported=True),dict(tokenParameter='max_tokens')])
def test_no_provider_model_mode_or_parameter_fallback(change):
    with pytest.raises(ValueError):probe.plan({**PROFILE,**change})


def runner(raw,status='COMPLETED',error=None,calls=None):
    def run(path,profile,spec):
        if calls is not None:calls.append(1)
        (path/'response.txt').write_text(raw)
        return dict(status=status,errorClass=error,exceptionChain=[dict(exceptionClass=error)] if error else [],usage=None,SDKRequestsForwarded=1,HTTPRequestsObserved=1)
    return run


def test_success_normalizes_and_runs_full_pipeline_without_creative_pass_requirement(spec):
    r=probe.inspect_response(json.dumps({'ideas':[DATA]}),spec)
    assert r['executionClassification']=='COMPACT_FULL_CONTRACT_EXECUTION_PASS'
    assert r['nativeSchemaValid'] and r['normalization'] and r['pipelineRan']
    assert r['prePipelineContract']['beatCount']==4 and r['prePipelineContract']['duration']['rangePassed']
    record=r['pipeline']['allRawIdeas'][0]['record']
    for key in ('validation','admission','observation','productionBlockers'):assert key in record
    assert r['creativeContractClassification'] in ('CREATIVE_CONTRACT_PASS','CREATIVE_CONTRACT_FAILURE')
    assert not r['creativeEvidence']['providerRationaleUsedAsAuthority']


@pytest.mark.parametrize('raw',['','{not json','{"ideas":[],"ideas":[]}','{"ideas":NaN}'])
def test_parse_failure_no_pipeline(raw,spec):
    def forbidden(*args):raise AssertionError('Pipeline must not run')
    r=probe.inspect_response(raw,spec,analysis=forbidden)
    assert r['executionClassification']=='COMPACT_FULL_CONTRACT_PARSE_FAILURE' and not r['pipelineRan']


@pytest.mark.parametrize('mutation',[lambda r:r.update(beats=r['beats'][:3]),lambda r:r.update(beats=r['beats']*2),lambda r:r.update(durationSeconds=24),lambda r:r.pop('everydayGoal'),lambda r:r.update(score=100)])
def test_schema_and_creative_contract_failure_no_repair(mutation,spec):
    raw=deepcopy(DATA);mutation(raw);before=deepcopy(raw)
    def forbidden(*args):raise AssertionError('Invalid native schema must stop before pipeline')
    r=probe.inspect_response(json.dumps({'ideas':[raw]}),spec,analysis=forbidden)
    assert r['executionClassification']=='COMPACT_FULL_CONTRACT_SCHEMA_FAILURE'
    assert r['creativeContractClassification']=='CREATIVE_CONTRACT_FAILURE' and not r['pipelineRan']
    assert before==raw
    if raw.get('durationSeconds')==24:assert not r['prePipelineContract']['duration']['rangePassed']


def test_cross_field_domain_failure_not_native_schema_defect(spec):
    raw=deepcopy(DATA);raw['finalPayoff']='An unrelated unplanned final event appears.'
    r=probe.inspect_response(json.dumps({'ideas':[raw]}),spec)
    assert r['nativeSchemaValid'] and r['domainRejections'] and not r['normalization']
    assert r['executionClassification']=='COMPACT_FULL_CONTRACT_SCHEMA_FAILURE'


def test_noncanonical_actor_cannot_count_as_execution_pass(spec):
    raw=deepcopy(DATA);raw['protagonistSuggestion']='Unknown intruder'
    r=probe.inspect_response(json.dumps({'ideas':[raw]}),spec)
    assert r['nativeSchemaValid'] and not r['normalization'] and r['executionClassification']=='UNRESOLVED'


def test_rule_inconsistency_preserves_execution_pass_and_fails_creative_contract(spec):
    r=probe.inspect_response(json.dumps({'ideas':[MOCKS[0]['raw']]}),spec)
    assert r['executionClassification']=='COMPACT_FULL_CONTRACT_EXECUTION_PASS'
    assert r['creativeContractClassification']=='CREATIVE_CONTRACT_FAILURE'
    assert r['creativeEvidence']['ruleConsistency']=='RULE_INCONSISTENT'
    assert r['creativeEvidence']['offendingFindings']
    assert any(b['ruleConsistency']=='RULE_INCONSISTENT' for b in r['creativeEvidence']['perBeat'])


def test_trigger_and_opening_weakness_not_repaired(spec):
    for index in (1,4,5,6):
        raw=deepcopy(MOCKS[index]['raw']);r=probe.inspect_response(json.dumps({'ideas':[raw]}),spec)
        assert r['executionClassification']=='COMPACT_FULL_CONTRACT_EXECUTION_PASS'
        assert r['creativeContractClassification']=='CREATIVE_CONTRACT_FAILURE'
        assert r['pipeline']['allRawIdeas'][0]['raw']==raw


@pytest.mark.parametrize('status,error,raw,classification',[
 ('FAILED','ReadTimeout','','COMPACT_FULL_CONTRACT_TIMEOUT'),
 ('FAILED','ExperimentWallTimeout','','COMPACT_FULL_CONTRACT_TIMEOUT'),
 ('FAILED','AuthenticationError','','COMPACT_FULL_CONTRACT_PROVIDER_FAILURE'),
 ('COMPLETED',None,'{oops','COMPACT_FULL_CONTRACT_PARSE_FAILURE'),
 ('COMPLETED',None,json.dumps({'ideas':[]}),'COMPACT_FULL_CONTRACT_SCHEMA_FAILURE')])
def test_failure_single_consumed_experiment_no_retry_or_fallback(tmp_path,monkeypatch,status,error,raw,classification):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');calls=[];path=tmp_path/'run'
    result=probe.execute(path,PROFILE,authorization={'file':'mock-only'},tests=TESTS,runner=runner(raw,status,error,calls))
    assert result['executionClassification']==classification
    assert len(calls)==result['logicalRequestCount']==result['maximumLiveRequests']==1
    assert result['retries']==result['DeepSeekCalls']==result['fallbacks']==result['renders']==0
    with pytest.raises(FileExistsError):probe.execute(path,PROFILE,authorization={'file':'mock-only'},tests=TESTS,runner=runner(raw,calls=calls))
    assert len(calls)==1


def test_preflight_receipt_is_written_before_full_pipeline(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');path=tmp_path/'run';original=probe.inspect_response
    def inspect(raw,spec):
        assert (path/'pre-pipeline-creative-contract.json').exists()
        return original(raw,spec)
    monkeypatch.setattr(probe,'inspect_response',inspect)
    r=probe.execute(path,PROFILE,authorization={'file':'mock'},tests=TESTS,runner=runner(json.dumps({'ideas':[DATA]})))
    assert r['executionClassification']=='COMPACT_FULL_CONTRACT_EXECUTION_PASS' and r['pipelineRan']
    assert (path/'pipeline.json').exists() and (path/'complete-candidate-and-pipeline.txt').exists()


def test_authorization_and_completed_tests_required(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret')
    with pytest.raises(ValueError):probe.execute(tmp_path/'none',PROFILE,tests=TESTS)
    with pytest.raises(ValueError):probe.execute(tmp_path/'bad',PROFILE,authorization={'file':'mock'},tests={'noNewFailures':False})
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('mode',['success','timeout','double','wrong-prompt'])
def test_actual_sdk_mock_wire_exact_body_cap_and_timeout_metrics(mode,spec,tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');wire=[]
    def transport(request):
        wire.append(json.loads(request.content))
        if mode=='timeout':raise httpx.ReadTimeout('mock timeout',request=request)
        return httpx.Response(200,headers={'x-request-id':'mock-http-id'},json=dict(id='mock-completion',object='chat.completion',created=1,model='gpt-6.1-sol',choices=[dict(index=0,message=dict(role='assistant',content=json.dumps({'ideas':[DATA]})),finish_reason='stop')],usage=dict(prompt_tokens=111,completion_tokens=222,total_tokens=333)))
    class MockProvider(CreativeCapabilityProvider):
        def __init__(self,*args):
            super().__init__(*args);self.client._client.close();self.client._client=httpx.Client(transport=httpx.MockTransport(transport))
        def complete(self,prompt,system='',**kwargs):
            if mode=='wrong-prompt':system+=' changed'
            raw=super().complete(prompt,system=system,**kwargs)
            if mode=='double':super().complete(prompt,system=system,**kwargs)
            return raw
    probe.worker(tmp_path,PROFILE,spec,provider_factory=MockProvider)
    r=json.loads((tmp_path/'worker-result.json').read_text())
    if mode=='wrong-prompt':assert not wire and r['SDKRequestsForwarded']==0
    else:
        assert len(wire)==r['SDKRequestsForwarded']==r['HTTPRequestsObserved']==1
        assert wire[0]==spec['arguments']
        actual=json.loads((tmp_path/'last-mile-sdk-request.json').read_text());assert actual==wire[0]
    if mode=='success':
        assert r['status']=='COMPLETED' and r['httpStatus']==200 and r['timeToHeadersMs'] is not None
        assert r['httpRequestId']=='mock-http-id' and r['usage']['total_tokens']==333
        assert r['providerReportedCostUsd'] is None
    else:assert r['status']=='FAILED'
    if mode=='timeout':assert any(e['exceptionClass']=='ReadTimeout' for e in r['exceptionChain'])
    assert 'mock-secret' not in ''.join(p.read_text() for p in tmp_path.iterdir())


def test_accepted_prompts_judges_and_all_historical_evidence_unchanged():
    before=json.loads((ROOT/'intelligence/docs/semantic-compact-full-contract-probe-v1/protected-before.json').read_text())
    integrity.assert_manifest_integrity(ROOT,{p:h for p,h in before.items() if p!='intelligence/ml-service/tests/protected_integrity.py'})
