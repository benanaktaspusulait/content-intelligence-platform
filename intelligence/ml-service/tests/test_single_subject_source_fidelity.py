"""TEST_FIXTURE only: exact saved inputs, mocked transport, no real fidelity judgments."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from app.workflow import owner_machine_pilot as m
from test_source_fidelity_output_budget import sdk_response

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / 'intelligence/docs/cpq-single-subject-source-fidelity-evidence'
BATCH = ROOT / 'intelligence/docs/cpq-source-fidelity-output-budget-evidence/representative-unknown-response.MOCK.json'

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('POMPOM_DATA_ROOT',str(ROOT/'intelligence/data'))
    monkeypatch.setenv('OPENAI_API_KEY','TEST_FIXTURE_NOT_A_KEY')
    monkeypatch.delenv('CPQ_SOURCE_FIDELITY_REASONING_EFFORT',raising=False)
    monkeypatch.setenv('CPQ_PILOT_REAL_ENABLED','false')

def data(q='Q04'):
    return json.loads((EV/f'{q}-prototype-input.json').read_text())

def fixture(d):
    p=d['packets'][0]
    old=next(r for r in json.loads(BATCH.read_text())['results'] if r['neutralId']==p['neutralId'])
    result={**old,'sourceBinding':p['sourceBinding'],'rationale':'TEST_FIXTURE: complete source coverage, not a real semantic assessment.','uncertainty':'TEST_FIXTURE: no real model or visual evidence.'}
    mappings=[]
    # Exhaustive literal source spans; judgments intentionally UNKNOWN, never fabricated PASS.
    for event in p['requiredEvents']:
        quote=p['approvedStory'][event['sourceStart']:event['sourceEnd']]
        related=max((x for x in old['mappings'] if quote in x['sourceQuote'] or x['sourceQuote'] in quote),key=lambda x:min(len(quote),len(x['sourceQuote'])),default=old['mappings'][0])
        mappings.append({**related,'sourceQuote':quote,'eventId':event['eventId'],'consistency':'UNKNOWN'})
    represented={x['anchor'] for x in mappings}
    for mapping in old['mappings']:
        if mapping['anchor'] in represented:continue
        represented.add(mapping['anchor'])
        start=p['approvedStory'].find(mapping['sourceQuote'])
        event=next(e for e in p['requiredEvents'] if e['sourceStart']<=start<e['sourceEnd'])
        end=min(start+len(mapping['sourceQuote']),event['sourceEnd'])
        mappings.append({**mapping,'sourceQuote':p['approvedStory'][start:end],'eventId':event['eventId'],'consistency':'UNKNOWN'})
    for beat in p['changedBeats']:
        mapping=next(x for x in mappings if x['beatId']==beat['beatId'])
        mappings.append({**mapping,'promptQuote':beat['newExecution']})
    result['mappings']=mappings
    return {'results':[result]}

def body(d):
    return {'requestId':'TEST_FIXTURE_SINGLE_REQUEST','input':d,'authorization':{'authorizePaidInference':True,'automaticRetries':False,'profileId':'openai-escalation','provider':'openai','model':'gpt-6.1-sol','reasoningEffort':'low','maxOutputTokens':4000,'maxCostUsd':.30,'subjectPromptSha256':d['packets'][0]['promptSha256']}}

def run(d,raw=None,finish='stop',reasoning=100):
    if raw is None:raw=json.dumps(fixture(d),ensure_ascii=False,separators=(',',':'))
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=sdk_response(raw,finish,{'prompt_tokens':2000,'completion_tokens':4000 if finish=='length' else 1800,'completion_tokens_details':{'reasoning_tokens':reasoning}})
        out=m.execute(body(d));sdk.return_value.chat.completions.create.assert_called_once()
        args=sdk.return_value.chat.completions.create.call_args.kwargs
        assert sdk.call_args.kwargs['max_retries']==0 and args['reasoning_effort']=='low' and args['max_completion_tokens']==4000
        assert json.loads(args['messages'][1]['content'])==d
        assert args['response_format']['json_schema']['strict']
        return out,args

@pytest.mark.parametrize('q',['Q04','Q01','Q02','Q03'])
def test_exact_one_subject_unknown_is_complete_evidence(q):
    d=data(q);p=d['packets'][0]
    assert len(d['packets'])==1 and 'originalPrompt' not in p
    assert p['requiredEvents']==m.source_events(p['approvedStory'])
    assert hashlib.sha256(p['prompt'].encode()).hexdigest()==p['promptSha256']
    out,_=run(d)
    assert out['executionStatus']=='COMPLETED' and out['results'][0]['decision']=='UNKNOWN'
    assert out['evidenceType']=='MACHINE_REVIEW'
    assert {x['anchor'] for x in out['results'][0]['mappings']}==set(m.ANCHORS)
    assert out['results'][0]['sourceBinding']==p['sourceBinding']
    assert all(k not in out for k in ['grade','renderAuthorized','promptVersion'])

@pytest.mark.parametrize('defect',['missing_anchor','missing_event','changed_beat','invented_quote','invented_event','wrong_id','wrong_hash','unsupported_pass','empty_pass_quote'])
def test_invalid_semantic_contract_is_rejected(defect):
    d=data('Q01');f=fixture(d);r=f['results'][0]
    if defect=='missing_anchor':r['mappings']=[x for x in r['mappings'] if x['anchor']!='PHYSICAL_RULE']
    if defect=='missing_event':r['mappings']=[x for x in r['mappings'] if x['eventId']!='event_01']
    if defect=='changed_beat':
        for x in r['mappings']:x['beatId']='beat_99'
    if defect=='invented_quote':r['mappings'][0]['sourceQuote']='invented story quotation'
    if defect=='invented_event':r['mappings'][0]['eventId']='new_event'
    if defect=='wrong_id':r['neutralId']='another_subject'
    if defect=='wrong_hash':r['sourceBinding']=dict(r['sourceBinding'],promptSha256='0'*64)
    if defect=='unsupported_pass':r['decision']='PASS'
    if defect=='empty_pass_quote':r['mappings'][0].update(consistency='PASS',promptQuote='')
    out,_=run(d,json.dumps(f));assert out['executionStatus']=='FAILED_OR_AMBIGUOUS' and not out['results']

@pytest.mark.parametrize('defect',['story','prompt','settings','event_spans','scope','changed_execution'])
def test_bound_inputs_rejected_before_transport(defect):
    d=data('Q01');p=d['packets'][0]
    if defect=='story':p['approvedStory']+=' Unauthorized ending.'
    if defect=='prompt':p['prompt']+=' new story'
    if defect=='settings':p['productionSettings']['durationSeconds']=99
    if defect=='event_spans':p['requiredEvents'].pop()
    if defect=='scope':d['packets'].append(copy.deepcopy(p))
    if defect=='changed_execution':p['changedBeats'][0]['newExecution']='invented instruction'
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        with pytest.raises(ValueError):m.execute(body(d))
        sdk.assert_not_called()

@pytest.mark.parametrize('raw,finish,reasoning,category',[('', 'stop',0,'EMPTY_VISIBLE_OUTPUT'),('', 'length',4000,'REASONING_BUDGET_EXHAUSTED'),('{','stop',100,'PROVIDER_OR_RESPONSE_CONTRACT_FAILED'),('{','length',3900,'VISIBLE_OUTPUT_TRUNCATED')])
def test_single_transport_failures_preserve_accounting_without_retry(raw,finish,reasoning,category):
    out,_=run(data(),raw,finish,reasoning)
    assert out['executionStatus']=='FAILED_OR_AMBIGUOUS' and out['failureCategory']==category and out['rawResponse']==raw
    assert not out['results'] and out['usageAccountingStatus']=='COMPLETE'


def test_missing_evidence_is_unknown_not_invented_quote():
    d=data();f=fixture(d);f['results'][0]['mappings'][0]['promptQuote']=''
    assert m.validate(f,d)[0]['decision']=='UNKNOWN'


def test_proxy_budget_and_save_final_request_measurements():
    tok=pytest.importorskip('tiktoken').get_encoding('o200k_base')
    from test_source_fidelity_output_budget import execute_mock, response_fixture
    _,batch_args=execute_mock(sdk_response(json.dumps(response_fixture(),ensure_ascii=False,separators=(',',':'))))
    batch_serialized=json.dumps(batch_args,ensure_ascii=False,separators=(',',':'))
    batch_json=json.dumps(response_fixture(),ensure_ascii=False,separators=(',',':'))
    batch={'serializedRequestBytes':len(batch_serialized.encode()),'estimatedRequestTokens':len(tok.encode(batch_serialized)),'representativeJsonBytes':len(batch_json.encode()),'representativeVisibleTokens':len(tok.encode(batch_json))}
    metrics=[]
    for q in ['Q04','Q01','Q02','Q03']:
        d=data(q);f=fixture(d);raw=json.dumps(f,ensure_ascii=False,separators=(',',':'));out,args=run(d,raw)
        assert out['executionStatus']=='COMPLETED'
        serialized=json.dumps(args,ensure_ascii=False,separators=(',',':'))
        record={'neutralId':q,'serializedRequestBytes':len(serialized.encode()),'estimatedRequestTokens':len(tok.encode(serialized)),'representativeJsonBytes':len(raw.encode()),'representativeVisibleTokens':len(tok.encode(raw)),'fixtureLabel':'TEST_FIXTURE'}
        assert record['representativeVisibleTokens']<2500 and record['serializedRequestBytes']<14000
        (EV/f'{q}-single-subject-response.TEST_FIXTURE.json').write_text(json.dumps(f,ensure_ascii=False,indent=2)+'\n')
        (EV/f'{q}-single-subject-provider-request.TEST_FIXTURE.json').write_text(json.dumps(args,ensure_ascii=False,indent=2)+'\n')
        metrics.append(record)
    (EV/'final-request-size-comparison.json').write_text(json.dumps({'tokenizer':'o200k_base proxy, not actual model tokenizer','batch':batch,'subjects':metrics},indent=2)+'\n')
