import json
from copy import deepcopy
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.story_experiment import validate, preview, execute, sha
from story_experiment_fixture import inputs, alternatives


@pytest.fixture(autouse=True)
def profiles(monkeypatch):
    for key,value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_STORY_MODEL':'deepseek-chat',
                      'WORKFLOW_STORY_INPUT_USD_PER_MILLION':'.3','WORKFLOW_STORY_OUTPUT_USD_PER_MILLION':'1.2',
                      'WORKFLOW_STORY_REVIEW_MODEL':'gpt-4o-mini-2024-07-18',
                      'WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION':'.15','WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION':'.6'}.items():
        monkeypatch.setenv(key,value)


@pytest.mark.parametrize('count',[0,1,2,3])
def test_exact_count_scoped_to_pilot(count):
    text,context=inputs();values=alternatives(text,context['storyExperiment'])
    supplied=(values+[dict(values[0],candidateId='candidate-3')])[:count]
    gate=validate(text,context,{'alternatives':supplied})
    assert gate['eligible'] is (count==2)
    assert gate.get('semanticFidelity') != 'PASS'


@pytest.mark.parametrize('defect',['id','same','near','short','fields','Rex','Ada','unknown','unmapped','proposal','negation'])
def test_invalid_unknown_and_proposed_protected_changes_are_not_review_eligible(defect):
    text,context=inputs();values=alternatives(text,context['storyExperiment']);bad=values[1]
    if defect=='id':bad['candidateId']=values[0]['candidateId']
    if defect=='same':bad['text']=values[0]['text']
    if defect=='near':bad['text']=values[0]['text'].replace('careful','gentle')
    if defect=='short':bad['text']='Short.'
    if defect=='fields':bad['productionRisks']=42
    if defect in ['Rex','Ada']:bad['text']=('Rex the dragon flies to the moon. Then he sleeps. ' if defect=='Rex' else 'Ada the chef cooks soup. Then she goes home. ')*5
    if defect=='unknown':bad['sourceContract']['status']='UNKNOWN'
    if defect=='unmapped':bad['sourceContract']['bindings']=[]
    if defect=='negation':bad['text']=bad['text'].replace(context['storyExperiment']['protectedAnchors'][-1]['quote'],'Never '+context['storyExperiment']['protectedAnchors'][-1]['quote'])
    if defect=='proposal':bad['sourceContract'].update(status='PROTECTED_CHANGE_PROPOSAL',protectedChanges=[{'anchorId':'ending','proposedChange':'A different ending','justification':'Owner consideration only'}])
    gate=validate(text,context,{'alternatives':values})
    assert not gate['eligible']
    if defect=='proposal':assert gate['candidates'][1]['status']=='PROTECTED_CHANGE_PROPOSAL'


def test_variation_preserves_only_bound_facts_and_keeps_semantics_unknown():
    text,context=inputs();values=alternatives(text,context['storyExperiment'])
    assert values[0]['text']!=values[1]['text'] and all(c['text']!=text for c in values)
    gate=validate(text,context,{'alternatives':values})
    assert gate['eligible'] and all(c['status']=='SOURCE_COMPLIANT' for c in gate['candidates'])
    assert gate['semanticFidelity']=='UNKNOWN_REQUIRES_INDEPENDENT_REVIEW'


@pytest.mark.parametrize('change',['instruction','model','price','source','budget','fixture'])
def test_dispatch_mismatch_fails_before_provider_construction(monkeypatch,change):
    text,context=inputs();authorized=preview('STORY',text,context);authorized['maxCostUsd']=.1
    context['storyExperimentDispatch']=authorized
    if change=='instruction':authorized['systemSha256']='stale'
    if change=='model':monkeypatch.setenv('WORKFLOW_STORY_MODEL','different-model')
    if change=='price':monkeypatch.setenv('WORKFLOW_STORY_INPUT_USD_PER_MILLION','3')
    if change=='source':context['storyExperiment']['sourceStorySha256']='stale'
    if change=='fixture':monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE','true')
    with patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('Provider must not be constructed')):
        with pytest.raises(ValueError):execute('STORY',text,context,.00001 if change=='budget' else .1)


@pytest.mark.parametrize('mode',['valid','malformed','missing-usage','truncated','timeout','over-budget','one'])
def test_every_post_dispatch_outcome_returns_authentic_raw_usage_and_billing(mode):
    text,context=inputs();auth=preview('STORY',text,context);auth['maxCostUsd']=.1;context['storyExperimentDispatch']=auth
    class Adapter:
        def complete(self,*args,**kwargs):
            if mode=='timeout':raise TimeoutError('Offline timeout')
            self.last_usage=None if mode=='missing-usage' else {'prompt_tokens':1000000 if mode=='over-budget' else 100,'completion_tokens':200}
            self.last_response_metadata={'model':'deepseek-chat','finishReason':'length' if mode=='truncated' else 'stop'}
            values=alternatives(text,context['storyExperiment'])
            self.last_raw_response='{bad' if mode=='malformed' else json.dumps({'alternatives':values[:1] if mode=='one' else values})
            return self.last_raw_response
    with patch('app.workflow.deepseek.DeepSeekTextProvider',return_value=Adapter()):
        result=execute('STORY',text,context,.1)
    assert result['retrySafe'] is False
    assert (result['processingStatus']=='CANDIDATES_ACCEPTED') is (mode=='valid')
    if mode=='timeout':assert result['billingStatus']=='USAGE_UNKNOWN' and result['rawProviderResponse'] is None
    else:
        assert result['rawProviderResponse'] and result['responseSha256']==sha(result['rawProviderResponse'])
        assert (result['billingStatus']=='KNOWN_INCURRED') is (mode!='missing-usage')
        if mode=='malformed':assert result['actualCostUsd']==pytest.approx(.00027)


def test_unsigned_pilot_http_request_is_denied_without_transport():
    text,context=inputs()
    with patch('app.workflow.creative_roles.run_paid_role',side_effect=AssertionError('No dispatch')):
        result=TestClient(app).post('/api/v1/workflow/creative-role',json={'role':'STORY','text':text,'context':context,'maxCostUsd':.1})
    assert result.status_code==403
