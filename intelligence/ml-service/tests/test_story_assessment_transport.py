"""Real SDK, exclusively mocked HTTP. No network, provider spend or production data."""
import json
from pathlib import Path
from unittest.mock import patch

import httpx
import openai
import pytest
from app.workflow import story_assessment as a
from app.llm.openai_provider import OpenAIProvider
from test_story_assessment import configuration, grant
from story_assessment_cases import case_response


@pytest.mark.parametrize('mode,classification,cause,status',[
 ('sdk-timeout','SDK_TIMEOUT',None,None),
 ('connect-timeout','SDK_TIMEOUT','ConnectTimeout',None),
 ('read-timeout','SDK_TIMEOUT','ReadTimeout',None),
 ('write-timeout','SDK_TIMEOUT','WriteTimeout',None),
 ('pool-timeout','SDK_TIMEOUT','PoolTimeout',None),
 ('reset','NETWORK_CONNECTION_FAILURE','ReadError',None),
 ('dns','NETWORK_CONNECTION_FAILURE','ConnectError',None),
 ('429','HTTP_STATUS_ERROR',None,429),('503','HTTP_STATUS_ERROR',None,503),
 ('400','HTTP_STATUS_ERROR',None,400),
 ('positive',None,None,None),('missing-usage','MISSING_USAGE_AFTER_RESPONSE',None,None),
 ('invalid-usage','ACCOUNTING_VALIDATION_FAILED',None,None),
 ('refusal','PROVIDER_REFUSAL',None,None),('incomplete','INCOMPLETE_RESPONSE',None,None)])
def test_sdk_primary_error_accounting_correlation_and_nonretry(monkeypatch,mode,classification,cause,status):
 text,c=grant();calls=[];captured=[]
 monkeypatch.setenv('OPENAI_API_KEY','offline-not-a-credential')
 def transport(request):
  assert request.extensions['timeout']=={'connect':5,'pool':5,'write':10,'read':60}
  assert json.loads(request.content)==a.request_body(text,c)
  calls.append(request.headers['X-Client-Request-Id'])
  marker=Path(capture_root)/'workflow/story-assessment-receipts'/(c['storyRequestId']+'-reserved.json')
  assert json.loads(marker.read_text())['clientRequestId']==calls[-1]==c['storyRequestId']
  if mode=='sdk-timeout':raise openai.APITimeoutError(request=request)
  if mode in ('connect-timeout','read-timeout','write-timeout','pool-timeout','reset','dns'):
   typ={'connect-timeout':httpx.ConnectTimeout,'read-timeout':httpx.ReadTimeout,'write-timeout':httpx.WriteTimeout,'pool-timeout':httpx.PoolTimeout,'reset':httpx.ReadError,'dns':httpx.ConnectError}[mode]
   raise typ('private prompt and Bearer sk-secret-must-not-appear',request=request)
  if status:return httpx.Response(status,headers={'x-request-id':'req-offline-'+mode},json={'error':{'message':'private prompt sk-secret-must-not-appear','type':'offline_failure','code':'offline'}})
  body=json.loads(request.content);message={'role':'assistant','content':case_response(json.loads(body['messages'][1]['content']),'positive'),'refusal':None}
  if mode=='refusal':message.update(content=None,refusal='Offline refusal')
  usage={'prompt_tokens':100,'completion_tokens':200,'total_tokens':300}
  if mode=='invalid-usage':usage['prompt_tokens']=-1
  result={'id':'MOCK_ONLY_'+mode,'object':'chat.completion','created':0,'model':body['model'],'choices':[{'index':0,'message':message,'finish_reason':'length' if mode=='incomplete' else 'stop'}]}
  if mode!='missing-usage':result['usage']=usage
  return httpx.Response(200,headers={'x-request-id':'req-offline-success'},json=result)
 def client(**kw):
  assert kw['max_retries']==0 and kw['timeout'].as_dict()=={'connect':5,'pool':5,'write':10,'read':60}
  sdk=openai.OpenAI(**kw,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
  captured.append(sdk);return sdk
 import os
 capture_root=os.environ['POMPOM_DATA_ROOT']
 with patch('app.llm.openai_provider.OpenAI',side_effect=client):r=a.execute(text,c,.1)
 assert len(calls)==1 and r['clientRequestId']==c['storyRequestId']
 assert r['diagnostics']['elapsedSeconds']>=0
 if mode=='positive':
  assert r['processingStatus']=='INDEPENDENT_REVIEW_COMPLETED'
  assert r['result']==json.loads(r['rawProviderResponse']) and r['resolvedEvidence']
  assert r['actualCostUsd']==pytest.approx(.000135)
  assert r['providerResponseMetadata']['httpRequestId']=='req-offline-success'
 else:
  assert r['error']['failureClass']==classification
  assert 'sk-secret' not in json.dumps(r['error']) and 'private prompt' not in json.dumps(r['error'])
  if classification in ('SDK_TIMEOUT','NETWORK_CONNECTION_FAILURE','HTTP_STATUS_ERROR'):
   assert r['processingStatus']=='DISPATCH_UNCERTAIN' and r['billingStatus']=='USAGE_UNKNOWN'
   assert r['actualCostUsd'] is None and r['usage'] is None and not r['responseReceived']
   assert r['error']['category']!='ValueError' and 'omitted verifiable' in r['accountingError']['detail']
   snap=json.loads(Path(r['primaryFailureFile']).read_text());assert snap['primaryError']==r['error']
   assert not snap['completeSdkResponseReceived'] and not snap['usageReceived']
   if cause:assert r['error']['causeType']==cause
   if status:assert r['error']['httpStatus']==status and r['error']['providerHttpRequestId']=='req-offline-'+mode
  if mode in ('missing-usage','invalid-usage'):
   assert r['responseReceived'] and r['diagnostics']['completeSdkResponseReceived']
   assert r['actualCostUsd'] is None and r['billingStatus']=='USAGE_UNKNOWN'
  if mode in ('refusal','incomplete'):
   assert r['actualCostUsd']==pytest.approx(.000135) and r['responseReceived']
 assert r['retrySafe'] is False and r['assessmentOnly'] is True
 with patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('Duplicate dispatch forbidden')):
  with pytest.raises(FileExistsError):a.execute(text,c,.1)
 assert len(calls)==1
 for sdk in captured:sdk.close()


