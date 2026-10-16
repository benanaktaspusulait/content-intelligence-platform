import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.creative_roles import perform_role
from app.workflow.optimization_comparison import assess_comparison
from app.workflow.optimization_plans import response_format,validate_plan,compile_plan
from plan_first_test_fixture import valid_plan_fixture,source_owned_plan_fixture

class MockProvider:
    def __init__(self,result):self.result=result;self.calls=0
    def complete(self,prompt,system='',**kwargs):
        self.calls+=1;self.payload=json.loads(prompt);self.system=system
        return json.dumps(self.result)

def test_material_plans_pass_before_compilation_and_protect_story():
    source,ctx,raw=valid_plan_fixture();provider=MockProvider(raw)
    result=perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock-plan-only')
    assert provider.calls==1 and provider.payload['phase']=='MATERIAL_IMPROVEMENT_PLANS'
    assert result['rawProviderResult']==raw and result['promptCompilation']=='DETERMINISTIC_AFTER_PLAN_VALIDATION'
    assert len(result['result']['candidates'])==2
    contract=result['result']['protectedStoryContract']
    assert contract['corePhysicalRule']['sourceQuote']=='each pull doubles the number of sticky notes'
    assert contract['semanticStoryFidelity']=='UNKNOWN'
    assert contract['targetContentProfile']=='ABSURD_PHYSICS' and contract['baselinePromptHistoricalProfile']=='AUTO'
    for candidate in result['result']['candidates']:
        assert all(anchor in candidate['prompt'] for anchor in ctx['essentialEvents'])
        assert 'Content profile: AUTO' in candidate['prompt']
        assert candidate['targetContentProfile']=='ABSURD_PHYSICS'
        assert candidate['profileValidation']['status']=='HISTORICAL_PROFILE_REPRESENTATION_PRESERVED'
        assert 'Mimi is relieved but the cabinet remains visibly messy.' in candidate['prompt']
        assert candidate['planValidation']['storyFidelity']=='UNKNOWN'
    assessment=assess_comparison(source,result['result']['candidates'],ctx,85)
    assert all(c['classification']=='VALID_WITH_UNPROVEN_BENEFIT' for c in assessment['candidates'])

@pytest.mark.parametrize('invalid',['cosmetic','time-only','wrong-span','missing-event','wrong-order','audience-claim','camera-label-evidence','unrelated-focus'])
def test_nonmaterial_or_unfaithful_plans_fail_before_any_full_prompt(invalid):
    source,ctx,raw=valid_plan_fixture()
    if invalid=='cosmetic':raw['plans'][0]['changes'][0]['focusBindings']=[]
    if invalid=='time-only':raw['plans'][1]['changes']=raw['plans'][1]['changes'][:1]
    if invalid=='wrong-span':raw['plans'][0]['changes'][0]['focusBindings'][0]['quote']='invented cabinet'
    if invalid=='missing-event':raw['plans'][0]['preservedStoryAnchors'].pop()
    if invalid=='wrong-order':raw['plans'][1]['changes'].reverse()
    if invalid=='audience-claim':raw['plans'][0]['materialDifference']='This will deliver guaranteed retention improvement.'
    if invalid=='camera-label-evidence':raw['plans'][0]['changes'][0]['focusBindings']=[{'quote':"close-up on Mimi's hand"},{'quote':'her finger'}]
    if invalid=='unrelated-focus':raw['plans'][0]['changes'][0]['focusBindings']=[{'quote':'Mimi reaches'},{'quote':'looking determined'}]
    provider=MockProvider(raw)
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError):perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
        compiler.assert_not_called()
    assert provider.last_role_result==raw and provider.calls==1

def test_same_actions_under_timestamps_are_not_a_plan():
    source,ctx,raw=valid_plan_fixture();raw['plans'][1]['changes'][1]['stateSequence']=[]
    with pytest.raises(ValueError,match='complete explicit source progression'):validate_plan(source,ctx,raw['plans'][1])

