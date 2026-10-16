"""TEST_FIXTURE diagnostic comparisons, never independent creative evidence."""
import copy,json,os
from pathlib import Path
from unittest.mock import patch
import pytest
from app.workflow import draft_comparative_review as m
ROOT=Path(__file__).resolve().parents[3]
SPEC=json.loads((ROOT/'intelligence/backend/src/main/resources/cpq/mimi-draft-comparison-v1.json').read_text())
PACKET=(ROOT/'intelligence/docs/CPQ_V1_MIMI_FIRST_CREATIVE_COMPARISON_BLIND_PACKET.md').read_text()
def data(reverse=False):
    packets=[dict(label=l,prompt=PACKET.split('## Prompt '+l+'\n\n```text\n')[1].split('\n```')[0]) for l in ['A','B']]
    return dict(purpose=m.POLICY,instructionVersion=m.INSTRUCTIONS,responseSchemaVersion=m.SCHEMA,reviewerInstructions=SPEC['reviewerInstructions'],productionSettings=SPEC['effectiveProductionContext'],packets=packets[::-1] if reverse else packets)
def result(judgment='EQUIVALENT'):
    d=dict(judgment=judgment,evidence=[dict(label='A',quote='as a cleanup reminder'),dict(label='B',quote='looking determined')],absentEvidenceExplanation='',reason='TEST_FIXTURE compares two literal instructions; not real creative evidence.',weaknessesOrRisks=['TEST_FIXTURE unverified visual legibility.'],targetedSuggestion='TEST_FIXTURE inspect the visible cleanup cue.',uncertainty='TEST_FIXTURE rendered readability is unverified.')
    return dict(dimensions={dim:copy.deepcopy(d) for dim in m.DIMENSIONS},overall=dict(judgment=judgment,rationale='TEST_FIXTURE comparison mechanics only.',strongestDifference='TEST_FIXTURE specific cleanup-intention wording.',unresolvedIssue='TEST_FIXTURE no rendered evidence.',blockingRegressions=[],uncertainty='TEST_FIXTURE not calibrated independent review.'))
@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        yield
        sdk.assert_not_called()
@pytest.mark.parametrize('judgment',m.JUDGMENTS)
def test_all_legitimate_comparative_outcomes_and_reverse_order(judgment):
    assert m.validate(result(judgment),data())==m.validate(result(judgment),data(True))
@pytest.mark.parametrize('defect',['wrong_label','fabricated','missing_dimension','missing_pairwise','empty_unexplained','extra_metadata'])
def test_reject_incomplete_or_wrongly_attributed_comparisons(defect):
    r=result();d=r['dimensions'][m.DIMENSIONS[0]]
    if defect=='wrong_label':d['evidence'][0]['label']='B'
    if defect=='fabricated':d['evidence'][0]['quote']='invented not in either prompt'
    if defect=='missing_dimension':r['dimensions'].pop(m.DIMENSIONS[-1])
    if defect=='missing_pairwise':d.pop('judgment')
    if defect=='empty_unexplained':d['evidence']=[]
    if defect=='extra_metadata':r['sourceFidelity']='PASS'
    with pytest.raises(Exception):m.validate(r,data())
def test_insufficient_evidence_can_explain_absent_quotes():
    r=result('INSUFFICIENT_EVIDENCE')
    for d in r['dimensions'].values():d.update(evidence=[],absentEvidenceExplanation='TEST_FIXTURE actual rendered readability is absent from both textual inputs.')
    m.validate(r,data())
def test_blind_request_and_specific_budget_configuration():
    for identity,effort,tokens in [('deepseek-primary','none',6000),('openai-escalation','low',8000)]:
        pre=m.preflight(dict(input=data(),profileId=identity));assert pre['reasoningEffort']==effort and pre['maxOutputTokens']==tokens and pre['maxCalculatedCostUsd']>0
        sent=json.dumps(data());assert all(secret not in sent for secret in ['supervisorMapping','88.40625','OWNER_DECISION','sourceFidelityDecision','DRAFT_ONLY','promptSha256'])
