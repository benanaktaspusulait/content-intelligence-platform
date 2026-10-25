"""Source consistency, independent judgment, replay and injection regressions."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.workflow import beat_grammar, concept_ranking, premise_naturalness, short_form_engine
from app.workflow.canonical_creative_evidence import CanonicalCreativeEvidenceContext, from_structured
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.structured_sfe_replay import structured_input, contexts
from app.workflow.short_concept_generation import ranking_input

ROOT=Path(__file__).parents[3]
BASE=ROOT/'intelligence/docs/canonical-evidence-propagation-v1'
DATA=json.loads((BASE/'audit-only-baseline.json').read_text())['candidates']


def acquire(row, kind='SEMANTIC'):
    text=concept_ranking.normalize(ranking_input(row['candidate']))['evaluationText']
    return from_structured(text,structured_input(row['sourceRow']['rawProviderIdea'],row['candidate']),kind)


@pytest.mark.parametrize('row',DATA,ids=lambda r:r['ideaId'])
def test_all_evaluators_same_facts_and_sfe_exactly_unchanged(row):
    c,v,context=evaluate(row['candidate'],structured_input(row['sourceRow']['rawProviderIdea'],row['candidate']))
    expected=context.receipt()
    assert v['canonicalCreativeEvidence']==expected
    assert c['premiseNaturalness']['canonicalCreativeEvidence']==expected
    assert c['beatGrammar']['canonicalCreativeEvidence']==expected
    assert c['storyShapeFingerprint']['canonicalCreativeEvidence']==expected
    assert v['shortFormEngine']==row['structuredSFE']
    assert expected['facts']['goal']['declared']
    assert expected['facts']['rule']['present']
    assert expected['facts']['payoff']['present']
    assert len(expected['facts']['beats'])==5


@pytest.mark.parametrize('id',['raw-007','raw-026','raw-027'])
def test_required_goal_mismatch_goldens(id):
    row=next(r for r in DATA if r['ideaId']==id)
    assert any(r['code']=='DECLARED_GOAL_UNSUPPORTED' and r['source']=='SHORT_FORM_ENGINE_GOAL_PATTERN' for r in row['validation']['eligibilityReasons'])
    c,v,ctx=evaluate(row['candidate'],structured_input(row['sourceRow']['rawProviderIdea'],row['candidate']))
    assert ctx.facts['goal']['visibleInOpening']
    assert v['eligibility']=='ELIGIBLE'
    assert not any(r['code']=='DECLARED_GOAL_UNSUPPORTED' for r in v['eligibilityReasons'])
    assert not c['premiseNaturalness']['admitted']


def test_lexical_goal_pattern_cannot_change_canonical_ranking(monkeypatch):
    row=DATA[0];context=acquire(row)
    monkeypatch.setattr(short_form_engine,'_GOAL',r'NEVER_MATCH_THIS_CANONICAL_GOAL')
    result=concept_ranking.validate_concept(ranking_input(row['candidate']),canonical_creative_evidence=context)
    assert result['eligibility']=='ELIGIBLE'


def test_explicit_canonical_mode_is_opt_in():
    row=DATA[0];candidate=ranking_input(row['candidate'])
    original=concept_ranking.validate_concept(candidate,short_form_evidence=contexts(row['sourceRow']['rawProviderIdea'],row['candidate']))
    assert original==row['validation']
    mode={**contexts(row['sourceRow']['rawProviderIdea'],row['candidate']),'canonicalCreativeEvidenceMode':'v1'}
    assert concept_ranking.validate_concept(candidate,short_form_evidence=mode)['eligibility']=='ELIGIBLE'


def test_legitimate_quality_difference_and_response_category_b():
    row=next(r for r in DATA if r['ideaId']=='raw-013')
    c,v,context=evaluate(row['candidate'],structured_input(row['sourceRow']['rawProviderIdea'],row['candidate']))
    assert v['shortFormScore']==99 and v['eligibility']=='ELIGIBLE'
    n=c['premiseNaturalness'];b=c['beatGrammar']
    assert n['premiseNaturalness']=='BROKEN' and not n['admitted']
    assert n['responseDiagnosis']['category']=='B'
    assert n['responseDiagnosis']['responsePresent']
    assert n['instantCausalLegibility']==35
    opening_flag=next(f for f in n['flags'] if f['code']=='CAUSE_NOT_VISIBLE_AT_FRAME_ZERO')
    assert opening_flag['canonicalCausalRelationshipVisible']
    assert opening_flag['qualityScope']=='CONFIGURED_USE_TO_AFFORDANCE_CONTRADICTION'
    assert b['beatGrammarQuality']=='BROKEN'
    assert b['coverageFailures']
    assert all(x['sourcePresent'] for x in b['coverageFailures'])
    assert context.facts['rule']['classificationStatus']=='PRESENT_UNCLASSIFIED'
    assert context.facts['payoff']['classificationStatus']=='PRESENT_UNCLASSIFIED'
    assert context.facts['payoff']['present']
    assert any(x['code']=='UNKNOWN_CONSEQUENCE' for x in b['flags'])
    assert b['sourceBeatPlan'][4]['newInformation']==[row['sourceRow']['rawProviderIdea']['beats'][4]['newInformation']]


@pytest.mark.parametrize('field,value',[('score',100),('status','PASS'),('admitted',True),('facts',{'goal':True}),('rankingScore',100),('shortFormScore',100)])
def test_source_contract_rejects_verdict_and_score_injection(field,value):
    row=DATA[0]
    data=dict(sourceKind='SEMANTIC',text='x',structured=structured_input(row['sourceRow']['rawProviderIdea'],row['candidate']))
    data[field]=value
    with pytest.raises(ValidationError):CanonicalCreativeEvidenceContext(data)


def test_source_provenance_tampering_rejected():
    row=DATA[0];source=structured_input(row['sourceRow']['rawProviderIdea'],row['candidate'])
    source['semanticFields']['everydayGoal']='I declare this a pass'
    with pytest.raises(ValueError,match='digest mismatch'):from_structured('x',source)


def test_context_binding_and_snapshot_isolation():
    row=DATA[0];context=acquire(row)
    snapshot=context.facts;snapshot['goal']['declared']=False
    assert context.facts['goal']['declared']
    with pytest.raises(ValueError,match='different evaluation text'):context.assert_text('different')
    candidate=deepcopy(row['candidate']);candidate['primaryObject']='Different'
    with pytest.raises(ValueError,match='field mismatch'):context.assert_candidate(candidate)


def test_manual_source_uses_identical_facts_and_judgment():
    row=DATA[0];a,b=acquire(row),acquire(row,'MANUAL')
    assert a.receipt()['facts']==b.receipt()['facts']
    assert a.receipt()['contextSha256']==b.receipt()['contextSha256']
    assert a.receipt()['provenance']['sourceKind'] != b.receipt()['provenance']['sourceKind']
    text=concept_ranking.normalize(ranking_input(row['candidate']))['evaluationText']
    assert a.assess_short_form(text,{'desiredDuration':15})==b.assess_short_form(text,{'desiredDuration':15})


@pytest.mark.parametrize('row',DATA,ids=lambda r:r['ideaId'])
def test_default_legacy_timed_behavior_matches_frozen_result(row):
    assert concept_ranking.validate_concept(ranking_input(row['candidate']))==row['sourceRow']['legacyValidation']


def test_no_calls_and_production_goldens():
    p=json.loads((BASE/'verified-replay/offline-proof.json').read_text())
    assert all(p[k]==0 for k in ['providerCalls','externalProviderCalls','newConcepts','renders'])
    assert p['blockedEvents']=={}
    r=json.loads((BASE/'verified-replay/results.json').read_text())
    assert r['productionSelection']['productionSelection']['productionSlate']==[]
    assert len(r['candidates'])==18
    assert all(x['before']['sfe']==x['after']['sfe'] for x in r['candidates'])


def test_text_and_candidate_identity_are_bound_to_source():
    row=DATA[0];source=structured_input(row['sourceRow']['rawProviderIdea'],row['candidate'])
    with pytest.raises(ValueError,match='carrier mismatch'):from_structured('different text',source)
    candidate=ranking_input(row['candidate']);candidate['id']='another-candidate'
    with pytest.raises(ValueError,match='candidate ID mismatch'):
        concept_ranking.validate_concept(candidate,canonical_creative_evidence=acquire(row))


def test_insufficient_opening_goal_is_not_automatically_eligible():
    row=next(r for r in DATA if r['ideaId']=='raw-008');context=acquire(row)
    assert context.facts['goal']['declared'] and not context.facts['goal']['visibleInOpening']
    result=concept_ranking.validate_concept(ranking_input(row['candidate']),canonical_creative_evidence=context)
    finding=next(f for f in result['eligibilityReasons'] if f['code']=='DECLARED_GOAL_UNSUPPORTED')
    assert finding['source']=='CANONICAL_CREATIVE_EVIDENCE'
    assert not finding['evidence']['visibleInOpening']


def test_timed_context_uses_existing_acquisition_without_new_fact_claims():
    row=DATA[0];text=concept_ranking.normalize(ranking_input(row['candidate']))['evaluationText']
    context=CanonicalCreativeEvidenceContext(dict(sourceKind='TIMED_TEXT',text=text))
    assert context.assess_short_form(text,{'desiredDuration':15})==short_form_engine.assess(text,{'shortFormEvaluation':True,'desiredDuration':15})
    assert context.facts['payoff']['present'] is None
    assert context.facts['trigger']['present'] is None