def test_current_historical_minor_decision_is_unchanged():
    from plan_first_test_fixture import ROW
    source,ctx,_=valid_plan_fixture();original=deepcopy(ROW['attemptDiagnostics']['providerResultForRecovery']['candidates'])
    assert assess_comparison(source,original,ctx,85)['recommendation']=='KEEP_ORIGINAL'

def test_recovery_endpoint_uses_same_plan_first_path_without_sdk():
    source,ctx,raw=valid_plan_fixture()
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('No provider calls')):
        response=TestClient(app).post('/api/v1/workflow/optimization-recovery',json={'text':source,'context':ctx,'providerResult':raw,'diagnostics':{'model':'mock-plan-provider'}})
    assert response.status_code==200,response.text
    assert response.json()['calls']==0 and len(response.json()['result']['candidates'])==2

def test_schema_keeps_real_title_field_and_exact_two_plans():
    schema=response_format()['json_schema']['schema']
    assert schema['properties']['plans']['minItems']==schema['properties']['plans']['maxItems']==2
    assert 'title' in schema['$defs']['Plan']['properties']

def test_paid_adapter_is_mocked_and_sends_one_plan_request_with_budget_and_raw_recovery(monkeypatch):
    from app.workflow.creative_roles import run_paid_role,CreativeRoleFailure
    from openai.types.chat import ChatCompletion
    for k,v in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'gpt-4o-mini-2024-07-18','WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'.15','WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'.6','OPENAI_API_KEY':'mock-not-a-key'}.items():monkeypatch.setenv(k,v)
    source,ctx,raw=source_owned_plan_fixture()
    def response(value):return ChatCompletion.model_validate({'id':'mock-plan-completion','object':'chat.completion','created':1,'model':'gpt-4o-mini-2024-07-18','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(value)},'finish_reason':'stop'}],'usage':{'prompt_tokens':1000,'completion_tokens':1400,'total_tokens':2400}})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=response(raw)
        result=run_paid_role('PROMPT_OPTIMIZATION',source,ctx,.2)
        assert result['actualCostUsd']==pytest.approx(.00099)
        call=sdk.return_value.chat.completions.create.call_args.kwargs
        assert call['max_tokens']==4000 and call['response_format']['json_schema']['name']=='protected_execution_plans'
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries']==0
    raw['escalationPlan']['progressionChange']['executionOptionId']='action-consequence:beat_02'
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=response(raw)
        with pytest.raises(CreativeRoleFailure) as error:run_paid_role('PROMPT_OPTIMIZATION',source,ctx,.2)
        assert error.value.diagnostics['providerResultForRecovery']==raw
        assert error.value.diagnostics['actualCostUsd']==pytest.approx(.00099)
        assert error.value.diagnostics['retrySafe'] is False
        sdk.return_value.chat.completions.create.assert_called_once()

def test_incomplete_timing_fails_before_full_prompt_compilation():
    source,ctx,raw=valid_plan_fixture();raw['plans'][0]['changes'][0]['endTime']=1.0
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError,match='timing'):perform_role('PROMPT_OPTIMIZATION',source,ctx,MockProvider(raw),'mock')
        compiler.assert_not_called()

@pytest.mark.parametrize('field,claim',[
    ('proposedVisualConsequence','This will improve audience retention by 20%.'),
    ('materialDifference','Viewer response improves with this plan.'),
    ('baselineOpportunity','Completion rate will increase by 15 percentage points.'),
    ('title','Guaranteed retention improvement'),
    ('risksIntroduced','Guaranteed render success.'),
    ('risksReducedHypotheses','This doubles watch time.'),
    ('unknowns','Audience retention is 20% higher.'),
    ('risksReducedHypotheses','Clearer escalation may lead to better audience retention.'),
])
def test_unsupported_outcome_claims_in_all_plan_fields_fail_before_compilation(field,claim):
    source,ctx,raw=valid_plan_fixture()
    raw['plans'][0][field]=[claim] if field in ('risksIntroduced','risksReducedHypotheses','unknowns') else claim
    provider=MockProvider(raw)
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError,match='unsupported audience or render evidence'):
            perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
        compiler.assert_not_called()
    assert provider.last_role_result==raw and provider.calls==1

