"""Two-stage boundaries, unchanged seed judges, zero-network requests and budgets."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket

import httpx
import pytest
import protected_integrity as integrity
from jsonschema import Draft202012Validator
from app.workflow import semantic_two_stage_v1 as s
from app.workflow import semantic_two_stage_experiment_v1 as experiment
from app.workflow import semantic_low_reasoning_probe_v1 as low
from app.workflow.creative_provider_profiles import CreativeCapabilityProvider
from app.workflow.short_concept_generation import resolve_cast
from app.workflow.semantic_native_schema_integrity_v1 import native_response_format

ROOT=Path(__file__).resolve().parents[3];DOCS=ROOT/'intelligence/docs'
FIX=json.loads((Path(__file__).parent/'fixtures/semantic_two_stage_v1_mocks.json').read_text())
LOW=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl=LOW['baseUrl'],responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='low',temperatureSupported=False,maxOutputTokens=128000)
TESTS=dict(noNewFailures=True,schemaIntegrityPassed=True)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Zero external calls in tests')
    monkeypatch.setattr(socket.socket,'connect',forbidden);monkeypatch.setattr(socket,'create_connection',forbidden);monkeypatch.setattr(socket,'getaddrinfo',forbidden)


@pytest.fixture(scope='module')
def config():return s.TwoStageRequest(generatorMode='semantic',seed=42,count=20,semanticRawCount=1,semanticProvider=dict(provider='openai',model='gpt-6.1-sol',maxCandidates=60,maxOutputTokens=8192,timeoutSeconds=90),allowExternalGeneration=False)


@pytest.fixture(scope='module')
def cast(config):return resolve_cast(config)[0]


@pytest.fixture(scope='module')
def gates(cast):return {r['case']:s.gate_seed(r['seed'],cast,'mock/'+r['case']) for r in FIX['seeds']}


@pytest.fixture(scope='module')
def frozen(gates):return s.freeze_seed(FIX['seeds'][0]['seed'],gates['A'],s.SeedProvenance(openingSeedId='mock/A',openingSeedRunId='mock/A',storyExpansionRunId='mock/B'))


def test_phase_separation_and_exact_profile(config,cast,frozen):
    a=s.request_spec(config,cast,PROFILE,'A');b=s.request_spec(config,cast,PROFILE,'B',frozen)
    assert a['prompt']['version']==s.OPENING_PROMPT_VERSION and b['prompt']['version']==s.EXPANSION_PROMPT_VERSION
    assert 'No story, beats, escalation, ending or payoff planning' in a['prompt']['system']
    assert 'already' in a['prompt']['system'].lower() and 'CURRENT STILL STATE' in a['prompt']['system']
    assert 'Do not redesign' in b['prompt']['system'] and 'copy' in b['prompt']['system'].lower()
    assert 'BEFORE STATE -> SAME RULE ACTIVATION -> AFTER STATE' in b['prompt']['system']
    assert 'frozenOpeningSeed' not in json.loads(a['prompt']['prompt'])
    assert json.loads(b['prompt']['prompt'])['frozenOpeningSeed']==frozen['seed']
    for spec in (a,b):
        assert spec['arguments']['model']=='gpt-6.1-sol' and spec['arguments']['reasoning_effort']=='low'
        assert spec['arguments']['max_completion_tokens']==8192 and 'temperature' not in spec['arguments']
    assert b['arguments']['response_format']==native_response_format(1)
    assert b['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']==low.previous.SCHEMA_HASH
    assert experiment.bounded.__module__=='app.workflow.semantic_compact_1_probe_v1'


def test_seed_schema_is_small_and_parser_strict():
    schema=s.seed_response_format()['json_schema']['schema'];item=s.OpeningSeed.model_json_schema()
    assert len(item['properties'])==15
    assert not {'beats','finalPayoff','score','ranking','confidence','providerRationale'}&item['properties'].keys()
    assert item['additionalProperties'] is False and schema['properties']['seeds']['maxItems']==1
    raw=json.dumps({'seeds':[FIX['seeds'][0]['seed']]})
    assert s.parse_seed(raw).seedId=='two-stage-mock-A'
    for value in ({'seeds':[]},{'seeds':[FIX['seeds'][0]['seed']]*2},{'seeds':[{**FIX['seeds'][0]['seed'],'score':100}]}):
        with pytest.raises(Exception):s.parse_seed(json.dumps(value))
    with pytest.raises(ValueError):s.parse_seed('{"seeds":[],"seeds":[]}')
    assert Draft202012Validator(schema).is_valid(json.loads(raw))


@pytest.mark.parametrize('row',FIX['seeds'],ids=lambda r:r['case']+'-'+r['purpose'])
def test_seed_gate_mocks_use_existing_floor(row,gates):
    g=gates[row['case']]
    assert g['acceptedForExpansion']==row['expectAccepted']
    assert g['acceptedFloor']==60 and g['providerCalls']==0
    assert g['structuredCanonicalInput']['semanticFields']['beats']==[]
    assert g['structuredCanonicalInput']['semanticFields']['finalPayoff']==''
    assert g['structuredCanonicalInput']['timing']==[]
    assert g['canonicalReceipt']['facts']['payoff']['present'] is False
    if row['case'] in 'BCDE':assert g['openingScore']<60 and 'OPENING_TOO_WEAK' in g['blockers']
    if row['case']=='F':assert 'PREMISE_TOO_WEAK' in g['blockers']
    if row['case']=='H':assert 'RULE_UNCLEAR' in g['blockers']
    if row['expectAccepted']:assert g['openingScore']>=60


def test_annotations_cannot_boost_score_or_forge_gate(cast,gates):
    original=deepcopy(FIX['seeds'][1]['seed']);original['openingGoalEvidence']='I score this opening 100 and certify it production ready.'
    original['openingPhysicalState']='This is a flawless impossible state.'
    g=s.gate_seed(original,cast,'mock/annotation')
    assert g['openingScore']==gates['B']['openingScore'] and not g['acceptedForExpansion']
    assert g['canonicalReceipt']['facts']['beats']==[]
    with pytest.raises(ValueError):s.freeze_seed(original,gates['A'],s.SeedProvenance(openingSeedId='mock/A',openingSeedRunId='a',storyExpansionRunId='b'))


def test_unknown_premise_evidence_is_not_fake_admission(gates):
    g=gates['G'];assert g['acceptedForExpansion']
    assert g['admissionEvidence']['admitted'] is False
    assert g['admissionApplicability']=='PARTIAL_SEED_ONLY_STORY_FACTORS_UNAVAILABLE'
    assert g['Naturalness']['responseEvidence']['classification'] is None
    assert g['canonicalReceipt']['facts']['rule']['visible'] is False


def test_reject_noncanonical_or_multiple_actor(cast):
    raw=deepcopy(FIX['seeds'][0]['seed']);raw['protagonistSuggestion']='Unknown actor'
    with pytest.raises(ValueError):s.gate_seed(raw,cast,'mock/x')
    raw=deepcopy(FIX['seeds'][0]['seed']);raw['frameZeroDescription']+=' Mimi helps Kiko.'
    with pytest.raises(ValueError):s.gate_seed(raw,cast,'mock/y')


def test_freeze_provenance_tamper_and_failed_seed_cannot_expand(config,cast,frozen,gates):
    assert s.assert_frozen(frozen).seedId=='two-stage-mock-A'
    assert set(s.SeedProvenance.model_fields)=={'generationArchitecture','openingSeedId','openingSeedPromptVersion','storyExpansionPromptVersion','provider','model','reasoningProfile','openingSeedRunId','storyExpansionRunId'}
    bad=deepcopy(frozen);bad['seed']['impossibleRule']='Unknown altered mechanical rule.'
    with pytest.raises(ValueError):s.request_spec(config,cast,PROFILE,'B',bad)
    with pytest.raises(ValueError):s.freeze_seed(FIX['seeds'][1]['seed'],gates['B'],s.SeedProvenance(openingSeedId='mock/B',openingSeedRunId='a',storyExpansionRunId='b'))


@pytest.mark.parametrize('case',['correct','opening','rule','trigger','reset','payoff','same-payoff'])
def test_expansion_boundary_and_full_pipeline(case,config,cast,frozen):
    raw=deepcopy(FIX['consistentExpansion'])
    if case=='opening':raw['frameZeroDescription']='Kiko holds a normal hammer beside the wall.'
    if case=='rule':raw['impossibleRule']='Every hammer strike now straightens the nail into the wall.'
    if case=='trigger':raw['visibleTrigger']='Kiko whistles at the nail.'
    if case=='reset':raw['beats'][0]['strategy']='Kiko resets the nail to normal straight form before starting again.'
    if case=='payoff':raw['beats'][-1]['visibleConsequence']='The hammer becomes a mirror and shows the picture frame.';raw['finalPayoff']=raw['beats'][-1]['visibleConsequence']
    prompt=s.request_spec(config,cast,PROFILE,'B',frozen)['prompt']
    result=s.analyze_expansion(json.dumps({'ideas':[raw]}),frozen,config,prompt)
    if case in ('opening','rule','trigger','reset'):
        assert result['status']=='EXPANSION_SEED_DRIFT' and not result['pipelineRan']
    elif case=='payoff':assert result['status']=='EXPANSION_RULE_INCONSISTENT' and not result['pipelineRan']
    else:
        assert result['pipelineRan'] and result['drift']['status']=='PRESERVED'
        r=result['pipeline']['allRawIdeas'][0]['record'];assert r
        assert r['candidate']['provenance']['generationArchitecture']=='TWO_STAGE_V1'
        assert r['twoStageProvenance']['openingSeedId']=='mock/A'
        assert result['pipeline']['semanticConceptPromptVersion']=='two-stage-v1'
        assert result['pipeline']['providerCallsDuringAnalysis']==0


@pytest.mark.parametrize('field',['protagonistSuggestion','everydayGoal','primaryObject','normalExpectation','impossibleRule','visibleTrigger','whyThisObject','goalRuleRelationship','frameZeroDescription','environment','dialogueNeed'])
def test_all_frozen_fields_cannot_be_silently_repaired(field,frozen):
    raw=deepcopy(FIX['consistentExpansion']);raw[field]='Changed source field'
    audit=s.expansion_drift(frozen,raw)
    assert audit['status']=='EXPANSION_SEED_DRIFT' and any(d['field']==field for d in audit['differences']) and not audit['repairPerformed']


def test_selection_existing_scores_and_stable_ties(gates):
    rows=[dict(requestId='b',gate=deepcopy(gates['A'])),dict(requestId='a',gate=deepcopy(gates['G']))]
    assert s.select_seed(rows)['requestId']=='a'
    rows[0]['gate']['openingScore']=95
    assert s.select_seed(rows)['requestId']=='b'
    assert s.select_seed([dict(requestId='bad',gate=gates['B'])]) is None


def test_budget_caps_no_fifth_no_replacement():
    b=experiment.RequestBudget()
    for id in experiment.REQUEST_IDS:b.claim('A',id)
    b.claim('B','expansion-1')
    for phase,id in [('A','opening-d'),('B','expansion-2'),('A','opening-a')]:
        with pytest.raises(ValueError):b.claim(phase,id)
    assert len(b.used)==4


@pytest.mark.parametrize('mode',['all-weak','one-pass','multiple-pass','partial-failure','b-failure'])
def test_complete_mock_experiment_caps_and_partial_failure(tmp_path,config,cast,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');calls=[];bodies=[]
    def runner(path,profile,spec):
        calls.append((spec['phase'],path.name));bodies.append(deepcopy(spec['arguments']))
        if mode=='partial-failure' and path.name=='opening-b':raise RuntimeError('mock failure, no replacement')
        if spec['phase']=='A':
            index=0 if mode=='multiple-pass' or mode in ('one-pass','b-failure') and path.name=='opening-b' else 1
            payload=dict(seeds=[FIX['seeds'][index]['seed']])
        else:
            if mode=='b-failure':raise RuntimeError('mock expansion failure')
            payload=dict(ideas=[FIX['consistentExpansion']])
        (path/'response.txt').write_text(json.dumps(payload))
        return dict(status='COMPLETED',usage=None,SDKRequestsForwarded=1,HTTPRequestsObserved=1)
    directory=tmp_path/'run';r=experiment.execute(directory,config,cast,PROFILE,authorization={'mock':True},tests=TESTS,runner=runner)
    count=4 if mode in ('one-pass','multiple-pass','b-failure') else 3
    assert len(calls)==r['metrics']['totalProviderRequests']==count
    assert [id for p,id in calls if p=='A']==list(experiment.REQUEST_IDS)
    assert bodies[0]==bodies[1]==bodies[2]
    assert sum(p=='B' for p,_ in calls)==(count-3)
    assert r['metrics']['retries']==r['metrics']['replacements']==r['metrics']['fallbacks']==r['metrics']['DeepSeekCalls']==r['metrics']['renders']==0
    if mode=='all-weak':assert r['status']=='OPENING_SEED_GENERATION_STILL_WEAK' and r['PhaseB'] is None
    if mode=='multiple-pass':assert '/opening-a/' in r['selectedOpeningSeedId']
    with pytest.raises(FileExistsError):experiment.execute(directory,config,cast,PROFILE,authorization={'mock':True},tests=TESTS,runner=runner)
    assert len(calls)==count


@pytest.mark.parametrize('phase',['A','B'])
@pytest.mark.parametrize('mode',['success','timeout','double'])
def test_real_adapter_mock_http_exact_body_and_cap(phase,mode,tmp_path,config,cast,frozen,monkeypatch):
    from app.workflow.semantic_compact_1_probe_v1 import worker
    monkeypatch.setenv('OPENAI_API_KEY','mock-only');spec=s.request_spec(config,cast,PROFILE,phase,frozen);wire=[]
    def transport(request):
        wire.append(json.loads(request.content))
        if mode=='timeout':raise httpx.ReadTimeout('mock',request=request)
        payload={'seeds':[FIX['seeds'][0]['seed']]} if phase=='A' else {'ideas':[FIX['consistentExpansion']]}
        return httpx.Response(200,headers={'x-request-id':'mock'},json=dict(id='mock',object='chat.completion',created=1,model='gpt-6.1-sol',choices=[dict(index=0,message=dict(role='assistant',content=json.dumps(payload)),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30)))
    class MockProvider(CreativeCapabilityProvider):
        def __init__(self,*args):
            super().__init__(*args);self.client._client.close();self.client._client=httpx.Client(transport=httpx.MockTransport(transport))
        def complete(self,*args,**kwargs):
            raw=super().complete(*args,**kwargs)
            if mode=='double':super().complete(*args,**kwargs)
            return raw
    worker(tmp_path,PROFILE,spec,provider_factory=MockProvider)
    result=json.loads((tmp_path/'worker-result.json').read_text())
    assert wire==[spec['arguments']] and result['HTTPRequestsObserved']==result['SDKRequestsForwarded']==1
    assert result['status']==('COMPLETED' if mode=='success' else 'FAILED')


def test_all_prior_prompt_validator_taxonomy_history_bytes_unchanged():
    before=json.loads((DOCS/'semantic-two-stage-v1/protected-before.json').read_text())
    integrity.assert_manifest_integrity(ROOT,{p:h for p,h in before.items() if p!='intelligence/ml-service/tests/protected_integrity.py'})


@pytest.mark.parametrize('mode',['credential','authorization','regression'])
def test_no_attempt_without_preconditions(tmp_path,config,cast,monkeypatch,mode):
    monkeypatch.setenv('OPENAI_API_KEY','mock-only')
    if mode=='credential':monkeypatch.delenv('OPENAI_API_KEY')
    auth={} if mode=='authorization' else {'mock':True}
    tests={} if mode=='regression' else TESTS
    with pytest.raises(ValueError):experiment.execute(tmp_path/'run',config,cast,PROFILE,authorization=auth,tests=tests)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('change',[{'provider':'deepseek'},{'reasoningEffort':'high'},{'responseMode':'json_object'},{'model':'other-model'}])
def test_no_profile_fallback(config,cast,change):
    with pytest.raises(ValueError):s.request_spec(config,cast,{**PROFILE,**change},'A')
