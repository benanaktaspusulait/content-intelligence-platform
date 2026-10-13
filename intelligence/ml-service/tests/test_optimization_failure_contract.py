"""Saved real request; provider outputs/usage here are explicitly mocked evidence."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from openai.types.chat import ChatCompletion
from app.workflow.creative_roles import run_paid_role, CreativeRoleFailure, OPTIMIZATION_RESPONSE_FORMAT

REQUEST=json.loads((Path(__file__).parent/'fixtures/optimization-failed-request.json').read_text())

def setup(monkeypatch):
    for key,val in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'gpt-4o-mini-2024-07-18','WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'.15','WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'.6','OPENAI_API_KEY':'fixture-not-a-key'}.items():monkeypatch.setenv(key,val)

def candidates():
    from optimization_test_fixture import valid_optimization_fixture
    return valid_optimization_fixture()[2]

def sdk_response(content):
    return ChatCompletion.model_validate(dict(id='fixture-completion',object='chat.completion',created=1,model='gpt-4o-mini-2024-07-18',choices=[dict(index=0,message=dict(role='assistant',content=content),finish_reason='stop')],usage=dict(prompt_tokens=1000,completion_tokens=1500,total_tokens=2500)))

@pytest.mark.parametrize('rejection', ['unchanged-source','duplicate-revision','missing-essential','invalid-json','missing-usage','cost-over-limit'])
def test_real_saved_request_rejection_is_classified_without_losing_response(monkeypatch,rejection):
    setup(monkeypatch);values=candidates();category='CANDIDATE_STRUCTURE_INVALID'
    if rejection=='unchanged-source':values[0]['prompt']=REQUEST['text']
    if rejection=='duplicate-revision':values[1]['prompt']=values[0]['prompt']
    if rejection=='missing-essential':values[1]['prompt']='Unsupported replacement';category='STORY_FIDELITY_VALIDATION_FAILED'
    response=sdk_response('invalid json' if rejection=='invalid-json' else json.dumps({'candidates':values}))
    if rejection=='invalid-json':category='PROVIDER_RESPONSE_SCHEMA_ERROR'
    if rejection=='missing-usage':response.usage=None;category='PROVIDER_USAGE_MISSING'
    if rejection=='cost-over-limit':response.usage.completion_tokens=400000;category='COST_CEILING_EXCEEDED'
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=response
        with pytest.raises(CreativeRoleFailure) as failure:run_paid_role(REQUEST['role'],REQUEST['text'],{**REQUEST['context'],'attemptId':'fixture-attempt'},.2)
        d=failure.value.diagnostics
        assert d['category']==category and d['providerDispatched'] and d['providerResponseReturned']
        assert d['attemptId']=='fixture-attempt' and d['retrySafe'] is False and not d['candidatesSaved']
        assert d['tokenUsage']==({'inputTokens':1000,'outputTokens':400000 if rejection=='cost-over-limit' else 1500} if rejection!='missing-usage' else None)
        if rejection not in ['missing-usage','cost-over-limit']:assert d['actualCostUsd']==pytest.approx(.00105)
        if rejection not in ['invalid-json']:assert d['providerResultForRecovery']['candidates']==values
        sdk.return_value.chat.completions.create.assert_called_once()

def test_realistic_sdk_success_keeps_usage_candidate_contract_and_zero_automatic_approval(monkeypatch):
    setup(monkeypatch)
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=sdk_response(json.dumps({'candidates':candidates()}))
        result=run_paid_role(REQUEST['role'],REQUEST['text'],REQUEST['context'],.2)
        assert result['actualCostUsd']==pytest.approx(.00105) and result['approvedCostCeilingUsd']==.2
        assert len(result['result']['candidates'])==2 and result['validationStatus']=='NOT_VALIDATED'
        call=sdk.return_value.chat.completions.create.call_args.kwargs
        assert call['response_format']['type']=='json_schema' and call['max_tokens']==2000
        schema=call['response_format']['json_schema']
        assert schema['strict'] is True
        items=schema['schema']['properties']['candidates']
        assert items['minItems']==items['maxItems']==2
        assert items['items']['additionalProperties'] is False
        assert set(items['items']['required'])=={'candidateId','title','hypothesis','prompt','targetContentProfile'}
        assert items['items']['properties']['targetContentProfile']['enum']==['ABSURD_PHYSICS']
        assert sdk.call_args.kwargs['max_retries']==0
        sdk.return_value.chat.completions.create.assert_called_once()

def test_saved_nested_candidate_response_remains_rejected_and_recoverable(monkeypatch):
    setup(monkeypatch)
    fixture=json.loads((Path(__file__).parent/'fixtures/optimization-da-nested.json').read_text())
    request=fixture['request']; recovered=fixture['response']
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=sdk_response(json.dumps(recovered))
        with pytest.raises(CreativeRoleFailure) as failure:
            run_paid_role(request['role'],request['text'],request['context'],.2)
        diagnostics=failure.value.diagnostics
        assert diagnostics['category']=='CANDIDATE_STRUCTURE_INVALID'
        assert 'received 1' in diagnostics['validationError'] and 'nested' in diagnostics['validationError']
        assert diagnostics['providerResultForRecovery']==recovered
        assert diagnostics['retrySafe'] is False and not diagnostics['candidatesSaved']
        sdk.return_value.chat.completions.create.assert_called_once()
