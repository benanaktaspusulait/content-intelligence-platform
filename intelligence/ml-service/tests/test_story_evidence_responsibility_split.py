"""Offline evidence extraction proposal; never real creative verification."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from app.workflow.story_evidence import derive_source_evidence, proposed_story_authoring_contract
from app.workflow.story_experiment import validate, sha
from story_experiment_fixture import inputs, alternatives

ROOT=Path(__file__).resolve().parents[2]


def data():
    source,context=inputs()
    return source,context,alternatives(source,context['storyExperiment'])


def assert_exact_spans(body, rows):
    for row in rows:assert body[row['start']:row['end']]==row['quote']


def test_exact_facts_are_derived_without_model_certification_or_semantic_pass():
    source,context,values=data();c=values[0];c.pop('sourceContract');result=derive_source_evidence(source,context,c)
    assert result['status']=='DETERMINISTIC_SOURCE_CONTRACT_PASSED'
    assert result['semanticFidelity']=='UNKNOWN' and not result['paidReviewEligible'] and not result['sourceApproved']
    assert_exact_spans(c['text'],result['narrativeSpans'])
    for fact in result['protectedFacts']:
        assert source[fact['source']['start']:fact['source']['end']]==fact['source']['quote']
        assert_exact_spans(c['text'],fact['candidateLocations'])


@pytest.mark.parametrize('folder',['first-real-story-evolution-evidence','real-story-identity-fidelity-followup-evidence'])
def test_four_authentic_narratives_preserved_and_live_rejections_unchanged(folder):
    e=ROOT/'docs'/folder;req=json.loads((e/'exact-effective-story-request.json').read_text());payload=json.loads(req['messages'][1]['content'])
    raw=(e/'raw-model-response.txt').read_text();response=json.loads(raw);receipt=json.loads((e/'provider-receipt.json').read_text());source=payload['text'];context=payload['context']
    expected='34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1' if folder.startswith('first-') else '10dc1482d66514e153835b6e3cd90f4e8b58ff1e1d61f51fa99e42424f15fef3'
    assert hashlib.sha256(raw.encode()).hexdigest()==expected
    with patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('No inference')),patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('No inference')):
        gate=validate(source,context,response)
        assert not gate['eligible']
        if receipt.get('sourceValidation'):assert gate==receipt['sourceValidation']
        for c in response['alternatives']:
            before=deepcopy(c);result=derive_source_evidence(source,context,c)
            assert result['narrativeValidity']=='COMPLETE_BOUNDED_NARRATIVE'
            assert result['status']=='SEMANTIC_FIDELITY_REVIEW_REQUIRED'
            assert result['semanticFidelity']=='UNKNOWN' and not result['paidReviewEligible']
            assert result['narrativeSha256']==sha(c['text']) and c==before
            assert_exact_spans(c['text'],result['narrativeSpans'])
            assert any(claim['status']=='INVALID_EVIDENCE_CLAIM' for claim in result['modelEvidenceClaims'])
    assert (e/'raw-model-response.txt').read_text()==raw


def test_missing_literal_with_possible_continuity_does_not_fabricate_quote():
    source,context,values=data();c=values[0];quote=context['storyExperiment']['protectedAnchors'][3]['quote'];c['text']=c['text'].replace(quote,'The paper stays attached until the sneeze sends it onto the cabinet')
    r=derive_source_evidence(source,context,c);fact=r['protectedFacts'][3]
    assert fact['literalEvidence']=='MISSING' and fact['candidateLocations']==[]
    assert r['status']=='SEMANTIC_FIDELITY_REVIEW_REQUIRED' and r['semanticFidelity']=='UNKNOWN'
    assert any(x['anchorId']=='continuity' and x['status']=='INVALID_EVIDENCE_CLAIM' for x in r['modelEvidenceClaims'] if 'anchorId' in x)


def test_direct_source_contradiction_is_separate_from_invalid_quote():
    source,context,values=data();c=values[0];c['text']=c['text'].replace('Pip is relieved','Pip is not relieved')
    r=derive_source_evidence(source,context,c)
    assert r['status']=='DEFINITE_SOURCE_VIOLATION' and r['explicitContradictions']
    assert not r['paidReviewEligible']


def test_false_compliance_metadata_cannot_override_narrative():
    source,context,values=data();c=values[0];c['text']=c['text'].replace('Pip is relieved','Pip is not relieved');c['sourceContract']['status']='SOURCE_COMPLIANT'
    assert derive_source_evidence(source,context,c)['status']=='DEFINITE_SOURCE_VIOLATION'


@pytest.mark.parametrize('kind',['ENDING','PHYSICAL_RULE','CORE_PREMISE'])
def test_missing_or_changed_protected_fact_never_becomes_pass(kind):
    source,context,values=data();anchor=next(a for a in context['storyExperiment']['protectedAnchors'] if a['kind']==kind);c=values[0]
    c['text']=c['text'].replace(anchor['quote'],'A changed or paraphrased fact needs independent assessment')
    r=derive_source_evidence(source,context,c)
    assert r['status']=='SEMANTIC_FIDELITY_REVIEW_REQUIRED' and not r['paidReviewEligible']
    assert not validate(source,context,{'alternatives':values})['eligible']


def test_explicit_protected_change_is_a_proposal_not_approval():
    source,context,values=data();c=values[0];c['sourceContract'].update(status='PROTECTED_CHANGE_PROPOSAL',protectedChanges=[{'anchorId':'ending','proposedChange':'Unresolved ending','justification':'Owner review requested'}])
    r=derive_source_evidence(source,context,c)
    assert r['status']=='PROTECTED_CHANGE_PROPOSAL' and not r['sourceApproved'] and not r['paidReviewEligible']


def test_distinct_text_does_not_certify_material_improvement_and_superficial_pair_stays_blocked():
    source,context,values=data()
    assert values[0]['text']!=values[1]['text']
    for c in values:
        r=derive_source_evidence(source,context,c)
        assert r['independentReview']=='NOT_EXECUTED' and not r['renderAuthorized']
    values[1]['text']=values[0]['text']
    assert not validate(source,context,{'alternatives':values})['eligible']


def test_natural_unresolved_ending_when_source_permits_it():
    source,context,values=data();old=context['storyExperiment']['protectedAnchors'][-1]['quote'];new='Pip waits beside the cabinet, unsure what happens next.'
    source=source.replace(old,new)
    for a in context['storyExperiment']['protectedAnchors']:
        if a['kind']=='ENDING':a['quote']=new
        a['start']=source.index(a['quote']);a['end']=a['start']+len(a['quote'])
    context['storyExperiment']['sourceStorySha256']=sha(source)
    c=values[0];c['text']=c['text'].replace(old,new);c.pop('sourceContract')
    r=derive_source_evidence(source,context,c)
    assert r['status']=='DETERMINISTIC_SOURCE_CONTRACT_PASSED' and r['semanticFidelity']=='UNKNOWN'


def test_immediate_curiosity_needs_no_impossible_physics_opening():
    source,context,values=data();c=values[0];c['text']='Pip studies a puzzling blank spot, wondering what belongs there. '+c['text']
    r=derive_source_evidence(source,context,c)
    assert r['status']=='DETERMINISTIC_SOURCE_CONTRACT_PASSED'
    assert r['narrativeSpans'][0]['quote'].startswith('Pip studies')


def test_complete_narrative_survives_incomplete_evidence_metadata():
    source,context,values=data();c={k:values[0][k] for k in ('candidateId','title','text')};r=derive_source_evidence(source,context,c)
    assert r['narrativeValidity']=='COMPLETE_BOUNDED_NARRATIVE'
    assert all(x['status']=='NOT_SUPPLIED' for x in r['modelEvidenceClaims'])
    assert not r['paidReviewEligible']


def test_metadata_cannot_rescue_invalid_narrative():
    source,context,values=data();values[0]['text']='Short.'
    assert derive_source_evidence(source,context,values[0])['status']=='INVALID_GENERATION_OUTPUT'


def test_bad_model_offsets_do_not_poison_application_derived_offsets():
    source,context,values=data();values[0]['sourceContract']['bindings'][0].update(candidateStart=5,candidateEnd=7)
    r=derive_source_evidence(source,context,values[0]);assert r['modelEvidenceClaims'][4]['status']=='INVALID_EVIDENCE_CLAIM'
    assert r['protectedFacts'][0]['candidateLocations'][0]['quote']=='Pip the rabbit'
    assert not r['paidReviewEligible']


def test_proposed_contract_has_no_activation_or_authorization():
    p=proposed_story_authoring_contract()
    assert p['newSchemaVersion'] is None and p['status']=='PROPOSED_NOT_ACTIVATED'
    assert not p['dispatchEnabled'] and not p['paidReviewEligibilityChanged']
    assert not p['sourceApprovalEnabled'] and not p['buildPromptEnabled']