@pytest.mark.parametrize('identity',['','é','a'*513,'bad\r\nheader'])
def test_invalid_client_header_never_sends(monkeypatch,identity):
 monkeypatch.setenv('OPENAI_API_KEY','offline-not-a-credential')
 with patch('app.llm.openai_provider.OpenAI') as sdk:
  provider=OpenAIProvider();provider.client_request_id=identity
  with pytest.raises(ValueError,match='Client request ID'):provider.complete('offline')
  sdk.return_value.chat.completions.create.assert_not_called()


def test_unknown_failure_stays_unknown_and_never_leaks_message():
 text,c=grant()
 class UnknownAdapter:
  def complete(self,*args,**kwargs):
   raise RuntimeError('private prompt Bearer sk-secret-not-for-logs')
 with patch('app.llm.openai_provider.OpenAIProvider',return_value=UnknownAdapter()):r=a.execute(text,c,.1)
 assert r['error']['category']=='RuntimeError' and r['error']['failureClass']=='UNKNOWN_TRANSPORT_FAILURE'
 assert r['accountingError']['category']=='ValueError' and r['actualCostUsd'] is None
 assert 'sk-secret' not in json.dumps(r) and 'private prompt' not in json.dumps(r)
 assert json.loads(Path(r['primaryFailureFile']).read_text())['primaryError']==r['error']


def test_unrelated_dispatches_have_different_ids(monkeypatch):
 ids=[]
 def transport(request):
  ids.append(request.headers['X-Client-Request-Id'])
  raise httpx.ReadTimeout('Offline',request=request)
 def client(**kw):return openai.OpenAI(**kw,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
 monkeypatch.setenv('OPENAI_API_KEY','offline-not-a-credential')
 with patch('app.llm.openai_provider.OpenAI',side_effect=client):
  for _ in range(2):
   text,c=grant();r=a.execute(text,c,.1);assert r['clientRequestId']==ids[-1]
 assert len(ids)==len(set(ids))==2


def test_uncertain_historical_grant_cannot_authorize_changed_diagnostics():
 from story_experiment_fixture import assessment_inputs
 text,c=assessment_inputs()
 docs=Path(__file__).resolve().parents[2]/'docs'
 old=json.loads((docs/'real-evidence-reference-story-review-evidence/actual-owner-spending-grant.json').read_text())
 c.update(assessmentSpendingAuthorized=True,assessmentDispatch=old['operations'][0],storyRequestId=old['idempotencyKey'])
 with patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('Old grant cannot dispatch')):
  with pytest.raises(ValueError,match='Fresh exact assessment spending grant'):a.execute(text,c,.1)


def test_general_openai_adapter_keeps_its_original_timeout(monkeypatch):
 monkeypatch.setenv('OPENAI_API_KEY','offline-not-a-credential')
 monkeypatch.setenv('OPENAI_REQUEST_TIMEOUT_SECONDS','20')
 seen=[]
 def transport(request):
  seen.append(request.extensions['timeout'])
  return httpx.Response(200,json={'id':'MOCK_GENERAL','model':'gpt-4o','choices':[{'index':0,'message':{'role':'assistant','content':'offline'},'finish_reason':'stop'}]})
 def client(**kw):
  assert kw['timeout']==20 and kw['max_retries']==0
  return openai.OpenAI(**kw,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
 with patch('app.llm.openai_provider.OpenAI',side_effect=client):
  adapter=OpenAIProvider();assert adapter.complete('offline')=='offline';adapter.client.close()
 assert seen==[{'connect':20,'pool':20,'write':20,'read':20}]


def test_changed_execution_policy_leaves_review_body_and_catalog_unchanged():
 text,c=grant();docs=Path(__file__).resolve().parents[2]/'docs'
 old=json.loads((docs/'STORY_REVIEW_EVIDENCE_REFERENCE_REVIEW_MANIFEST.json').read_text())
 assert a.request_body(text,c)==old['providerRequest']
 current=a.preview(text,c)
 assert current['evidenceCatalogSha256']==old['operation']['evidenceCatalogSha256']
 assert current['timeoutPolicy']==c['assessmentScope']['transportPolicy']
 assert current['serializedRequestSha256']==old['operation']['serializedRequestSha256']
 assert current['implementationSha256']!=old['operation']['implementationSha256']
 c['assessmentScope']['transportPolicy']['backendHttpSeconds']=25
 with pytest.raises(ValueError,match='timeout policy'):a.preview(text,c)
