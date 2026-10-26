"""Source-bound premise facts, independent quality, and frozen downstream parity."""
from copy import deepcopy
import json
from pathlib import Path
import types
import pytest
from pydantic import ValidationError
from app.workflow import premise_naturalness as nat,beat_grammar
from app.workflow.canonical_creative_evidence import from_structured
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.structured_sfe_replay import structured_input
from app.workflow.short_concept_generation import ranking_input
from app.workflow.concept_ranking import normalize
from app.workflow.premise_admission_evidence import ResponseEvidence,object_support

ROOT=Path(__file__).parents[3]
DOC=ROOT/'intelligence/docs/premise-admission-opening-generalization-v1'
DATA=json.loads((DOC/'audit-before-modification.json').read_text())['candidates']


def acquire(row,changes=None,kind='SEMANTIC'):
    c=deepcopy(row['candidate']);raw=deepcopy(row['raw']);raw.update(changes or {})
    for key in ['primaryObject','everydayGoal','impossibleRule']:
        c[key]=raw[key]
    source=structured_input(raw,c)
    return c,from_structured(normalize(ranking_input(c))['evaluationText'],source,kind)


def assess(row,changes=None,kind='SEMANTIC'):
    c,ctx=acquire(row,changes,kind)
    return nat.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)


@pytest.mark.parametrize('row',DATA,ids=lambda r:r['ideaId'])
def test_all18_default_and_downstream_exactly_unchanged(row):
    c,ctx=acquire(row)
    assert nat.assess(c,canonical_creative_evidence=ctx)==row['naturalness']
    result=assess(row)
    assert result['canonicalCreativeEvidence']==ctx.receipt()
    assert result['openingEvidence']['goalVisible']==ctx.facts['goal']['visibleInOpening']
    assert result['responseEvidenceState']!='RESPONSE_MISSING'
    assert not result['admitted']
    projected,validation,_=evaluate(c,structured_input(row['raw'],c))
    assert validation==row['validation']
    assert beat_grammar.assess(c['structuredBeatPlan'],canonical_creative_evidence=ctx,unclassified_consequence_support=True)==row['beatGrammar']


@pytest.mark.parametrize('id',['raw-013','raw-007','raw-026','raw-027'])
def test_four_pass_cases_source_consistent_and_exact_admission_reason(id):
    row=next(r for r in DATA if r['ideaId']==id);r=assess(row)
    assert r['goalInterferenceType']=='DIRECT'
    assert not r['admitted']
    assert r['qualityEvidence']['exactObjectRelevance']['qualitySupport']=='UNRESOLVED'
    assert not r['qualityEvidence']['exactObjectRelevance']['independentlyVerified']
    assert r['responseEvidence']['diagnosisCategory']==('D' if id=='raw-007' else 'B')
    assert r['qualityAssessmentStatus']=='UNRESOLVED'
    assert r['admissionCriteria']['taxonomyDependentCriteriaRemainUnresolved']


def test_raw013_presence_is_not_missing_or_automatic_quality_bonus():
    r=assess(next(r for r in DATA if r['ideaId']=='raw-013'))
    assert r['responseEvidenceState']=='RESPONSE_PRESENT_UNCLASSIFIED'
    assert r['responseType'] is None and r['premiseNaturalness']=='CONTRIVED'
    assert r['qualityAssessmentStatus']=='UNRESOLVED' and not r['admitted']
    assert r['openingEvidence']['openingFactsState']=='OPENING_FACTS_PRESENT'
    assert r['instantCausalLegibility']==35
    assert r['openingEvidence']['stillCausalLegibility']=='UNRESOLVED'
    assert not any(f['code']=='UNSUPPORTED_RESPONSE' for f in r['flags'])
    assert {'EXACT_OBJECT_DEPENDENCY_NOT_VERIFIED','STILL_FRAME_CAUSALITY_NOT_ESTABLISHED'} <= {f['code'] for f in r['flags']}


def test_known_incompatible_response_preserves_existing_arbitrary_filter():
    r=assess(DATA[0],dict(primaryObject='fork',everydayGoal='eat food',normalExpectation='Fork carries food to mouth.',impossibleRule='The fork floats away whenever lifted.',whyThisObject='Fork is a tool for food.',goalRuleRelationship='The food floats away, preventing eating.'))
    assert r['responseEvidenceState']=='RESPONSE_PRESENT_INCOMPATIBLE'
    assert r['responseEvidence']['diagnosisCategory']=='C'
    assert r['qualityAssessmentStatus']=='PRESENT_BUT_LOW_QUALITY'
    assert not r['admitted']
    assert 'ARBITRARY_MAGIC_RELATIONSHIP' in {f['code'] for f in r['flags']}


@pytest.mark.parametrize('rule,state',[('', 'RESPONSE_MISSING'),('Maybe the brush changes.', 'RESPONSE_AMBIGUOUS')])
def test_missing_and_ambiguous_are_distinct(rule,state):
    r=assess(DATA[1],dict(impossibleRule=rule))
    assert r['responseEvidenceState']==state
    assert r['premiseNaturalness']=='BROKEN' and not r['admitted']


