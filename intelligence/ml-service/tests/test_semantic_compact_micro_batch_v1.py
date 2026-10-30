"""Zero external calls: fixed policy, partial failure, provenance and offline reporting."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.workflow import semantic_compact_micro_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[3]
DOCS=ROOT/'intelligence/docs'
PRIOR=json.loads((DOCS/'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
ACCEPTED=json.loads((DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
REFERENCE=DOCS/'semantic-low-reasoning-full-contract-probe-1-run-001/inspection.json'
PROFILE=dict(provider='openai',model='gpt-6.1-sol',baseUrl=PRIOR['baseUrl'],responseMode='json_schema',tokenParameter='max_completion_tokens',reasoningEffort='high',temperatureSupported=False,maxOutputTokens=128000)
TESTS=dict(noNewFailures=True,schemaIntegrityPassed=True)


def test_three_planned_requests_exact_accepted_profile():
    p=batch.plan(PROFILE,PRIOR,ACCEPTED)
    assert p['requestIds']==['micro-a','micro-b','micro-c']
    assert p['maximumLiveRequests']==3 and p['candidateCountPerRequest']==1
    assert p['request']==ACCEPTED
    assert p['request']['arguments']['reasoning_effort']=='low'
    assert p['request']['arguments']['max_completion_tokens']==8192
    assert p['retries']==p['fallbacks']==p['DeepSeekCalls']==p['renders']==0
    changed=deepcopy(ACCEPTED);changed['arguments']['reasoning_effort']='high'
    with pytest.raises(ValueError):batch.plan(PROFILE,PRIOR,changed)


@pytest.mark.parametrize('failure',[None,'micro-a','micro-b','micro-c'])
def test_fixed_cap_partial_failure_no_replacement_retry_fallback_and_reference_reuse(tmp_path,failure):
    calls=[];before=REFERENCE.read_bytes()
    def fake(path,config,prior,**kwargs):
        calls.append((path.name,batch.low.plan(config,prior)['newRequest']))
        if path.name==failure:raise RuntimeError('mock-only planned failure')
        path.mkdir();(path/'inspection.json').write_bytes(before)
        return dict(status='COMPLETED',SDKRequestsForwarded=1,HTTPRequestsObserved=1)
    dest=tmp_path/'run'
    result=batch.execute(dest,PROFILE,PRIOR,ACCEPTED,REFERENCE,
                         authorization={'mock':True},tests=TESTS,executor=fake)
    assert [c[0] for c in calls]==list(batch.REQUEST_IDS)
    assert all(c[1]==ACCEPTED for c in calls)
    assert REFERENCE.read_bytes()==before
    assert result['sampleSize']==(3 if failure else 4)
    assert result['referenceRegenerated'] is False
    ids=[r['candidateId'] for r in result['candidates']]
    assert len(ids)==len(set(ids))
    assert len(list(dest.glob('*-provenance.json')))==3
    proof=json.loads((dest/'execution-proof.json').read_text())
    assert proof['consumedSlots']==proof['maximumLiveRequests']==3
    assert not proof['fourthRequest'] and proof['replacementRequests']==proof['retries']==proof['fallbacks']==0
    with pytest.raises(FileExistsError):
        batch.execute(dest,PROFILE,PRIOR,ACCEPTED,REFERENCE,
                      authorization={'mock':True},tests=TESTS,executor=fake)
    assert len(calls)==3


def test_combined_analysis_and_existing_thresholds():
    i=json.loads(REFERENCE.read_text())
    r=batch.combine({name:deepcopy(i) for name in ('REFERENCE-0',*batch.REQUEST_IDS)})
    assert r['sampleSize']==4 and r['opening']['acceptedFloor']==60
    assert r['opening']['scores']==[35]*4
    assert r['opening']['mean']==r['opening']['median']==35
    assert r['opening']['signal']=='OPENING_WEAKNESS_SIGNAL'
    assert r['SFE']['scores']==[84]*4 and r['SFE']['mean']==84
    assert r['productionAdmissibleCount']==0 and r['providerCallsDuringAnalysis']==0


@pytest.mark.parametrize('case,expected',[
    ('production','PRODUCTION_ADMISSIBLE'),('ranking','RANKING_ELIGIBLE'),
    ('pass','SFE_PASS'),('one','SFE_GE75_ONE_BLOCKER'),('admitted','ADMITTED_ONE_BLOCKER'),('none',None)])
def test_human_review_set_construction(case,expected):
    r=deepcopy(json.loads(REFERENCE.read_text())['pipeline']['allRawIdeas'][0]['record'])
    r['productionAdmissible']=False;r['validation']['eligibility']='INELIGIBLE'
    r['validation']['shortFormEngine']['status']='REVISION_REQUIRED'
    r['validation']['shortFormScore']=74;r['admission']['admitted']=False;r['productionBlockers']=['A','B']
    if case=='production':r['productionAdmissible']=True
    if case=='ranking':r['validation']['eligibility']='ELIGIBLE'
    if case=='pass':r['validation']['shortFormEngine']['status']='PASS'
    if case=='one':r['productionBlockers']=['A'];r['validation']['shortFormScore']=75
    if case=='admitted':r['productionBlockers']=['A'];r['admission']['admitted']=True
    reasons=batch.review_reasons(r)
    assert (expected in reasons) if expected else not reasons
