"""No-egress protocol fixtures; never evidence of real creative quality."""
import copy
import hashlib
import json
import pytest
from app.workflow import owner_machine_pilot as pilot

@pytest.fixture
def config(monkeypatch):
    cfg={'provider':'openai','model':'fixture-model','documentedVersion':'fixture-v1','maxOutputTokens':4000,'contextTokens':100000,'inputUsdPerMillion':1,'outputUsdPerMillion':1}
    monkeypatch.setattr(pilot,'profile',lambda identity:cfg)
    return cfg

def data(source=False):
    prompt='Mimi pulls a note. She sneezes; the cabinet stays messy.'
    return {'policyVersion':pilot.POLICY,'evidenceType':'MACHINE_REVIEW','purpose':'SOURCE_FIDELITY' if source else 'CREATIVE_CRITIC','packets':[{'neutralId':q,'prompt':prompt,'promptSha256':hashlib.sha256(prompt.encode()).hexdigest(),'productionSettings':{'generator':'SEEDANCE_2_0_MINI','desiredDuration':15},**({'approvedStory':prompt,'originalPrompt':prompt,'changedBeats':[{'beatId':'beat_01'}]} if source else {})} for q in ['Q01','Q02']]}

def result(source=False):
    results=[]
    for q in ['Q01','Q02']:
        if source:
            r={'neutralId':q,'decision':'PASS','rationale':'TEST_FIXTURE only; not an actual creative or source judgment.','uncertainty':'Rendered adherence unverified.','conflict':False,'omissions':[],'additions':[],'productionRisks':[],'mappings':[{'anchor':a,'beatId':'beat_01','sourceQuote':'Mimi','promptQuote':'Mimi'} for a in pilot.ANCHORS]}
        else:
            dim={'level':'ADEQUATE','strengths':['TEST_FIXTURE staged contact'],'weaknesses':['TEST_FIXTURE quantity risk'],'improvements':['TEST_FIXTURE inspect contact'],'productionConstraints':['15 seconds'],'uncertainty':'No visual evidence.','rationale':'TEST_FIXTURE reasoning only, not real quality evidence.','citations':['Mimi']}
            r={'neutralId':q,'dimensions':{k:copy.deepcopy(dim) for k in pilot.DIMENSIONS},'productionRisks':['TEST_FIXTURE no actual render'],'improvementHypotheses':[]}
        results.append(r)
    return {'results':results}

def request(source=False):
    return {'requestId':'fixture-request','input':data(source),'authorization':{'profileId':'fixture','provider':'openai','model':'fixture-model','authorizePaidInference':True,'automaticRetries':False,'maxOutputTokens':4000,'maxCostUsd':.1}}

class Fake:
    calls=[]
    def __init__(self,*args):pass
    def complete(self,prompt,**kwargs):
        self.calls.append(json.loads(prompt))
        self.last_usage={'prompt_tokens':100,'completion_tokens':100}
        self.last_response_metadata={'model':'fixture-model'}
        self.last_raw_response=json.dumps(result(json.loads(prompt)['purpose']=='SOURCE_FIDELITY'))
        return self.last_raw_response

@pytest.mark.parametrize('source',[False,True])
def test_separate_machine_evidence_and_actual_usage(config,source):
    out=pilot.execute(request(source),Fake)
    assert out['executionStatus']=='COMPLETED'
    assert out['evidenceType']=='MACHINE_REVIEW' and out['costUsd']==.0002
    assert 'grade' not in out and out['requestId']=='fixture-request'

@pytest.mark.parametrize('change',[lambda r:r['results'][0]['dimensions'].pop(pilot.DIMENSIONS[0]),lambda r:r['results'][0]['dimensions'][pilot.DIMENSIONS[0]].update(citations=[]),lambda r:r['results'][0]['dimensions'][pilot.DIMENSIONS[0]].update(citations=['invented quote']),lambda r:r['results'][0].update(grade='A+')])
def test_bad_critic_contract_rejected(config,change):
    r=result();change(r)
    with pytest.raises(Exception):pilot.validate(r,data())

@pytest.mark.parametrize('issue',['conflict','omissions','mappings'])
def test_incomplete_or_conflicting_source_stays_unknown(config,issue):
    r=result(True)
    r['results'][0][issue]={'conflict':True,'omissions':['mirror unclear'],'mappings':[]}[issue]
    assert pilot.validate(r,data(True))[0]['decision']=='UNKNOWN'

def test_blind_input_forbids_previous_reviews_and_wrong_hash_before_dispatch(config):
    for key in ['criticA','provider','canonicalGrade','optimizerRecommendation']:
        r=request();r['input']['packets'][0][key]='hidden'
        with pytest.raises(ValueError):pilot.execute(r,lambda *args:pytest.fail('No dispatch'))
    r=request();r['input']['packets'][0]['promptSha256']='wrong'
    with pytest.raises(ValueError):pilot.execute(r,lambda *args:pytest.fail('No dispatch'))

@pytest.mark.parametrize('field,value',[('authorizePaidInference',False),('automaticRetries',True),('model','fallback-model'),('maxCostUsd',.000001),('maxOutputTokens',5000)])
def test_authorization_failures_prevent_provider_construction(config,field,value):
    r=request();r['authorization'][field]=value
    with pytest.raises(ValueError):pilot.execute(r,lambda *args:pytest.fail('No provider allowed'))

def test_rejected_response_is_retained_without_retry(config):
    class Bad(Fake):
        dispatches=0
        def complete(self,*args,**kwargs):
            Bad.dispatches+=1;super().complete(*args,**kwargs);self.last_raw_response='{broken';return self.last_raw_response
    out=pilot.execute(request(),Bad)
    assert out['executionStatus']=='FAILED_OR_AMBIGUOUS' and out['rawResponse']=='{broken' and Bad.dispatches==1

def test_direct_paid_endpoint_fails_closed(monkeypatch):
    monkeypatch.delenv('CPQ_PILOT_REAL_ENABLED',raising=False)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.workflow.api import router
    app=FastAPI();app.include_router(router)
    assert TestClient(app).post('/api/v1/workflow/cpq-pilot/execute',json=request()).status_code==403
