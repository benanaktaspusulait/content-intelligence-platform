"""Untouched real-response regression and independent materiality acceptance.

No original provider output is repaired, aliased, compiled as a success or sent
back to a real provider. Positive examples are controlled structured mock plans.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from app.workflow.creative_reconstruction import (AUTHORING_VERSION, AuthoredResponseV2, compile_reconstruction,
    request_payload, response_format, generation_system, perform_reconstruction, response_model)
from app.workflow.model_authored_execution import LEGACY_AUTHORING_VERSION, review_authored, temporal_evidence
from test_creative_reconstruction_v2 import MockProvider, response, canonical_review
from test_model_authored_execution import inputs, contact, progression

REAL=Path(__file__).parent/'fixtures/real-model-authored-failure-2026-10-15.json'
REAL_SHA='0783b28b78e18bcdfa3c2ac14aec5266e91a15e89b65aaedea489c09c7ab95e0'


def saved_response():
    assert hashlib.sha256(REAL.read_bytes()).hexdigest()==REAL_SHA
    return json.loads(REAL.read_text())


def reviewed(raw=None):
    f=inputs();value=saved_response() if raw is None else raw
    payload=request_payload(f['text'],f['context']);parsed=AuthoredResponseV2.model_validate(value)
    result=[]
    for proposal in parsed.proposals:
        for intervention in proposal.initial.interventions:
            op=next(o for o in payload['creativeDiagnosis']['opportunities'] if o['opportunityId']==intervention.opportunityId)
            result.append(review_authored(intervention,op,payload['sourceReferenceCatalog'],f['text']))
    return f,payload,result


def test_both_actual_real_proposals_revalidated_without_modifying_or_promoting_them():
    raw=saved_response();before=deepcopy(raw);f,payload,reviews=reviewed(raw)
    assert raw==before and hashlib.sha256(REAL.read_bytes()).hexdigest()==REAL_SHA
    assert len(reviews)==2
    for review in reviews:
        assert review['technicalValidity']=='INVALID'
        assert review['sourceFidelity']=='UNKNOWN' and review['sourceDiagnostics']==[]
        assert review['materiality']['classification']=='VALID_BUT_EQUIVALENT'
        assert not review['materiality']['material'] and not review['accepted']
        assert len(review['temporalAdvisories'])==1
        assert review['temporalAdvisories'][0]['code']=='SOURCE_BEAT_WINDOW_REPEATED'
        assert not any('TIMING' in d['code'] for d in review['technicalDiagnostics'])
    assert [len(r['technicalDiagnostics']) for r in reviews]==[2,4]
    assert all(d['code']=='INVALID_CATALOG_REFERENCE' and d['allowedIds'] and d['field'].startswith('spatialRelationships.') for r in reviews for d in r['technicalDiagnostics'])
    provider=MockProvider(raw)
    result=perform_reconstruction(f['text'],f['context'],provider,'mock-replay-only')
    assert provider.calls==1 and not result['result']['candidates']
    assert all(r['classification']=='AUTHORING_CONTRACT_INVALID' for r in result['result']['rejectedProposals'])
    assert result['result']['improvementMetrics']['storyFidelityFailures']==0
    assert result['rawProviderResult']==raw


@pytest.mark.parametrize('candidate,valid_window',[(contact(),'0-2s'),(progression(),'5–10 seconds')])
def test_exact_source_window_is_valid_redundant_and_never_materiality_evidence(candidate,valid_window):
    candidate['interventions'][0]['production']['temporalPresentation']='During '+valid_window+', preserve the existing source beat window.'
    f,payload,reviews=reviewed(response([candidate]));review=reviews[0]
    assert review['accepted'] and review['technicalValidity']=='VALID'
    assert review['temporalAdvisories'][0]['materialEvidence'] is False
    compiled=compile_reconstruction(f['text'],f['context'],candidate)
    assert valid_window in compiled['prompt'] and compiled['creativeAssessment']['provenBetter'] is False


@pytest.mark.parametrize('text,code',[
    ('During 0-1s, reveal the note contact before the existing result.','UNSUPPORTED_NEW_SUB_BEAT_TIMING'),
    ('During 2-5s, preserve contact in the opening view.','WRONG_SOURCE_BEAT_WINDOW'),
    ('During 0-3s, preserve contact in the opening view.','CHANGED_SOURCE_BEAT_WINDOW'),
    ('During 0-16s, complete the whole source sequence.','STORY_DURATION_CHANGED'),
    ('Set the video duration to 16 seconds for this production.','STORY_DURATION_CHANGED'),
    ('Hold for 0.4 seconds before completing the contact.','UNSUPPORTED_TEMPORAL_CLAIM'),
    ('Add a one-second pause before the note attaches.','UNSUPPORTED_TEMPORAL_CLAIM'),
    ('During 2-0s, retain the original contact view.','INVALID_TIME_RANGE'),
])
def test_invented_timing_duration_and_unsupported_claims_stay_rejected(text,code):
    p=contact();p['interventions'][0]['production']['temporalPresentation']=text
    _,_,reviews=reviewed(response([p]));r=reviews[0]
    assert not r['accepted']
    assert any(code in d['code'] for d in r['technicalDiagnostics']+r['sourceDiagnostics'])


def test_catalog_has_generic_exact_other_hand_and_each_hand_mentions_not_fabricated_hands():
    f=inputs();payload=request_payload(f['text'],f['context']);refs=payload['sourceReferenceCatalog']
    hand_refs={key:r for key,r in refs.items() if r['beatId']=='beat_02' and r['quote'] in {'her other hand','each hand'}}
    assert {r['quote'] for r in hand_refs.values()}=={'her other hand','each hand'}
    for key,r in hand_refs.items():
        a,z=r['sourceSpan'];assert f['text'][a:z]==r['quote']
        assert r['identityResolution']=='UNKNOWN_SOURCE_MENTION_ONLY'
    assert not any(r['quote']=="Mimi's hands" for r in refs.values())
    for r in refs.values():
        a,z=r['sourceSpan'];assert f['text'][a:z]==r['quote']


def test_machine_readable_ids_are_in_wire_schema_and_per_beat_relationship_contract():
    f=inputs();payload=request_payload(f['text'],f['context']);schema=response_format(f['context'],f['text'])['json_schema']['schema'];defs=schema['$defs']
    allowed=payload['authoringContract']['allowedReferenceIdsByKind']
    assert defs['SpatialRelationship']['properties']['subjectRef']['enum']==allowed['ENTITY']
    assert defs['ChoreographyV2']['properties']['sourceActionRef']['enum']==allowed['ACTION']
    assert defs['ChoreographyV2']['properties']['sourceConsequenceRef']['enum']==allowed['CONSEQUENCE']
    assert defs['StatePresentationV2']['properties']['sourceStateRef']['enum']==allowed['STATE']
    assert not {'Mimi','the cabinet','the sticky note',"Mimi's hands"} & set(allowed['ENTITY'])
    opening=next(o for o in payload['authoringContract']['opportunityContracts'] if o['beatId']=='beat_01')
    assert opening['requiredSurfacePair']==['beat_01.expectedSurface','beat_01.actualSurface']
    assert all(key.startswith('beat_01.') for key in opening['allowedReferenceIdsByKind']['ENTITY'])
    assert payload['preferredCandidateCount']==1 and payload['maxCandidates']==2
    assert len(json.dumps(payload,ensure_ascii=False).encode())<=24000
    assert all('proposedImprovement' not in op for op in payload['creativeDiagnosis']['opportunities'])


@pytest.mark.parametrize('kind',['wrong-kind','wrong-beat','name-alias','same-mention'])
def test_precise_reference_diagnostics_do_not_alias_or_claim_story_mutations(kind):
    p=contact();i=p['interventions'][0]
    if kind=='wrong-kind':i['production']['choreography']['sourceActionRef']='beat_01.actor'
    if kind=='wrong-beat':i['production']['choreography']['sourceActionRef']='beat_02.action'
    if kind=='name-alias':i['production']['spatialRelationships'][0]['subjectRef']='the cabinet'
    if kind=='same-mention':
        i['production']['spatialRelationships'][0]['subjectRef']='beat_01.finger'
        i['production']['spatialRelationships'][0]['objectRef']='beat_01.actualSurface'
    _,_,reviews=reviewed(response([p]));r=reviews[0]
    expected={'wrong-kind':'WRONG_REFERENCE_KIND','wrong-beat':'CROSS_BEAT_REFERENCE','name-alias':'INVALID_CATALOG_REFERENCE','same-mention':'SAME_SOURCE_MENTION_RELATION'}[kind]
    assert any(d['code']==expected for d in r['technicalDiagnostics'])
    assert r['sourceFidelity']=='UNKNOWN' and not r['accepted']


def test_genuine_new_source_bound_hand_reference_is_usable_for_physical_staging():
    f=inputs();payload=request_payload(f['text'],f['context']);refs=payload['sourceReferenceCatalog']
    hand=next(k for k,r in refs.items() if r['beatId']=='beat_02' and r['quote']=='her other hand')
    p=contact();i=p['interventions'][0];i.update(opportunityId='SEPARATE_ACTION_RESULT:beat_02',operation='SEPARATE_ACTION_RESULT')
    prod=i['production'];prod['spatialRelationships']=[{'subjectRef':hand,'objectRef':'beat_02.object','relation':'LEFT_OF',
        'instruction':'Keep {'+hand+'} to the left of the existing {beat_02.object}, leaving the contact edge outside the overlapping hand silhouette.'}]
    prod['choreography'].update(sourceActionRef='beat_02.action',sourceConsequenceRef='beat_02.consequence',
        instruction='Carry the existing peel laterally along the exposed sticky edge, keeping the participating hand silhouettes separated through the source split.',consequencePresentation=None)
    prod.update(temporalPresentation=None,cameraComposition=None,generatorConstraints=[])
    _,_,reviews=reviewed(response([p]));assert reviews[0]['accepted']
    compiled=compile_reconstruction(f['text'],f['context'],p)
    assert 'her other hand' in compiled['prompt'] and 'locked-off medium shot;' not in compiled['prompt']


def test_nullable_unchanged_fields_and_no_settings_padding_still_compile_authored_delta():
    p=contact();prod=p['interventions'][0]['production']
    prod.update(temporalPresentation=None,cameraComposition=None,generatorConstraints=[])
    f,payload,reviews=reviewed(response([p]));assert reviews[0]['accepted']
    compiled=compile_reconstruction(f['text'],f['context'],p)
    assert prod['choreography']['instruction'] in compiled['prompt']
    assert '[close-up on Mimi\'s hand]' in compiled['prompt']
    assert any(s['author']=='PROTECTED_SOURCE' and "close-up on Mimi's hand" in s['text'] for s in compiled['productionProvenance']['segments'])
    assert 'None' not in compiled['prompt'] and 'Stage the cabinet and her finger on' not in compiled['prompt']
    assert all(i['author']=='MODEL_AUTHORED' for b in compiled['productionProvenance']['beats'] for i in b['instructions'])
    with patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No real providers')):compiled['review']=canonical_review(f,compiled)
    assert compiled['review']['canonicalRuleEvaluation']['rulesetVersion']=='1.11'
    assert compiled['review']['canonicalRuleEvaluation']['score']==pytest.approx(f['baselineScore'])
    assert compiled['review']['family8']['renderAuthorization']['status']=='BLOCKED_PENDING_EVIDENCE'


def test_reference_validity_and_new_camera_words_do_not_establish_materiality():
    raw=saved_response();p=contact();prod=p['interventions'][0]['production'];real=raw['proposals'][0]['initial']['interventions'][0]['production']
    # A separate controlled counterexample, not a repair of the immutable real fixture.
    prod['spatialRelationships'][0].update(relation='IN_FRONT_OF',instruction='Keep Mimi in front of the cabinet with the finger and intended cabinet surface visible.')
    prod['choreography']['instruction']=real['choreography']['instruction']
    prod['choreography']['consequencePresentation']=real['choreography']['consequencePresentation']
    prod['temporalPresentation']=real['temporalPresentation'];prod['cameraComposition']='A very long, beautiful, crystal-clear close-up shows every existing detail with wonderful visual clarity.'
    prod['generatorConstraints']=real['generatorConstraints']
    _,_,reviews=reviewed(response([p]));r=reviews[0]
    assert r['technicalValidity']=='VALID'
    assert r['sourceFidelity']=='UNKNOWN' and not r['accepted']
    assert r['materiality']['classification']=='VALID_BUT_EQUIVALENT'


def test_frozen_v1_actual_response_replay_retains_original_interpretation():
    f=inputs();f['context']['optimizationGenerationInstructionsVersion']=LEGACY_AUTHORING_VERSION;raw=saved_response()
    result=perform_reconstruction(f['text'],f['context'],MockProvider(raw),'mock-historical-replay')
    assert not result['result']['candidates']
    assert all(any('no unbound sub-beat timestamps' in reason for reason in r['reasons']) for r in result['result']['rejectedProposals'])
    assert result['result']['instructionsVersion']==LEGACY_AUTHORING_VERSION
    assert 'authoringContract' not in request_payload(f['text'],f['context'])
    assert 'enum' not in response_format(f['context'])['json_schema']['schema']['$defs']['SpatialRelationship']['properties']['subjectRef']


def test_generation_instructions_request_physical_difference_and_abstention_not_padding():
    f=inputs();system=generation_system(f['context'])
    assert 'preferably ONE' in system and 'not rewriting the approved story' in system
    assert 'Never put an entity name or quote into a Ref property' in system
    assert 'null when unchanged' in system and 'do not restate aspect ratio' in system
    assert 'copy source action/result sentences' in system and 'proposals []' in system
    assert AUTHORING_VERSION!=LEGACY_AUTHORING_VERSION


def test_source_state_counts_accept_equivalent_numerals_without_changing_the_rule():
    p=progression()
    for number,state in zip((2,4,8),p['interventions'][0]['production']['stateProgression']):
        state['placementInstruction']=state['placementInstruction'].replace('{'+state['sourceStateRef']+'}',str(number))
    _,_,reviews=reviewed(response([p]));assert reviews[0]['accepted']
    assert reviews[0]['sourceFidelity']=='UNKNOWN'
