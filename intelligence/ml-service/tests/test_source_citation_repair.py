"""OFFLINE_REVALIDATION_ONLY: exact preserved real output; never persist or call a provider."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from app.workflow import owner_machine_pilot as m

ROOT=Path(__file__).resolve().parents[3]
SAVED=ROOT/'intelligence/docs/cpq-single-subject-delivery-evidence/real-original-only-durable-result.json'


def saved():
    row=json.loads(SAVED.read_text());data=row['input'];raw=json.loads(row['response']['rawResponse'])
    p=data['packets'][0]
    assert hashlib.sha256(p['prompt'].encode()).hexdigest()==p['promptSha256']=='0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98'
    assert hashlib.sha256(p['approvedStory'].encode()).hexdigest()==p['sourceBinding']['approvedStorySha256']=='df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b'
    return row,data,raw

@pytest.fixture(autouse=True)
def no_provider():
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        yield
        sdk.assert_not_called()


def test_exact_immutable_real_fail_is_structurally_admissible_offline_only():
    original=SAVED.read_bytes();row,data,raw=saved();before=copy.deepcopy(raw)
    result=m.validate(copy.deepcopy(raw),data)[0]
    assert result['decision']==before['results'][0]['decision']=='FAIL'
    assert result['validationNotice'].startswith('REVIEW_REQUIRED')
    assert len(result['mappings'])==14 and {x['anchor'] for x in result['mappings']}==set(m.ANCHORS)
    assert row['state']=='FAILED_OR_AMBIGUOUS' and row['response']['results']==[]
    assert m.citation_event_range(data['packets'][0],raw['results'][0]['mappings'][11])==['event_06','event_07','event_08']
    assert raw==before and SAVED.read_bytes()==original

@pytest.mark.parametrize('index',range(14))
def test_all_actual_citations_and_literal_source_and_prompt_evidence(index):
    _,data,raw=saved();p=data['packets'][0];mapping=raw['results'][0]['mappings'][index]
    ids=m.citation_event_range(p,mapping)
    assert mapping['eventId'] in ids and 1<=len(ids)<=3
    assert mapping['sourceQuote'] in p['approvedStory'] and mapping['promptQuote'] in p['prompt']
    assert len(ids)==(3 if index==11 else 1)

@pytest.mark.parametrize('first,last,anchor',[(0,1,0),(4,6,5),(5,7,5),(5,7,6),(5,7,7)])
def test_explicit_exact_two_or_three_sentence_boundaries_with_anchor_inside(first,last,anchor):
    _,data,raw=saved();p=data['packets'][0];events=p['requiredEvents'];mapping=raw['results'][0]['mappings'][11]
    mapping.update(eventId=events[anchor]['eventId'],sourceQuote=p['approvedStory'][events[first]['sourceStart']:events[last]['sourceEnd']])
    assert m.citation_event_range(p,mapping)==[e['eventId'] for e in events[first:last+1]]

@pytest.mark.parametrize('defect',['noncontiguous','reordered','fabricated','wrong_anchor','wrong_anchor_kind','unknown_event','whole_story','four_events','partial_boundary','normalized_whitespace'])
def test_range_constraints_are_not_general_quote_relaxation(defect):
    _,data,raw=saved();p=data['packets'][0];events=p['requiredEvents'];mapping=raw['results'][0]['mappings'][11]
    spans=[p['approvedStory'][e['sourceStart']:e['sourceEnd']] for e in events]
    if defect=='noncontiguous':mapping['sourceQuote']=spans[5]+' '+spans[7]
    if defect=='reordered':mapping['sourceQuote']=spans[7]+' '+spans[6]+' '+spans[5]
    if defect=='fabricated':mapping['sourceQuote']+=' This never happened.'
    if defect=='wrong_anchor':mapping['eventId']='event_05'
    if defect=='wrong_anchor_kind':mapping['anchor']='APPROVED_EVENTS'
    if defect=='unknown_event':mapping['eventId']='event_99'
    if defect=='whole_story':mapping['sourceQuote']=p['approvedStory']
    if defect=='four_events':mapping['sourceQuote']=p['approvedStory'][events[4]['sourceStart']:events[7]['sourceEnd']]
    if defect=='partial_boundary':mapping['sourceQuote']=mapping['sourceQuote'][1:]
    if defect=='normalized_whitespace':mapping['sourceQuote']=mapping['sourceQuote'].replace('. ','.  ',1)
    with pytest.raises(ValueError):m.validate(raw,data)

@pytest.mark.parametrize('defect',['missing_anchor','missing_span','range_only_coverage','unsupported_pass'])
def test_complete_coverage_and_no_unsupported_pass_remain_mandatory(defect):
    _,data,raw=saved();r=raw['results'][0]
    if defect=='missing_anchor':r['mappings']=[x for x in r['mappings'] if x['anchor']!='PHYSICAL_RULE']
    if defect=='missing_span':r['mappings']=[x for x in r['mappings'] if not(x['anchor']=='APPROVED_EVENTS' and x['eventId']=='event_07')]
    if defect=='range_only_coverage':r['mappings']=[x for x in r['mappings'] if x['anchor']!='APPROVED_EVENTS']
    if defect=='unsupported_pass':r['decision']='PASS'
    with pytest.raises(ValueError):m.validate(raw,data)

@pytest.mark.parametrize('decision',['FAIL','UNKNOWN'])
def test_complete_non_pass_is_evidence_not_transport_failure(decision):
    _,data,raw=saved();raw['results'][0]['decision']=decision
    assert m.validate(raw,data)[0]['decision']==decision


def test_legacy_batch_contract_keeps_previous_interpretation():
    row=json.loads((ROOT/'intelligence/docs/cpq-first-real-ai-experiment-evidence/source-fidelity-durable-request.json').read_text())
    fixture=json.loads((ROOT/'intelligence/docs/cpq-source-fidelity-output-budget-evidence/representative-unknown-response.MOCK.json').read_text())
    assert len(m.validate(fixture,row['input']))==4
