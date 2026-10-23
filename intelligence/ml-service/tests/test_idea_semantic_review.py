import copy
import json
from pathlib import Path
import pytest
from fastapi import HTTPException
from app.workflow.idea_review import DIMENSIONS, VERSION, validate, preview
from app.workflow.idea_evaluation import payload_hash
from app.workflow.api import IdeaSemanticReviewRequest, idea_semantic_review
from app.workflow.creative_roles import run_paid_role, perform_role

MODEL='gpt-6-sol'

def context():
    fixture=json.loads((Path(__file__).parent/'fixtures/arda_idea_sources.json').read_text())
    return {**fixture['context'],'candidates':[dict(candidateId=c['candidateId'],payload=c['payload'],sourcePayloadSha256=payload_hash(c['payload']),originalEvaluationRevision=3) for c in fixture['candidates']]}

def review(ctx,model=MODEL):
    return dict(policyVersion=VERSION,reviewerModel=model,reviewerVersion=model,candidateReviews=[dict(candidateId=c['candidateId'],sourcePayloadSha256=c['sourcePayloadSha256'],originalEvaluationRevision=3,judgments=[dict(dimension=d,ruleId=r,verdict=('SEMANTIC_FAIL' if i==0 and d=='RULE_CONSISTENCY' else 'VISUAL_EVIDENCE_REQUIRED' if d=='ORIGINALITY_RISK' else 'SEMANTIC_PASS'),evidence=[dict(field='impossibleRule',quote=c['payload']['impossibleRule'])],comparisonEvidence=[],reason='Synthetic contract fixture only; this is not a production judgment.',confidence=.7) for d,r in DIMENSIONS.items()]) for i,c in enumerate(ctx['candidates'])])

def test_three_independent_results_with_exact_unicode_spans():
    ctx=context(); result=validate(review(ctx),ctx,MODEL)
    assert len(result['candidateReviews'])==3
    assert result['candidateReviews'][0]['semanticStatus']=='SEMANTIC_FAIL'
    for row in result['candidateReviews']:
        for j in row['judgments']:
            span=j['sourceSpans'][0]
            c=next(c for c in ctx['candidates'] if c['candidateId']==row['candidateId'])
            assert c['payload'][span['field']][span['start']:span['end']]==span['quote']
            assert j['originalEvaluationRevision']==3

@pytest.mark.parametrize('case',['hash','revision','missing_candidate','duplicate_candidate','missing_dimension','duplicate_dimension','quote','cross_candidate','no_evidence','verdict','rule','model','nan'])
def test_reject_unbound_or_malformed_judgments(case):
    ctx=context(); value=review(ctx); row=value['candidateReviews'][0]; j=row['judgments'][0]
    if case=='hash':row['sourcePayloadSha256']='0'*64
    elif case=='revision':row['originalEvaluationRevision']=2
    elif case=='missing_candidate':value['candidateReviews'].pop()
    elif case=='duplicate_candidate':value['candidateReviews'][1]=copy.deepcopy(row)
    elif case=='missing_dimension':row['judgments'].pop()
    elif case=='duplicate_dimension':row['judgments'][1]=copy.deepcopy(j)
    elif case=='quote':j['evidence'][0]['quote']='Invented claim that never existed'
    elif case=='cross_candidate':j['evidence'][0]['candidateId']=ctx['candidates'][1]['candidateId']
    elif case=='no_evidence':j['evidence']=[]
    elif case=='verdict':j['verdict']='PASS'
    elif case=='rule':j['ruleId']='FAKE_POLICY'
    elif case=='model':value['reviewerVersion']='invented-version'
    elif case=='nan':j['confidence']=float('nan')
    with pytest.raises(ValueError):validate(value,ctx,MODEL)

def test_changed_source_invalidates_prior_review():
    ctx=context(); value=review(ctx);ctx['candidates'][0]['payload']['payoff']+=' changed'
    with pytest.raises(ValueError,match='hash'):validate(value,ctx,MODEL)

@pytest.mark.parametrize('auth,budget,calls',[(False,1,1),(True,0,1),(True,-1,1),(True,.0001,1),(True,1,2),(True,float('nan'),1)])
def test_no_provider_dispatch_without_exact_authorization(monkeypatch,auth,budget,calls):
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider',lambda **kwargs:pytest.fail('SDK constructed'))
    with pytest.raises(HTTPException):
        idea_semantic_review(IdeaSemanticReviewRequest(candidates=context()['candidates'],ownerAuthorized=auth,maxCostUsd=budget,maximumProviderCalls=calls,action='REVIEW'))

def test_generic_role_requires_operation_authorization_before_sdk(monkeypatch):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','true')
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider',lambda **kwargs:pytest.fail('SDK constructed'))
    with pytest.raises(ValueError,match='authorization'):run_paid_role('IDEA_REVIEW','Review',context(),1)

def test_preview_is_no_provider_and_discloses_bounded_model(monkeypatch):
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider',lambda **kwargs:pytest.fail('SDK constructed'))
    quote=preview(context()['candidates'],{})
    assert quote['model']==MODEL and quote['maximumProviderCalls']==1
    assert quote['estimatedUpperBoundUsd']>0 and not quote['providerDispatched']

def test_isolated_transport_uses_real_parser_and_no_provider(monkeypatch,tmp_path):
    ctx=context();ctx.update(ownerAuthorized=True,maximumProviderCalls=1)
    value=review(ctx,'fixture-transport-v1')
    (tmp_path/'idea_review.json').write_text(json.dumps(value))
    monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE','true');monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_DIR',str(tmp_path));monkeypatch.setenv('POMPOM_ISOLATED_FIXTURE_TOKEN','x'*40);monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','true')
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider',lambda **kwargs:pytest.fail('SDK constructed'))
    result=run_paid_role('IDEA_REVIEW','Review saved sources',ctx,1)
    assert result['calls']==0 and result['provider']=='ISOLATED_FIXTURE' and not result['providerDispatched']
    assert result['rawProviderResponse']==json.dumps(value,ensure_ascii=False)
    assert len(result['result']['candidateReviews'])==3

def test_malformed_json_no_repair_or_second_call():
    class Provider:
        calls=0
        def complete(self,*a,**kw):self.calls+=1;return 'not JSON'
    provider=Provider()
    with pytest.raises(ValueError):perform_role('IDEA_REVIEW','Review',context(),provider,MODEL)
    assert provider.calls==1


def test_exact_displayed_ceiling_matches_existing_paid_transport_bound(monkeypatch):
    ctx=context();ctx.update(ownerAuthorized=True,maximumProviderCalls=1,storyModel=MODEL)
    quote=preview(ctx['candidates'],{})
    # Match the empty-context endpoint here; SDK is fully replaced by a local fake.
    bound={k:ctx[k] for k in ('candidates','ownerAuthorized','maximumProviderCalls','storyModel')}
    class Fake:
        last_usage={'prompt_tokens':10,'completion_tokens':10}
        last_response_metadata={'model':MODEL,'finishReason':'stop','requestId':'test-only'}
        def __init__(self,**kwargs):pass
        def complete(self,*args,**kwargs):
            self.last_request_started=True
            self.last_raw_response=json.dumps(review(bound))
            return self.last_raw_response
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','true')
    monkeypatch.delenv('POMPOM_ISOLATED_ACCEPTANCE',raising=False)
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider',Fake)
    result=run_paid_role('IDEA_REVIEW','Review the saved IDEA sources independently.',bound,quote['estimatedUpperBoundUsd'])
    assert result['costUpperBoundUsd']==quote['estimatedUpperBoundUsd']
