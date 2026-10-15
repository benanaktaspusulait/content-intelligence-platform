import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.creative_roles import perform_role
from app.workflow.creative_reconstruction import diagnose, compile_reconstruction, assess_candidate, metrics
from app.workflow.optimization_comparison import assess_comparison
from app.workflow.review import review_prompt
from app.parser.prompt_parser import source_plan_evidence

FIXTURE=Path(__file__).parent/'fixtures/mimi-creative-v2.json'
def fixture(): return json.loads(FIXTURE.read_text())
def plan(identity='candidate-a',op='CONTACT_PLANE:beat_01',operation='CONTACT_PLANE',layout='DEPTH',camera='LOCKED'):
    return {'candidateId':identity,'title':'Spatially legible contact choreography',
        'objective':'Show the intended destination and wrong-surface attachment in a continuous, unobstructed contact view.',
        'interventions':[{'opportunityId':op,'operation':operation,'layout':layout,'camera':camera,
            'rationale':'A separated contact plane may make the existing intention and wrong attachment distinguishable; actual clarity is unverified.'}],
        'storyChangeRequested':False}
def response(plans=None):
    return {'proposals':[{'initial':p,'revision':None} for p in (plans if plans is not None else [plan()])], 'noImprovementReason':None}
class MockProvider:
    def __init__(self,value):self.value=value;self.calls=0
    def complete(self,prompt,system='',**kwargs):
        self.calls+=1;self.payload=json.loads(prompt);self.system=system
        return json.dumps(self.value)
def run(value=None):
    f=fixture();provider=MockProvider(response() if value is None else value)
    result=perform_role('PROMPT_OPTIMIZATION',f['text'],f['context'],provider,'mock-only')
    return f,provider,result

def canonical_review(f,candidate):
    source=source_plan_evidence(candidate['prompt'],'creative-v2','UNSAVED','1.11')
    # Same source-plan producer/consumer mapping used by WorkflowService.reviewCreativeCandidate.
    beats=[]
    for b in source['videoPlanIR']['beats']:
        beats.append({**{k:b[k] for k in ('id','startTime','endTime','sourceSpan','sourceQuote')},'action':b.get('sourceAction') or b['sourceQuote'],'semanticStatus':'PENDING'})
    request={**f['boundRequest'],'prompt':candidate['prompt'],'sourceId':'creative-v2','sourceVersion':'UNSAVED',
        'structuredPlan':{'schemaVersion':'source-bound-beats-v1','evidenceStatus':'DETERMINISTIC_SOURCE_EVENTS_ONLY','sourceVersion':'UNSAVED','beats':beats},
        'acceptedStartFrame':False,'authorizationEvidence':{}}
    return review_prompt(request,{})

def test_actual_saved_mimi_full_role_source_canonical_comparison_pipeline():
    f,provider,result=run()
    assert provider.calls==1
    assert provider.payload['creativeDiagnosis']['protectedStoryContract']['sourcePromptSha256']=='0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98'
    c=result['result']['candidates'][0]
    assert 'Stage the cabinet and her finger on separate foreground and background planes' in c['prompt']
    assert 'visible gap to the intended destination' in c['prompt']
    assert all(event in c['prompt'] for event in f['context']['essentialEvents'])
    assert 'each pull doubles the number of sticky notes' in c['prompt']
    assert 'Mimi is relieved but the cabinet remains visibly messy.' in c['prompt']
    with patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No paid provider')):
        c['review']=canonical_review(f,c)
    assert c['review']['canonicalRuleEvaluation']['status']=='EVALUATED'
    assessment=assess_comparison(f['text'],[c],f['context'],f['baselineScore'])
    assert assessment['actualCandidateCount']==1 and assessment['integrityStatus']=='COMPLETE_CANDIDATE_SET'
    assert assessment['candidates'][0]['classification']=='PLAUSIBLE_IMPROVEMENT_UNVERIFIED'
    assert assessment['recommendation']=='REVIEW_MATERIAL_CANDIDATE'
    assert assessment['candidates'][0]['creativeAssessment']['provenBetter'] is False
    assert c['sourceEventCoverage']['semanticFidelity']=='UNKNOWN'
    # A complete revised prompt, not a fake higher-score fixture, is the acceptance evidence.
    assert c['review']['canonicalRuleEvaluation']['score']==pytest.approx(f['baselineScore'])

@pytest.mark.parametrize('kind',['CAMERA_LABEL','TIMING_SPLIT'])
def test_cosmetic_and_timestamp_only_variants_rejected(kind):
    p=plan();p['interventions'][0]['operation']=kind
    f,provider,result=run(response([p]))
    assert not result['result']['candidates']
    assert result['result']['outcome']=='NO_JUSTIFIED_IMPROVEMENT'
    assert result['result']['rejectedProposals'][0]['classification']=='VALID_BUT_EQUIVALENT'
    assert provider.calls==1

def test_two_distinct_material_plans_and_explicit_counted_choreography():
    b=plan('candidate-b','COUNTABLE_STATE_PATH:beat_03','COUNTABLE_STATE_PATH','LATERAL')
    f,_,r=run(response([plan(),b]))
    assert len(r['result']['candidates'])==2
    assert 'two → four → eight' in r['result']['candidates'][1]['prompt']
    assert 'group positions stable' in r['result']['candidates'][1]['prompt']
    assert r['result']['candidates'][0]['prompt']!=r['result']['candidates'][1]['prompt']