def test_unmeasured_audience_unknowns_do_not_block_source_bound_execution_hypotheses():
    source,ctx,raw=valid_plan_fixture()
    raw['plans'][0]['unknowns']=['Audience retention and viewer response are unmeasured.']
    assert validate_plan(source,ctx,raw['plans'][0])['creativeBenefit']=='HYPOTHESIS_ONLY'
    raw['plans'][0]['unknowns']=['Whether audience retention increases remains UNKNOWN.']
    assert validate_plan(source,ctx,raw['plans'][0])['creativeBenefit']=='HYPOTHESIS_ONLY'
    raw['plans'][0]['unknowns']=['Unmeasured retention requires actual audience evidence.','No proven retention improvement is established.','No guaranteed render success is established.']
    assert validate_plan(source,ctx,raw['plans'][0])['creativeBenefit']=='HYPOTHESIS_ONLY'

def test_actual_attempt_73_is_rejected_without_rewriting_or_a_second_provider_call():
    saved=json.loads((Path(__file__).parent/'fixtures/optimization-73-plan-contract.json').read_text())
    source=saved['sourceRequest']['text'];ctx=saved['sourceRequest']['context'];raw=saved['providerResult']
    provider=MockProvider(raw)
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError,match='candidate-a.*Increased viewer engagement'):
            perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
        compiler.assert_not_called()
    assert provider.last_role_result==raw and provider.calls==1
    for p in raw['plans']:
        # Removing the audience claim still cannot repair its missing story anchors.
        p=deepcopy(p);p['risksReducedHypotheses']=['Contact visibility may reduce causal ambiguity.']
        with pytest.raises(ValueError,match='all 5 approved event anchors'):
            validate_plan(source,ctx,p)

def test_request_explains_complete_anchors_and_exact_binding_shapes_without_invented_evidence():
    source,ctx,raw=valid_plan_fixture();provider=MockProvider(raw)
    perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
    protocol=provider.payload['bindingProtocol']
    assert provider.payload['instructionsVersion']=='plan-first-owned-source-v3'
    assert protocol['exactPreservedStoryAnchorsForBOTHPlans']==ctx['essentialEvents']
    opening=protocol['openingRequiredBindings']
    assert opening['focusBindings']==[{'quote':'the cabinet'},{'quote':'her finger'}]
    assert opening['stateSequence']==[]
    assert protocol['explicitProgressionBindingOptions'][0]['stateSequence']==[{'quote':'two'},{'quote':'four'},{'quote':'eight'}]
    for pair in protocol['actionConsequenceBindingOptions']:
        event=next(e for e in provider.payload['protectedStoryContract']['events'] if e['sourceBeatId']==pair['sourceBeatId'])
        before,after=event['sourceQuote'].split('->',1)
        assert pair['focusBindings'][0]['quote'] in before and pair['focusBindings'][1]['quote'] in after
        assert pair['stateSequence']==[]
    definitions=provider.response_format['json_schema']['schema']['$defs']
    assert definitions['OpeningChoice']['properties']['executionOptionId']['enum']==['opening:beat_01']
    assert definitions['ProgressionChoice']['properties']['executionOptionId']['enum']==['progression:beat_03']
    assert 'sourceQuote' not in definitions['OpeningChoice']['properties']
    assert 'Do not return sourceQuote' in provider.system
    assert 'increased engagement' in provider.system

