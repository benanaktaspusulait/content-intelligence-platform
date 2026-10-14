import json
from copy import deepcopy
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.creative_roles import perform_role
from app.workflow.optimization_comparison import assess_comparison
from app.workflow.optimization_plans import response_format,validate_plan,compile_plan
from plan_first_test_fixture import valid_plan_fixture

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
        assert 'Content profile: ABSURD_PHYSICS' in candidate['prompt']
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
    source,ctx,raw=valid_plan_fixture()
    def response(value):return ChatCompletion.model_validate({'id':'mock-plan-completion','object':'chat.completion','created':1,'model':'gpt-4o-mini-2024-07-18','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(value)},'finish_reason':'stop'}],'usage':{'prompt_tokens':1000,'completion_tokens':1400,'total_tokens':2400}})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=response(raw)
        result=run_paid_role('PROMPT_OPTIMIZATION',source,ctx,.2)
        assert result['actualCostUsd']==pytest.approx(.00099)
        call=sdk.return_value.chat.completions.create.call_args.kwargs
        assert call['max_tokens']==4000 and call['response_format']['json_schema']['name']=='protected_execution_plans'
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries']==0
    raw['plans'][1]['changes']=raw['plans'][1]['changes'][:1]
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