@pytest.mark.parametrize('defect',['story','camera-risk','unchanged'])
def test_story_deviation_execution_regression_and_unchanged_staging(defect):
    p=plan()
    if defect=='story':p['storyChangeRequested']=True
    if defect=='camera-risk':p['interventions'][0]['camera']='TRACK'
    if defect=='unchanged':p['interventions'][0]['layout']='UNCHANGED'
    _,_,r=run(response([p]))
    assert r['result']['candidates']==[]
    expected={'story':'STORY_CHANGE_REQUIRES_APPROVAL','camera-risk':'REGRESSION','unchanged':'VALID_BUT_EQUIVALENT'}[defect]
    assert r['result']['rejectedProposals'][0]['classification']==expected

def test_bounded_revision_uses_same_response_no_additional_call():
    p=plan(camera='TRACK');raw=response([p]);raw['proposals'][0]['revision']=plan()
    _,provider,r=run(raw)
    assert provider.calls==1 and len(r['result']['candidates'])==1
    assert r['result']['critiqueCycles'][0]['revisionsUsed']==1
    assert r['rawProviderResult']==raw

def test_keep_original_without_forced_candidates_or_fake_metrics():
    raw={'proposals':[],'noImprovementReason':'No source-supported production change is justified without the missing visual evidence.'}
    f,_,r=run(raw)
    assert assess_comparison(f['text'],r['result']['candidates'],f['context'],f['baselineScore'])['recommendation']=='KEEP_ORIGINAL'
    m=r['result']['improvementMetrics']
    assert m['materialCandidateSuccessRate'] is None and m['callsWithoutAcceptableCandidate']==1
    assert m['defensibleOperatorPreferenceRate'] is None and m['providerCostUsd'] is None

def test_saved_recovery_routes_v2_without_provider_and_preserves_raw_result():
    f=fixture();raw=response()
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('No SDK')):
        r=TestClient(app).post('/api/v1/workflow/optimization-recovery',json={'text':f['text'],'context':f['context'],'providerResult':raw,'diagnostics':{}})
    assert r.status_code==200,r.text
    assert r.json()['calls']==0 and r.json()['rawProviderResult']==raw

def test_tampered_prompt_and_plan_cannot_claim_compiler_proof():
    f,_,r=run();c=r['result']['candidates'][0]
    c['prompt']=c['prompt'].replace('Mimi sees herself in a mirror and screams','Mimi dances instead')
    a=assess_candidate(f['text'],c,f['context'],f['baselineScore'])
    assert a['classification']=='STORY_FIDELITY_FAILED' and not a['approvalEligible']

def test_curiosity_discovery_does_not_force_causality_at_frame_zero():
    f=fixture();f['context']['openingStrategy']='CURIOSITY_DISCOVERY'
    d=diagnose(f['text'],f['context'])
    assert not any(o['operation']=='CONTACT_PLANE' for o in d['opportunities'])
    assert len(d['dimensions'])==6 and d['endingReview']['loopRequired'] is False

def test_actual_canonical_regression_not_hidden_by_materiality():
    f,_,r=run();c=r['result']['candidates'][0]
    c['review']={'canonicalRuleEvaluation':{'status':'EVALUATED','score':80,'failedRules':[{'ruleId':'NEW_FAILURE'}]}}
    a=assess_candidate(f['text'],c,f['context'],f['baselineScore'])
    assert a['classification']=='REGRESSION' and not a['approvalEligible']
    assert a['creativeAssessment']['newCanonicalFailures']==['NEW_FAILURE']

def test_model_claim_cannot_turn_hypothetical_benefit_into_observed_uplift():
    p=plan();p['interventions'][0]['rationale']='This will increase audience retention by 20 percent.'
    _,_,r=run(response([p]));assert r['result']['candidates']==[]
    assert 'UNSUPPORTED_AUDIENCE_OR_RENDER_CLAIM' in r['result']['rejectedProposals'][0]['reasons']

def test_v2_paid_adapter_mocked_sdk_cost_budget_and_no_retry(monkeypatch):
    from app.workflow.creative_roles import run_paid_role
    from openai.types.chat import ChatCompletion
    f=fixture()
    for key,value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'mock-v2','WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'.15','WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'.6','OPENAI_API_KEY':'mock-only'}.items():monkeypatch.setenv(key,value)
    answer=ChatCompletion.model_validate({'id':'mock-v2','object':'chat.completion','created':1,'model':'mock-v2','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(response())},'finish_reason':'stop'}],'usage':{'prompt_tokens':3000,'completion_tokens':1500,'total_tokens':4500}})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=answer
        result=run_paid_role('PROMPT_OPTIMIZATION',f['text'],f['context'],.1)
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries']==0
        assert sdk.return_value.chat.completions.create.call_args.kwargs['response_format']['json_schema']['name']=='creative_reconstruction_v2'
        assert result['actualCostUsd']==pytest.approx(.00135)
        assert result['result']['improvementMetrics']['providerCostUsd']==pytest.approx(.00135)
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        with pytest.raises(ValueError,match='cost ceiling'):run_paid_role('PROMPT_OPTIMIZATION',f['text'],f['context'],.000001)
        sdk.assert_not_called()