def test_source_owned_provider_choices_compile_exact_quotes_and_distinct_strategies():
    source,ctx,raw=source_owned_plan_fixture();provider=MockProvider(raw)
    result=perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
    assert provider.calls==1 and provider.last_role_result==raw and result['rawProviderResult']==raw
    events={e['sourceBeatId']:e for e in provider.payload['protectedStoryContract']['events']}
    for plan in result['result']['plans']:
        assert plan['preservedStoryAnchors']==ctx['essentialEvents']
        for change in plan['changes']:assert change['sourceQuote']==events[change['sourceBeatId']]['sourceQuote']
    assert [c['stagingMode'] for c in result['result']['plans'][1]['changes']]==['ACTION_CONSEQUENCE_PAIR','DISTINCT_STATE_HOLDS']
    assert all(c['planValidation']['storyFidelity']=='UNKNOWN' for c in result['result']['candidates'])
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('No paid recovery')):
        response=TestClient(app).post('/api/v1/workflow/optimization-recovery',json={'text':source,'context':ctx,'providerResult':raw,'diagnostics':{}})
    assert response.status_code==200,response.text
    assert response.json()['calls']==0 and response.json()['result']==json.loads(json.dumps(result['result']))

@pytest.mark.parametrize('defect',['invented-id','wrong-family','two-action-pairs','copied-source-quote'])
def test_source_owned_options_reject_invalid_choice_without_compiling(defect):
    source,ctx,raw=source_owned_plan_fixture()
    if defect=='invented-id':raw['openingPlan']['openingChange']['executionOptionId']='opening:invented'
    if defect=='wrong-family':raw['openingPlan']['openingChange']['executionOptionId']='progression:beat_03'
    if defect=='two-action-pairs':raw['escalationPlan']['progressionChange']['executionOptionId']='action-consequence:beat_02'
    if defect=='copied-source-quote':raw['openingPlan']['openingChange']['sourceQuote']='fragment'
    provider=MockProvider(raw)
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError):perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
        compiler.assert_not_called()
    assert provider.last_role_result==raw and provider.calls==1

def test_actual_attempt_41_has_truncated_quotes_and_missing_progression_and_stays_rejected():
    saved=json.loads((Path(__file__).parent/'fixtures/optimization-41-source-quote.json').read_text());req=saved['sourceRequest'];raw=saved['providerResult']
    provider=MockProvider(raw)
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError,match='source quote differs'):perform_role('PROMPT_OPTIMIZATION',req['text'],req['context'],provider,'mock')
        compiler.assert_not_called()
    assert provider.last_role_result==raw
    from app.workflow.optimization_distinctness import _beats
    beats={b['id']:b for b in _beats(req['text'])};second=deepcopy(raw['plans'][1])
    for change in second['changes']:change['sourceQuote']=beats[change['sourceBeatId']]['sourceQuote']
    with pytest.raises(ValueError,match='distinct source actions and ordered state exposure'):
        validate_plan(req['text'],req['context'],second)

def test_unsupported_source_catalog_fails_before_provider_creation(monkeypatch):
    from app.workflow.creative_roles import run_paid_role
    from types import SimpleNamespace
    source,ctx,_=source_owned_plan_fixture()
    for k,v in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'gpt-4o-mini-2024-07-18','WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'.15','WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'.6'}.items():monkeypatch.setenv(k,v)
    with patch('app.workflow.optimization_plans.parse_prompt',return_value=SimpleNamespace(video_plan_ir={})),patch('app.workflow.creative_roles.OpenAIProvider') as factory:
        with pytest.raises(ValueError,match='opening evidence is UNKNOWN'):run_paid_role('PROMPT_OPTIMIZATION',source,ctx,.2)
        factory.assert_not_called()

def test_current_generation_cannot_fall_back_to_legacy_text_copy_output():
    source,ctx,raw=valid_plan_fixture();ctx['optimizationGenerationInstructionsVersion']='plan-first-owned-source-v3'
    provider=MockProvider(raw)
    with patch('app.workflow.optimization_plans.compile_plan') as compiler:
        with pytest.raises(ValueError,match='source-owned openingPlan and escalationPlan'):
            perform_role('PROMPT_OPTIMIZATION',source,ctx,provider,'mock')
        compiler.assert_not_called()
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('No paid recovery')):
        response=TestClient(app).post('/api/v1/workflow/optimization-recovery',json={'text':source,'context':ctx,'providerResult':raw,'diagnostics':{}})
    assert response.status_code==200 and response.json()['calls']==0
