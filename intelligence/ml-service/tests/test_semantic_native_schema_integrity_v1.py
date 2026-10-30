"""Offline reference/equivalence/wire tests; all provider requests are mocks."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import httpx
import pytest
from jsonschema import Draft202012Validator
from referencing.exceptions import Unresolvable

from app.workflow import semantic_native_schema_integrity_v1 as integrity
from app.workflow import semantic_schema_integrity_probe_v1 as probe
from app.workflow.semantic_concept_provider import SemanticIdea,parse_response
from app.workflow.semantic_concept_adapter import normalize_idea
from app.workflow.semantic_prompt_v2_experiment import configuration_for
from app.workflow.short_concept_generation import resolve_cast

ROOT=Path(__file__).parents[2]
FIXTURE=Path(__file__).parent/'fixtures/semantic_schema_integrity_full_candidate_v1.json'
DATA=json.loads(FIXTURE.read_text())
OLD_REQUEST=json.loads((ROOT/'docs/semantic-provider-contract-decomposition-v1-run-001/probe-e/request.json').read_text())
OLD=OLD_REQUEST['arguments']['response_format']
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl='https://example.invalid',responseMode='json_schema',
    tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False,maxOutputTokens=128000)


def test_old_native_wrapper_reproduces_unresolved_root_reference():
    schema=OLD['json_schema']['schema'];audit=integrity.reference_audit(schema)
    assert len(audit)==1 and audit[0]['reference']=='#/$defs/SemanticBeat' and audit[0]['status']=='UNRESOLVED'
    assert audit[0]['resolvedTargetPath'] is None
    with pytest.raises(Unresolvable):list(Draft202012Validator(schema).iter_errors({'ideas':[DATA]}))
    with pytest.raises(ValueError,match='FINAL_PROVIDER_SCHEMA_VALIDATION'):integrity.final_provider_schema_validation(schema)


def test_corrected_full_schema_syntax_all_refs_and_fixture():
    fmt=integrity.native_response_format(1);schema=fmt['json_schema']['schema']
    assert schema['$defs']['SemanticBeat']==SemanticIdea.model_json_schema()['$defs']['SemanticBeat']
    assert '$defs' not in schema['properties']['ideas']['items']
    audit=integrity.reference_audit(schema)
    assert len(audit)==1 and audit[0]['status']=='RESOLVED' and audit[0]['resolvedTargetPath']=='/$defs/SemanticBeat'
    assert integrity.final_provider_schema_validation(schema)['unresolvedReferences']==0
    Draft202012Validator(schema).validate({'ideas':[DATA]})
    assert integrity.semantic_equivalence_proof(schema)['candidateLogicalSchemaIdentical']


def test_complete_audit_includes_hidden_unused_external_and_cycle():
    schema=integrity.native_response_format()['json_schema']['schema'];schema['$defs']['unused']={'$ref':'#/$defs/missing'}
    assert any(r['status']=='UNRESOLVED' for r in integrity.reference_audit(schema))
    with pytest.raises(ValueError):integrity.final_provider_schema_validation(schema)
    schema['$defs']['unused']={'$ref':'https://example.invalid/no-fetch'}
    assert any(r['status']=='UNSUPPORTED_REFERENCE_FORM' for r in integrity.reference_audit(schema))
    cycle={'type':'object','additionalProperties':False,'properties':{'node':{'$ref':'#/$defs/node'}},'$defs':{'node':{'type':'object','properties':{'next':{'$ref':'#/$defs/node'}}}}}
    assert all(r['status']=='CYCLIC_REFERENCE' for r in integrity.reference_audit(cycle))


def test_json_pointer_escaping_and_root_resolution():
    schema={'$defs':{'a/b~c':{'type':'string'}},'properties':{'x':{'$ref':'#/$defs/a~1b~0c'}}}
    assert integrity.reference_audit(schema)[0]['status']=='RESOLVED'
    assert integrity.reference_audit({'$ref':'#'})[0]['status']=='CYCLIC_REFERENCE'


@pytest.mark.parametrize('mutation',[
    lambda d:d['ideas'][0].pop('everydayGoal'),
    lambda d:d['ideas'][0]['beats'][0].pop('strategy'),
    lambda d:d['ideas'][0]['beats'][0].update(strategy=1),
    lambda d:d['ideas'][0].update(extra='not allowed'),
    lambda d:d['ideas'][0]['beats'][0].update(extra='not allowed'),
    lambda d:d.update(extra='not allowed'),
    lambda d:d['ideas'][0].update(beats=d['ideas'][0]['beats'][:3]),
    lambda d:d['ideas'][0].update(beats=d['ideas'][0]['beats']*2),
    lambda d:d['ideas'][0].update(dialogueNeed='MINIMAL'),
    lambda d:d['ideas'][0].update(primaryObject=None),
])
def test_malformed_missing_nested_extra_enum_and_item_constraints(mutation):
    value={'ideas':[deepcopy(DATA)]};mutation(value)
    assert list(Draft202012Validator(integrity.native_response_format()['json_schema']['schema']).iter_errors(value))


@pytest.mark.parametrize('mutation',[
    lambda c:c['properties'].pop('loopPotential'),
    lambda c:c['properties']['everydayGoal'].update(type='number'),
    lambda c:c['required'].remove('beats'),
    lambda c:c['properties']['beats'].update(minItems=3),
    lambda c:c['properties']['dialogueNeed']['enum'].append('MINIMAL'),
    lambda c:c['properties']['primaryObject'].update(type=['string','null']),
    lambda c:c.update(additionalProperties=True),
    lambda c:c['properties']['durationSeconds'].update(default=16),
])
def test_semantic_equivalence_detects_contract_changes(mutation):
    schema=integrity.native_response_format()['json_schema']['schema'];mutation(schema['properties']['ideas']['items'])
    with pytest.raises(ValueError,match='contract changed'):integrity.semantic_equivalence_proof(schema)


def test_round_trip_domain_json_schema_parser_normalizer_preserves_meaning():
    obj=SemanticIdea.model_validate(DATA);assert set(obj.model_dump())==set(SemanticIdea.model_fields)
    value={'ideas':[obj.model_dump(mode='json')]};schema=integrity.native_response_format()['json_schema']['schema']
    Draft202012Validator(schema).validate(value);ideas,rejections=parse_response(json.dumps(value),60)
    assert not rejections and ideas[0].model_dump()==obj.model_dump()
    cfg=configuration_for(PROFILE);cast,_=resolve_cast(cfg)
    prompt=dict(version='semantic-concept-prompt-v2',sha256='offline-fixture-no-provider')
    before=normalize_idea(obj,cfg,cast,prompt);after=normalize_idea(ideas[0],cfg,cast,prompt)
    assert before==after
    assert after['providerData']['rawFinalPayoff']==DATA['finalPayoff']
    assert after['providerData']['rawFrameZeroDescription']==DATA['frameZeroDescription']


def test_historically_domain_valid_payloads_remain_structurally_valid():
    sources=[json.loads((ROOT/'ml-service/app/workflow/semantic_concept_mock_v1.json').read_text())['ideas'],
        json.loads((ROOT/'docs/semantic-live-v1-seed-42-count-40/live-attempt/response.txt').read_text())['ideas']]
    pairs=json.loads((Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json').read_text())['cases']
    sources.extend([[p[key] for p in pairs] for key in ['mockV1','mockV2']])
    canonical=Draft202012Validator(SemanticIdea.model_json_schema());provider=Draft202012Validator(integrity.native_response_format()['json_schema']['schema'])
    total=0
    for source in sources:
        ideas,_=parse_response(json.dumps({'ideas':source}),60)
        for idea in ideas:
            data=idea.model_dump(mode='json');canonical.validate(data);provider.validate({'ideas':[data]});total+=1
    assert total>=60


def test_last_mile_guard_rejects_transformed_broken_object_before_sdk():
    calls=[];fmt=integrity.native_response_format()
    guard=integrity.LastMileSchemaGuard(lambda **kw:calls.append(kw),fmt,lambda *a:None)
    with pytest.raises(ValueError,match='Last-mile'):guard(response_format=OLD)
    assert calls==[] and guard.forwarded==0


def test_last_mile_guard_detects_post_validation_recording_mutation():
    calls=[];fmt=integrity.native_response_format()
    def mutate(args,receipt):args['response_format']['json_schema']['schema'].pop('$defs')
    guard=integrity.LastMileSchemaGuard(lambda **kw:calls.append(kw),fmt,mutate)
    with pytest.raises(ValueError,match='mutated after final'):guard(response_format=deepcopy(fmt))
    assert calls==[] and guard.forwarded==0


def test_actual_installed_sdk_mock_wire_receives_exact_validated_schema(monkeypatch):
    from app.workflow.creative_provider_profiles import CreativeCapabilityProvider
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');wire=[];receipts=[]
    fmt=integrity.native_response_format()
    def transport(request):
        payload=json.loads(request.content);wire.append(payload)
        assert payload['response_format']==fmt
        integrity.final_provider_schema_validation(payload['response_format']['json_schema']['schema'])
        return httpx.Response(200,json={'id':'mock-completion','object':'chat.completion','created':1,'model':'gpt-6.1-sol',
            'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps({'ideas':[DATA]})},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':1,'completion_tokens':2,'total_tokens':3}})
    provider=CreativeCapabilityProvider(PROFILE,8192,90);provider.client._client.close()
    provider.client._client=httpx.Client(transport=httpx.MockTransport(transport))
    provider.response_format=fmt
    guard=integrity.LastMileSchemaGuard(provider.client.chat.completions.create,fmt,lambda args,receipt:receipts.append((deepcopy(args),receipt)))
    provider.client.chat.completions.create=guard
    assert provider.complete('Generate one fictional example.',system='Return JSON only.')
    assert len(wire)==len(receipts)==guard.forwarded==1
    assert wire[0]['response_format']==receipts[0][0]['response_format']
    assert receipts[0][1]['step']=='FINAL_PROVIDER_SCHEMA_VALIDATION' and receipts[0][1]['unresolvedReferences']==0
    assert 'mock-secret' not in json.dumps(receipts)
    with pytest.raises(ValueError,match='One SDK'):guard(**receipts[0][0])
    provider.client.close()


def test_native_non_strict_compatibility_preserves_optional_defaults():
    fmt=integrity.native_response_format();audit=integrity.native_compatibility_audit(fmt)
    assert audit['strict'] is False and all(o['additionalProperties'] is False for o in audit['objects'])
    assert any(not o['allPropertiesRequired'] for o in audit['objects'])
    assert audit['knownUnsupportedKeywordsFromRepository'] is None


def test_minimal_corrected_probe_only_schema_changes():
    spec=probe.plan(OLD_REQUEST)
    before=deepcopy(OLD_REQUEST['arguments']);after=deepcopy(spec['arguments'])
    before.pop('response_format');after.pop('response_format');assert before==after
    assert all('RULE IMMUTABILITY' not in m['content'] for m in spec['arguments']['messages'])
    assert spec['integrity']['unresolvedReferences']==0


def test_monotonic_and_utc_recording_normal_and_clock_jump():
    start=datetime(2026,10,26,tzinfo=UTC)
    normal=probe.timing_record(start,start+timedelta(seconds=.5),10,500_000_010)
    assert normal['timingConsistent'] and normal['monotonicElapsedSeconds']==.5
    jump=probe.timing_record(start,start+timedelta(seconds=600),10,500_000_010)
    assert not jump['timingConsistent'] and jump['wallClockEndUTC']==(start+timedelta(seconds=600)).isoformat()
    assert jump['monotonicElapsedSeconds']==.5


def test_one_probe_no_retry_no_pipeline_and_history_unchanged(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock-secret');calls=[]
    prompt_path=ROOT/'ml-service/app/workflow/semantic_concept_prompt_v2.txt';before=hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    def runner(path,profile,spec):
        calls.append(1);(path/'response.txt').write_text(json.dumps({'ideas':[DATA]}))
        return dict(status='COMPLETED',usage={'prompt_tokens':1,'completion_tokens':2,'total_tokens':3})
    kwargs=dict(authorization={'file':'test'},tests={'noNewFailures':True,'schemaIntegrityPassed':True},runner=runner)
    path=tmp_path/'probe';result=probe.execute(path,PROFILE,OLD_REQUEST,**kwargs)
    assert result['primaryClassification']=='FULL_SCHEMA_EXECUTION_CONFIRMED_AFTER_SCHEMA_REPAIR'
    assert result['creativePipelineCalls']==result['DeepSeekCalls']==result['retries']==result['fallbacks']==0
    assert result['timing']['timingConsistent']
    with pytest.raises(FileExistsError):probe.execute(path,PROFILE,OLD_REQUEST,**kwargs)
    assert calls==[1] and before==hashlib.sha256(prompt_path.read_bytes()).hexdigest()


def test_no_probe_before_offline_integrity_or_authorization(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','mock')
    with pytest.raises(ValueError):probe.execute(tmp_path/'p',PROFILE,OLD_REQUEST)
    with pytest.raises(ValueError):probe.execute(tmp_path/'p',PROFILE,OLD_REQUEST,authorization={'file':'test'},tests={'noNewFailures':True})
    assert not (tmp_path/'p').exists()
