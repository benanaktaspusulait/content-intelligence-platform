"""Prospective ownership/anchor regression; synthetic opinions, zero inference."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
import pytest
from app.workflow import story_assessment as a
from story_experiment_fixture import assessment_inputs,assessment_review,evidence_ids
from story_assessment_cases import material_comparison,DOCS
from test_story_assessment import configuration


def example():
    text,c=assessment_inputs();p=a.wire(text,c)['payload'];return text,c,p,assessment_review(p)


def all_pass(v,p):
    for ref,row in v['candidateAssessments'].items():
        for check,f in row['semanticChecks'].items():
            ids=[x for group in p['semanticChecks'][check]['anchorEvidence'].values() for x in group]
            f.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=list(dict.fromkeys(ids)),candidateEvidenceIds=evidence_ids(p,'CANDIDATE_'+ref),reason='Synthetic semantic support through paraphrase, not certified truth.')


@pytest.mark.parametrize('outcomes,expected',[(('PASS',),'PASS'),(('UNKNOWN',),'UNKNOWN'),(('FAIL',),'FAIL'),(('FAIL','UNKNOWN'),'FAIL')])
def test_aggregation_unknown_reasons_and_eligibility(outcomes,expected):
    text,c,p,v=example();all_pass(v,p)
    for check,outcome in zip(('trigger_conditions','single_mechanic'),outcomes):
        f=v['candidateAssessments']['A']['semanticChecks'][check]
        f.update(outcome=outcome,basis={'PASS':'SEMANTIC_SUPPORT','UNKNOWN':'INSUFFICIENT','FAIL':'CONTRADICTION'}[outcome],reason='Unchanged model reason: '+check)
    v['candidateAssessments']['A']['creativeConclusion']=material_comparison(p)
    before=deepcopy(v);derived=a.derive_assessment(v,text,c);row=derived['candidateAssessments']['A']
    assert row['semanticOutcome']=='SEMANTIC_SOURCE_'+expected
    assert row['sourceUnknowns']==[{'check':k,'reason':f['reason']} for k,f in v['candidateAssessments']['A']['semanticChecks'].items() if f['outcome']=='UNKNOWN']
    assert row['eligibleForOwnerProposal']==(expected=='PASS')
    assert v==before and derived['ownerDecision']=='PENDING'
    assert not any(derived[k] for k in ('sourceApproved','buildPromptAuthorized','renderAuthorized'))


def test_no_materiality_or_research_policy_means_no_eligibility():
    text,c,p,v=example();all_pass(v,p)
    assert not a.derive_assessment(v,text,c)['candidateAssessments']['A']['eligibleForOwnerProposal']
    v['candidateAssessments']['A']['creativeConclusion']=material_comparison(p)
    c['assessmentScope']['ownerPolicyApproval']=False
    assert 'RESEARCH_POLICY_NOT_AUTHORIZED' in a.derive_assessment(v,text,c)['candidateAssessments']['A']['eligibilityRestrictions']


@pytest.mark.parametrize('field',['semanticOutcome','sourceUnknowns','eligibleForOwnerProposal'])
def test_derived_fields_cannot_be_model_authored(field):
    text,c,p,v=example();assert field not in a.response_contract(p['evidenceCatalog'])['$defs']['candidate_A']['properties']
    v['candidateAssessments']['A'][field]=False
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


def test_preference_is_preserved_even_when_source_ineligible():
    text,c,p,v=example();v['researchPreference']='A'
    derived=a.derive_assessment(v,text,c)
    assert derived['researchPreference']=='A' and not derived['candidateAssessments']['A']['eligibleForOwnerProposal']


@pytest.mark.parametrize('check',['rule','trigger_conditions','single_mechanic','causal_clarity'])
def test_release_alone_is_not_rule_anchor_and_additional_context_allowed(check):
    text,c,p,v=example();f=v['candidateAssessments']['A']['semanticChecks'][check]
    f.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip remains covered'),candidateEvidenceIds=evidence_ids(p,'CANDIDATE_A'),reason='Synthetic definite claim.')
    with pytest.raises(ValueError,match='protected-fact anchor'):a.validate_review(v,text,c)
    f['sourceEvidenceIds']+=evidence_ids(p,'SOURCE','every removal or transfer attempt')
    assert a.validate_review(v,text,c) is v


def test_interpretation_contract_and_source_mapping_are_generic():
    text,c,p,v=example();sc=p['semanticChecks']
    assert 'activating the impossible rule' in sc['trigger_conditions']['meaning']
    assert 'primary impossible mechanism' in sc['single_mechanic']['meaning']
    assert sc['trigger_conditions']['anchorEvidence']==sc['rule']['anchorEvidence']
    assert sc['continuity']['anchorEvidence']!=sc['rule']['anchorEvidence']
    assert not any(x in a.SYSTEM for x in ('Pip','sneeze','S05','S06'))
    # Offset mapping works on another story, without inferred locks or event graphs.
    source='A fox. A coin duplicates on touch. A bell releases it. It rests.'
    from app.workflow.story_evidence import review_evidence_catalog
    cat=review_evidence_catalog({'SOURCE':source,'CANDIDATE_A':source,'CANDIDATE_B':source})
    quote='A coin duplicates on touch.';start=source.index(quote)
    context={'assessmentScope':{'sourceScope':{'protectedAnchors':[{'id':'rule','start':start,'end':start+len(quote),'quote':quote}]}}}
    mapped=a.check_scope(source,context,cat)
    assert mapped['rule']['anchorEvidence']['rule']==[cat['records'][1]['evidenceId']]
    assert mapped['continuity']['unmappedAnchors']==['continuity']


@pytest.mark.parametrize('dim',['SCROLL_STOP_VISUAL_PROMISE','ENDING_REPLAY'])
def test_creative_boundary_context_and_unknown_allowed(dim):
    text,c,p,v=example();d=v['candidateAssessments']['A']['creativeDimensions'][dim]
    d['candidateEvidenceIds']=evidence_ids(p,'CANDIDATE_A','split into eight')
    with pytest.raises(ValueError,match='boundary evidence'):a.validate_review(v,text,c)
    d.update(candidateEvidenceIds=[],strength='UNKNOWN',weakness='UNKNOWN',risk='UNKNOWN')
    assert a.validate_review(v,text,c) is v


def test_conservative_comparison_with_unknown_completes_without_preference_repair():
    text,c,p,v=example()
    for row in v['candidateAssessments'].values():row['creativeConclusion'].update(outcome='NO_MATERIAL_IMPROVEMENT',materialityReason='Posture differs but a visible production gain is not established.')
    d=a.derive_assessment(v,text,c)
    assert d['researchPreference']=='NO_CREATIVE_WINNER'
    assert all(r['semanticOutcome']=='SEMANTIC_SOURCE_UNKNOWN' and not r['eligibleForOwnerProposal'] for r in d['candidateAssessments'].values())


def test_real_v4_stays_rejected_diagnostic_is_not_a_new_review():
    text,c,p,v=example();e=DOCS/'real-timeout-hardened-story-review-evidence';path=e/'raw-openai-review.txt';before=path.read_bytes();raw=json.loads(before)
    assert hashlib.sha256(before).hexdigest()==json.loads((e/'durable-provider-receipt.json').read_text())['responseSha256']
    ns={'__name__':'app.workflow.story_assessment','__package__':'app.workflow','__file__':a.__file__}
    exec((DOCS/'story-review-derived-verdict-evidence/legacy-v4-story-assessment.py.txt').read_text(),ns)
    with pytest.raises(ValueError,match='cannot become PASS'):ns['validate_review'](raw,text,c)
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(raw,text,c)
    for ref,row in raw['candidateAssessments'].items():
        d=a.semantic_summary(row['semanticChecks'])
        assert d['semanticOutcome']=='SEMANTIC_SOURCE_UNKNOWN' and len(d['sourceUnknowns'])==2
        assert not set(row['semanticChecks']['rule']['sourceEvidenceIds']) & set(p['semanticChecks']['rule']['anchorEvidence']['rule'])
    assert json.loads((e/'actual-final-run.json').read_text())['state']=='STOPPED' and path.read_bytes()==before
