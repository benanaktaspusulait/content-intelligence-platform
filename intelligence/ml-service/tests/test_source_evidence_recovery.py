"""Offline contract tests using retained real output; never a provider execution."""
import copy, hashlib, json
from pathlib import Path
from unittest.mock import patch
import pytest
from app.workflow import owner_machine_pilot as m
ROOT=Path(__file__).resolve().parents[3]
SAVED=ROOT/'intelligence/docs/cpq-single-subject-delivery-evidence/real-original-only-durable-result.json'
def body():
    row=json.loads(SAVED.read_text()); response=row['response']
    return dict(input=row['input'],savedResponse=response,originalAuthorization=row['authorization_payload'],citationContractVersion=m.SOURCE_CITATION_CONTRACT,inputSha256=row['input_sha256'],requestId=row['request_id'],rawResponseSha256=hashlib.sha256(response['rawResponse'].encode()).hexdigest(),providerResponseId=response['providerMetadata']['requestId'])
@pytest.fixture(autouse=True)
def no_provider():
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        yield
        sdk.assert_not_called()
def test_exact_saved_output_offline_revalidation_is_immutable():
    b=body();before=copy.deepcopy(b); result=m.revalidate_saved_source(b)
    assert b==before
    assert result['results'][0]['decision']=='FAIL'
    for key in ('omissions','additions','uncertainty','productionRisks','rationale'):
        assert result['results'][0][key]==json.loads(b['savedResponse']['rawResponse'])['results'][0][key]
    assert result['newInference'] is False and result['newInferenceCostUsd']==0
    assert result['correctedMappings']==[dict(mappingIndex=11,eventIds=['event_06','event_07','event_08'],anchorEventId='event_07')]
@pytest.mark.parametrize('field,value',[('rawResponseSha256','f'*64),('inputSha256','f'*64),('providerResponseId','wrong'),('citationContractVersion','wrong')])
def test_wrong_proofs(field,value):
    b=body();b[field]=value
    with pytest.raises(ValueError):m.revalidate_saved_source(b)
@pytest.mark.parametrize('field,value',[('rawResponse',''),('rawResponse','{"results":['),('failureCategory','REASONING_BUDGET_EXHAUSTED'),('usageAccountingStatus','UNKNOWN'),('costUsd',99),('executionStatus','COMPLETED')])
def test_ineligible_retained_response(field,value):
    b=body();b['savedResponse'][field]=value;b['rawResponseSha256']=hashlib.sha256(b['savedResponse']['rawResponse'].encode()).hexdigest()
    with pytest.raises((ValueError,KeyError)):m.revalidate_saved_source(b)
@pytest.mark.parametrize('field,value',[('finishReason','length'),('model','wrong'),('apiStatus','UNKNOWN')])
def test_incomplete_provider(field,value):
    b=body();b['savedResponse']['providerMetadata'][field]=value
    with pytest.raises(ValueError):m.revalidate_saved_source(b)
@pytest.mark.parametrize('field',['promptSha256','approvedStorySha256','productionSettingsSha256'])
def test_source_bindings(field):
    b=body();b['input']['packets'][0]['sourceBinding'][field]='f'*64
    b['inputSha256']=hashlib.sha256(json.dumps(b['input'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    with pytest.raises(ValueError):m.revalidate_saved_source(b)
def test_first_two_historical_requests_are_not_recoverable():
    for file in ['cpq-first-real-ai-experiment-evidence/source-fidelity-durable-request.json','cpq-source-fidelity-completed-experiment-evidence/source-fidelity-durable-request.json']:
        row=json.loads((ROOT/'intelligence/docs'/file).read_text());b=body();b.update(input=row['input'],savedResponse=row['response'],originalAuthorization=row['authorization_payload'],requestId=row['request_id'],inputSha256=row['input_sha256'])
        with pytest.raises(ValueError):m.revalidate_saved_source(b)
def test_signed_offline_route_with_paid_switch_disabled(monkeypatch):
    import hmac
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.workflow.api import router
    app=FastAPI();app.include_router(router);client=TestClient(app);token='offline-test-only-'*3
    monkeypatch.setenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN',token);monkeypatch.setenv('CPQ_PILOT_REAL_ENABLED','false')
    raw=json.dumps(body()).encode();path='/api/v1/workflow/cpq-pilot/revalidate-source'
    assert client.post(path,content=raw).status_code==403
    response=client.post(path,content=raw,headers={'X-CPQ-Pilot-Dispatch':hmac.new(token.encode(),raw,hashlib.sha256).hexdigest()})
    assert response.status_code==200,response.text
    assert response.json()['results'][0]['decision']=='FAIL'
@pytest.mark.parametrize('change',['missing_anchor','missing_span','noncontiguous','no_corrected_defect'])
def test_recovery_requires_full_evidence_and_specific_corrected_failure(change):
    b=body();raw=json.loads(b['savedResponse']['rawResponse']);result=raw['results'][0];packet=b['input']['packets'][0]
    if change=='missing_anchor':
        result['mappings']=[m for m in result['mappings'] if m['anchor']!='PHYSICAL_RULE']
    elif change=='missing_span':
        result['mappings']=[m for m in result['mappings'] if m['eventId']!='event_01']
    elif change=='noncontiguous':
        result['mappings'][11]['sourceQuote']=result['mappings'][11]['sourceQuote'].replace('Notlar o kadar çoğalır ki Mimi boğulacak gibi olur. ','')
    else:result['mappings'].pop(11)
    b['savedResponse']['rawResponse']=json.dumps(raw,ensure_ascii=False);b['rawResponseSha256']=hashlib.sha256(b['savedResponse']['rawResponse'].encode()).hexdigest()
    with pytest.raises(ValueError):m.revalidate_saved_source(b)