def test_exact_object_relevance_is_required_even_when_rule_is_explicit():
    r=assess(DATA[1],dict(whyThisObject='Any object can produce this unrelated random magic.'))
    assert r['qualityEvidence']['arbitraryMagicRisk']['explicitlyPortable']
    assert r['qualityAssessmentStatus']=='PRESENT_BUT_LOW_QUALITY' and not r['admitted']
    assert r['objectSpecificityScore']<70
    assert 'ARBITRARY_MAGIC_RELATIONSHIP' in {f['code'] for f in r['flags']}


def test_direct_goal_interference_without_response_label():
    r=assess(DATA[1]);assert r['responseType'] is None
    assert r['goalInterferenceType']=='DIRECT'
    assert r['qualityEvidence']['goalInterference']['relationMatchesGoal']
    assert r['qualityEvidence']['goalInterference']['visibleEffectGoalMatches']


def test_motion_opening_can_have_facts_and_remain_weak():
    r=assess(DATA[0]);o=r['openingEvidence']
    assert o['goalVisible'] and o['objectVisible'] and o['problemVisible']
    assert o['needsMotionToUnderstand'] and o['blockerClassification']=='MOTION_DEPENDENT_OPENING'
    assert r['instantCausalLegibility']==35 and not r['admitted']


@pytest.mark.parametrize('id',['raw-026','raw-027'])
def test_still_contrast_witness_independent_of_taxonomy_and_no_admission_bonus(id):
    r=assess(next(r for r in DATA if r['ideaId']==id))
    assert r['responseType'] is None
    assert r['openingEvidence']['sourceFunctionalContrastSupported']
    assert r['openingEvidence']['stillPropertyContrast']
    assert r['instantCausalLegibility']==90 and r['staticFrameLegibility']==85
    assert r['expectationDistance']=='CLEAR_CONTRADICTION'
    assert not r['admitted']


def test_color_presence_alone_cannot_bypass_use_pose_or_output_relation():
    row=next(r for r in DATA if r['ideaId']=='raw-027');c,ctx=acquire(row)
    # Unit source-frame diagnostic mutation; no generator or new saved concept.
    from app.workflow.premise_admission_evidence import opening_evidence
    class View:
        fields={**ctx.fields,'frameZeroDescription':'Mimi holds a brush near a blue shirt and an orange chair.'}
        facts=ctx.facts
    o=opening_evidence(c,View(),row['naturalness'])
    assert not o['sourceFunctionalContrastSupported']


def test_unknown_object_alias_is_unresolved_not_false_missing():
    assert object_support('Refrigerator','Noah holds fridge door open.')['present'] is None
    assert object_support('Hairbrush','Opa holds a brush in his hair.')['present'] is True


def test_manual_and_semantic_equal_judgments():
    a=assess(DATA[1],kind='MANUAL');b=assess(DATA[1])
    a.pop('canonicalCreativeEvidence');b.pop('canonicalCreativeEvidence');assert a==b


def test_evidence_state_model_cannot_accept_score_or_pass():
    for field,value in [('score',100),('admitted',True),('status','PASS')]:
        with pytest.raises(ValidationError):ResponseEvidence(**{field:value})


def test_mode_requires_strict_canonical_evidence():
    with pytest.raises(ValueError,match='explicit canonical'):nat.assess({},generalized_premise_evidence=True)


def test_legacy_deterministic_fixtures_exact_full_reports():
    module=types.ModuleType('app.workflow.old_nat');module.__package__='app.workflow';module.__file__=nat.__file__
    src=(DOC/'legacy-premise_naturalness.py.txt').read_text();exec(compile(src,str(DOC/'legacy-premise_naturalness.py.txt'),'exec'),module.__dict__)
    fixtures=json.loads((ROOT/'intelligence/ml-service/tests/fixtures/premise_naturalness_v1_cases.json').read_text())['cases']
    for c in fixtures.values():assert nat.assess(c)==module.assess(c)


def test_text_or_dialogue_cannot_supply_strong_still_frame():
    row=next(r for r in DATA if r['ideaId']=='raw-027');c,ctx=acquire(row)
    from app.workflow.premise_admission_evidence import opening_evidence
    class View:
        fields={**ctx.fields,'frameZeroDescription':row['raw']['frameZeroDescription']+' A caption explains the color rule.'}
        facts=ctx.facts
    o=opening_evidence(c,View(),row['naturalness'])
    assert o['requiresTextOrDialogue'] and o['stillCausalLegibility']=='UNRESOLVED'


def test_colored_background_objects_do_not_establish_output_contrast():
    row=next(r for r in DATA if r['ideaId']=='raw-027');c,ctx=acquire(row)
    from app.workflow.premise_admission_evidence import opening_evidence
    class View:
        fields={**ctx.fields,'frameZeroDescription':'Mimi is painting a wall with a blue paint bucket; an orange chair is behind her.'}
        facts=ctx.facts
    assert not opening_evidence(c,View(),row['naturalness'])['sourceFunctionalContrastSupported']


def test_sanitized_visual_failure_is_not_missing_raw_source():
    r=assess(next(r for r in DATA if r['ideaId']=='raw-031'));o=r['openingEvidence']
    assert o['frameZeroDescription'] and not o['sourceFrameVisual']
    assert o['characterVisible'] and o['objectVisible']
    assert o['blockerClassification']=='EVIDENCE_SOURCE_MISMATCH'
    assert r['responseEvidenceState']=='RESPONSE_PRESENT_UNCLASSIFIED'