@pytest.mark.parametrize('failure',['none','empty','truncated','bad_quote'])
def test_mock_provider_retains_raw_output_and_accounting_without_sdk(failure):
    class Provider:
        def __init__(self,cfg,tokens,timeout):self.last_usage=dict(prompt_tokens=1000,completion_tokens=1000);self.last_response_metadata=dict(model=cfg['model'],finishReason='length' if failure=='truncated' else 'stop',apiStatus='COMPLETED',requestId='TEST_FIXTURE_RESPONSE');self.last_raw_response=''
        def complete(self,prompt,**kwargs):
            assert '88.40625' not in prompt and 'supervisorMapping' not in prompt
            r=result()
            if failure=='bad_quote':r['dimensions'][m.DIMENSIONS[0]]['evidence'][0]['quote']='fabricated'
            self.last_raw_response='' if failure=='empty' else json.dumps(r);return self.last_raw_response
    pre=m.preflight(dict(input=data(),profileId='openai-escalation'));auth={k:pre[k] for k in ['provider','model','reasoningEffort','maxOutputTokens']};auth.update(profileId='openai-escalation',authorizePaidInference=True,automaticRetries=False,maxCostUsd=.20)
    out=m.execute(dict(requestId='TEST_FIXTURE_REQUEST',input=data(),authorization=auth),Provider)
    assert out['executionStatus']==('COMPLETED' if failure=='none' else 'FAILED_OR_AMBIGUOUS');assert out['usageAccountingStatus']=='COMPLETE' and out['costUsd']>0
    if failure!='none':assert 'comparison' not in out

def test_unauthorized_call_does_not_construct_provider():
    with patch.object(m,'CreativeCapabilityProvider') as sdk:
        with pytest.raises(ValueError):m.execute(dict(input=data(),authorization=dict(profileId='openai-escalation'),requestId='TEST_FIXTURE'))
        sdk.assert_not_called()
@pytest.mark.parametrize('identity,effort,token_key,tokens',[('deepseek-primary','none','max_tokens',6000),('openai-escalation','low','max_completion_tokens',8000)])
def test_exact_adapter_payload_has_no_retry_tools_or_hidden_synthesis(identity,effort,token_key,tokens,monkeypatch):
    from types import SimpleNamespace
    from app.workflow.creative_provider_profiles import CreativeCapabilityProvider
    cfg=m.config(identity);monkeypatch.setenv(cfg['provider'].upper()+'_API_KEY','TEST_FIXTURE_KEY_NOT_REAL')
    usage=SimpleNamespace(model_dump=lambda:dict(prompt_tokens=1000,completion_tokens=1000))
    completion=SimpleNamespace(id='TEST_FIXTURE_RESPONSE',model=cfg['model'],usage=usage,choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(result())))])
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=completion
        auth=dict(profileId=identity,provider=cfg['provider'],model=cfg['model'],reasoningEffort=effort,maxOutputTokens=tokens,maxCostUsd=.20,authorizePaidInference=True,automaticRetries=False)
        response=m.execute(dict(requestId='TEST_FIXTURE_REQUEST',input=data(),authorization=auth),CreativeCapabilityProvider)
        assert response['executionStatus']=='COMPLETED'
        assert sdk.call_args.kwargs['max_retries']==0
        args=sdk.return_value.chat.completions.create.call_args.kwargs
        assert args[token_key]==tokens and args['reasoning_effort']==effort
        assert args['response_format']['type']==cfg['responseMode'] and 'tools' not in args
        assert len(args['messages'])==2 and sdk.return_value.chat.completions.create.call_count==1


def test_preference_citation_requirement_is_explicit_in_bound_request():
    text=data()['reviewerInstructions']
    assert 'A AND at least one from B' in text
    assert 'A reason mentioning B does not replace a B excerpt' in text
    assert m.INSTRUCTIONS=='PAIRWISE_CREATIVE_INSTRUCTIONS_V2'
