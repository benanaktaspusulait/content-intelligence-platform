from copy import deepcopy
import json,os,uuid
from unittest.mock import patch
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.story_assessment import preview,wire,sources,validate_review,execute
from app.workflow.story_experiment import validate
from story_experiment_fixture import assessment_inputs,assessment_review,assessment_failed_check

@pytest.fixture(autouse=True)
def configuration(monkeypatch,tmp_path):
    for k,v in {'WORKFLOW_STORY_REVIEW_MODEL':'gpt-4o-mini-2024-07-18','WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION':'.15','WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION':'.6','WORKFLOW_CREATIVE_ROLES_ENABLED':'true','CPQ_PILOT_REAL_ENABLED':'true','POMPOM_DATA_ROOT':str(tmp_path)}.items():monkeypatch.setenv(k,v)
    for k in ('POMPOM_ISOLATED_ACCEPTANCE','POMPOM_ISOLATED_FIXTURE_DIR','POMPOM_ISOLATED_FIXTURE_TOKEN'):monkeypatch.delenv(k,raising=False)


def grant():
    text,context=assessment_inputs();p=preview(text,context);p['maxCostUsd']=.1
    context.update(assessmentDispatch=p,assessmentSpendingAuthorized=True,storyRequestId=str(uuid.uuid4()))
    return text,context


def test_two_real_cross_run_sources_derived_without_claim_authority():
    text,c=assessment_inputs();selected=sources(text,c)
    assert len(selected)==2 and selected[0]['provenance']['historicalIdentityMatch'] is False
    assert selected[0]['provenance']['originalRunId']!=selected[1]['provenance']['originalRunId']
    assert all(x['semanticFidelity']=='UNKNOWN' and x['researchStatus']=='SEMANTIC_FIDELITY_REVIEW_REQUIRED' for x in selected)
    assert selected[1]['derivedEvidence']['invalidCitationsExcluded'][0]['anchorId']=='continuity'
    w=wire(text,c);assert w['payload']['originalStory']==text and all(x['narrative'] in json.dumps(w['payload']) for x in selected)
    assert 'SOURCE_COMPLIANT' not in json.dumps(w['payload'])


@pytest.mark.parametrize('change',['sha','raw','selected','known-violation','proposal','incomplete','contradiction','identity'])
def test_unverifiable_or_excluded_sources_never_prepare(change):
    text,c=assessment_inputs();entry=c['assessmentScope']['candidates'][0]
    if change=='sha':entry['candidateSha256']='changed'
    if change=='raw':entry['receipt']['rawProviderResponse']='{}'
    if change=='selected':entry['candidateId']='candidate-1'
    if change=='known-violation':entry['knownDefiniteSourceViolation']=True
    if change=='proposal':entry['originalCandidate']['sourceContract']['status']='PROTECTED_CHANGE_PROPOSAL'
    if change=='incomplete':entry['originalCandidate']['text']='Short'
    if change=='contradiction':entry['originalCandidate']['text']=entry['originalCandidate']['text'].replace('Pip is relieved','Pip is not relieved')
    if change=='identity':entry['receipt']['providerResponseMetadata']['model']='invented'
    with pytest.raises(ValueError):preview(text,c)


def test_strict_gate_still_rejects_both_historical_pairs():
    text,c=assessment_inputs();scope=c['assessmentScope']['sourceScope'];ctx={'storyExperiment':{'version':'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1','requestedAlternativeCount':2,'sourceStorySha256':scope['sourceStorySha256'],'sourceScopeSha256':scope['sourceScopeSha256'],'protectedAnchors':scope['protectedAnchors']}}
    for item in c['assessmentScope']['candidates']:
        assert not validate(text,ctx,json.loads(item['receipt']['rawProviderResponse']))['eligible']


@pytest.mark.parametrize('failure',['missing-grant','changed-model','changed-price','changed-instruction','changed-sha'])
def test_exact_owner_spending_binding_before_provider_construction(monkeypatch,failure):
    text,c=grant()
    if failure=='missing-grant':c.pop('assessmentSpendingAuthorized')
    if failure=='changed-model':monkeypatch.setenv('WORKFLOW_STORY_REVIEW_MODEL','other')
    if failure=='changed-price':monkeypatch.setenv('WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION','2')
    if failure=='changed-instruction':c['assessmentDispatch']['systemSha256']='changed'
    if failure=='changed-sha':c['assessmentScope']['candidates'][0]['candidateSha256']='changed'
    with patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('No provider')),patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('No generation')):
        with pytest.raises(ValueError):execute(text,c,.1)


@pytest.mark.parametrize('failure',['semantic-pass-from-unknown','semantic-fail-proposal','missing-semantics','missing-dimension','fake-quote'])
def test_semantic_before_creative_and_exact_evidence(failure):
    text,c=assessment_inputs();value=assessment_review(wire(text,c)['payload']);row=value['candidateAssessments']['A']
    if failure=='semantic-pass-from-unknown':row['semanticOutcome']='SEMANTIC_SOURCE_PASS'
    if failure=='semantic-fail-proposal':
        assessment_failed_check(value,wire(text,c)['payload']);row['eligibleForOwnerProposal']=True
    if failure=='missing-semantics':row['semanticChecks']={}
    if failure=='missing-dimension':row['creativeDimensions'].pop(next(iter(row['creativeDimensions'])))
    if failure=='fake-quote':row['semanticChecks']['identity']['candidateEvidenceIds']=['invented-id']
    with pytest.raises(ValueError):validate_review(value,text,c)


@pytest.mark.parametrize('mode',['positive','malformed','timeout','fail-source'])
def test_review_receipt_survives_failures_and_has_no_production_authority(mode):
    text,c=grant()
    class Adapter:
        def complete(self,prompt,**kwargs):
            if mode=='timeout':raise TimeoutError('Offline simulated timeout')
            value=assessment_review(json.loads(prompt))
            if mode=='fail-source':
                assessment_failed_check(value,json.loads(prompt))
            self.last_raw_response='{bad' if mode=='malformed' else json.dumps(value)
            self.last_usage={'prompt_tokens':100,'completion_tokens':200};self.last_response_metadata={'model':'gpt-4o-mini-2024-07-18','finishReason':'stop'}
            return self.last_raw_response
    with patch('app.llm.openai_provider.OpenAIProvider',return_value=Adapter()):result=execute(text,c,.1)
    assert (result['processingStatus']=='INDEPENDENT_REVIEW_COMPLETED') is (mode in ('positive','fail-source'))
    if mode=='timeout':assert result['billingStatus']=='USAGE_UNKNOWN'
    else:
        assert result['actualCostUsd']==pytest.approx(.000135)
        saved=json.loads(Path(result['rawReceiptFile']).read_text());assert saved['capturedBeforeParsing'] and saved['rawProviderResponse']==result['rawProviderResponse']
    with patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('No replay')):
        with pytest.raises(FileExistsError):execute(text,c,.1)


def test_unsigned_assessment_rejected_without_provider():
    text,c=assessment_inputs()
    with patch('app.workflow.creative_roles.run_paid_role',side_effect=AssertionError('No dispatch')):
        r=TestClient(app).post('/api/v1/workflow/creative-role',json={'role':'STORY_REVIEW','text':text,'context':c,'maxCostUsd':.1})
    assert r.status_code==403
