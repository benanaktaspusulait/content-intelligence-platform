"""Admission provenance, real source contradictions, safety and frozen-score parity."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.workflow import premise_naturalness as nat,beat_grammar
from app.workflow.evidence_supported_admission_v2 import assess,project_naturalness,OPENING_FLOOR
from app.workflow.canonical_creative_evidence import from_structured
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.concept_ranking import normalize
from app.workflow.short_concept_generation import ranking_input
from app.workflow.structured_sfe_replay import structured_input,selected_run
from app.workflow.semantic_concept_generation import GenerationRequest

ROOT=Path(__file__).parents[3]
SOURCE=json.loads((ROOT/'intelligence/docs/premise-admission-opening-generalization-v1/audit-before-modification.json').read_text())['candidates']
BASE={r['ideaId']:r for r in json.loads((ROOT/'intelligence/docs/evidence-supported-premise-admission-v2/baseline.json').read_text())['candidates']}


def source_context(row,kind='SEMANTIC'):
    c=row['candidate'];return from_structured(normalize(ranking_input(c))['evaluationText'],structured_input(row['raw'],c),kind)


def fixture(kind='hammer',changes=None,weak_opening=False):
    """Minimal metamorphic test input only; no generator or saved production story.

    Reuses an existing declared rule/opening. Repetitive beats deliberately make
    this unsuitable as a new creative batch: premise admission is not BG scoring.
    """
    row=next(r for r in SOURCE if r['ideaId']==('raw-026' if kind=='hammer' else 'raw-007'))
    raw=deepcopy(row['raw']);c=deepcopy(row['candidate'])
    if kind=='hammer':
        beat=dict(strategy='Kiko hammers the nail gently.',visibleConsequence='The nail bends away from the wall and the picture frame falls.',newInformation='Hammering bends the nail and prevents hanging the picture frame.')
        if weak_opening:raw['frameZeroDescription']='Kiko holds a hammer by a bent nail in the wall, with a picture frame beside him.'
    else:
        beat=dict(strategy='Opa sets the alarm for 7 AM.',visibleConsequence='The hands spin backward, showing the wrong time and preventing Opa from waking at 7 AM.',newInformation='Setting the alarm reverses the hands, preventing the scheduled wake time.')
    raw['beats']=[deepcopy(beat) for _ in range(5)];raw['finalPayoff']=beat['visibleConsequence'];raw.update(changes or {})
    for key in ['primaryObject','everydayGoal','impossibleRule']:c[key]=raw[key]
    c['beats']=[dict(startSeconds=i*3,endSeconds=(i+1)*3,description=f"{c['protagonist']} {b['strategy']}. {b['visibleConsequence']} {b['newInformation']}") for i,b in enumerate(raw['beats'])]
    c['beats'][0]['description']=raw['frameZeroDescription']+' '+c['beats'][0]['description']
    c['frameZeroDescription']=c['beats'][0]['description'];c['finalPayoff']=c['beats'][-1]['description']
    for p,b in zip(c['structuredBeatPlan'],raw['beats']):p['objectResponse']=b['visibleConsequence'];p['characterConsequence']=b['newInformation']
    ctx=from_structured(normalize(ranking_input(c))['evaluationText'],structured_input(raw,c))
    return c,ctx


@pytest.mark.parametrize('row',SOURCE,ids=lambda r:r['ideaId'])
def test_all18_fallback_source_bound_and_frozen_outputs(row):
    c=row['candidate'];ctx=source_context(row);decision=assess(c,ctx)
    assert decision.sourceContextSha256==ctx.receipt()['contextSha256']
    assert decision.provenance=='EVIDENCE_SUPPORTED_UNCLASSIFIED'
    assert decision.responseClassificationStatus in ['PRESENT_UNCLASSIFIED','PRESENT_CLASSIFIED']
    current,v,_=evaluate(c,structured_input(row['raw'],c))
    assert v==BASE[row['ideaId']]['validation']
    assert beat_grammar.assess(c['structuredBeatPlan'],canonical_creative_evidence=ctx,unclassified_consequence_support=True)==BASE[row['ideaId']]['beatGrammar']
    n=nat.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)
    projected=project_naturalness(n,decision)
    assert all(projected[k]==value for k,value in n.items() if k!='admitted')


def test_strong_object_specific_unclassified_premise_can_be_admitted():
    c,ctx=fixture();d=assess(c,ctx,opening_mandatory=True)
    assert d.admitted and d.status=='ADMITTED_EVIDENCE_SUPPORTED_UNCLASSIFIED'
    assert d.coverage=='EVIDENCE_SUPPORTED_UNCLASSIFIED' and d.provenance=='EVIDENCE_SUPPORTED_UNCLASSIFIED'
    assert d.responseClassification is None and d.responseClassificationStatus=='PRESENT_UNCLASSIFIED'
    assert all(f['supported'] for f in d.factors.values())


def test_present_unclassified_does_not_automatically_admit():
    row=next(r for r in SOURCE if r['ideaId']=='raw-026');d=assess(row['candidate'],source_context(row))
    assert not d.admitted and d.responseClassification is None
    assert d.factors['objectSpecificity']['supported']
    assert not d.factors['causalCoherence']['supported']


@pytest.mark.parametrize('id,codes',[('raw-026',{'DECLARED_RULE_OUTCOME_REVERSED','UNDECLARED_TRIGGER_RESTRICTION'}),('raw-027',{'RULE_MODEL_CHANGED','UNDECLARED_MATERIAL_OR_FUNCTION'})])
def test_raw026_027_receive_real_quality_decisions(id,codes):
    row=next(r for r in SOURCE if r['ideaId']==id);d=assess(row['candidate'],source_context(row))
    assert d.status=='NOT_ADMITTED_RULE_INCOHERENT' and not d.admitted
    assert d.openingPassed
    assert codes<={r['code'] for r in d.reasons}
    assert all(d.factors[k]['supported'] for k in ['normalExpectation','objectSpecificity','trigger','goalInterference','nonArbitrary','functionalAffordanceRelationship','openingLegibility'])


def test_raw013_opening_never_bypassed():
    row=next(r for r in SOURCE if r['ideaId']=='raw-013');ctx=source_context(row);d=assess(row['candidate'],ctx,opening_mandatory=True)
    assert not d.admitted and not d.openingPassed
    assert d.factors['openingLegibility']['score']==35
    assert any(r['code']=='OPENING_BELOW_EXISTING_FLOOR' for r in d.reasons)


def test_core_admission_and_production_opening_are_independent():
    c,ctx=fixture(weak_opening=True);core=assess(c,ctx);combined=assess(c,ctx,opening_mandatory=True)
    assert core.admitted and core.corePremiseSupported and not core.openingPassed
    assert not combined.admitted and combined.status=='NOT_ADMITTED_OPENING_WEAK'
    # Premise boolean projection cannot remove the unchanged opening preselection gate.
    original=next(r['raw'] for r in SOURCE if r['ideaId']=='raw-026')
    raw={**original,**ctx.fields}
    after,v,_=evaluate(c,structured_input(raw,c))
    n=nat.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)
    after['premiseNaturalness']=project_naturalness(n,core)
    cfg=GenerationRequest.model_validate(json.loads((ROOT/'intelligence/docs/semantic-live-v1-seed-42-count-40/live-attempt/configuration.json').read_text())['generation'])
    result=selected_run([after],{c['candidateId']:v},cfg)
    reasons=result['suppressed'][0]['reasons']
    assert 'OPENING_EVIDENCE_INSUFFICIENT' in reasons and 'PREMISE_NOT_ADMITTED' not in reasons
    assert result['productionSelection']['productionSlate']==[]
    assert OPENING_FLOOR==60


def test_classified_but_unresolved_compatibility_can_use_fallback():
    c,ctx=fixture('clock');d=assess(c,ctx)
    assert d.admitted and d.provenance=='EVIDENCE_SUPPORTED_UNCLASSIFIED'
    assert d.responseClassificationStatus=='PRESENT_CLASSIFIED'
    assert d.responseClassification=='RETURN_ORIGIN'
    assert not d.openingPassed


def test_known_compatible_path_preserves_legacy_decision_and_metrics():
    cases=json.loads((ROOT/'intelligence/ml-service/tests/fixtures/premise_naturalness_v1_cases.json').read_text())['cases']
    for key,c in cases.items():
        old=nat.assess(c);d=assess(c)
        assert d.admitted==old['admitted']
        projection=project_naturalness(old,d)
        assert all(projection[k]==v for k,v in old.items() if k!='admitted')
    assert assess(cases['shoe_reset']).status=='ADMITTED_KNOWN_COMPATIBILITY'


def test_known_incompatibility_cannot_escape_through_fallback():
    cases=json.loads((ROOT/'intelligence/ml-service/tests/fixtures/premise_naturalness_v1_cases.json').read_text())['cases']
    d=assess(cases['fork_float'])
    assert not d.admitted and d.status=='NOT_ADMITTED_INCOMPATIBLE' and d.coverage=='INCOMPATIBLE'


def test_arbitrary_magic_and_weak_function_specificity_are_not_admitted():
    c,ctx=fixture(changes={'whyThisObject':'Any object can produce this unrelated random magic.'})
    d=assess(c,ctx);assert not d.admitted and d.status=='NOT_ADMITTED_ARBITRARY'
    assert not d.factors['nonArbitrary']['supported']
    c,ctx=fixture(changes={'normalExpectation':'A generic thing does something.'})
    d=assess(c,ctx);assert not d.admitted and not d.factors['objectSpecificity']['supported']


def test_fork_ceiling_teleport_does_not_gain_object_specificity_from_goal_block():
    beat=dict(strategy='Kiko touches the fork.',visibleConsequence='The ceiling teleports onto the food, blocking the food from his mouth.',newInformation='Touching the fork moves the ceiling onto the food and prevents eating food.')
    c,ctx=fixture(changes=dict(primaryObject='fork',everydayGoal='Eat food',normalExpectation='A fork carries food toward the mouth.',impossibleRule='Touching the fork makes the ceiling teleport onto the food.',visibleTrigger='Kiko touches the fork and the ceiling teleports onto the food.',whyThisObject='The fork changes the ceiling location.',goalRuleRelationship='The ceiling blocks eating the food, preventing the goal.',frameZeroDescription='Kiko tries to eat food with a fork, but the ceiling rests on the food.',beats=[deepcopy(beat) for _ in range(5)],finalPayoff=beat['visibleConsequence']))
    d=assess(c,ctx)
    assert d.factors['normalExpectation']['supported'] and d.factors['impossibleResponse']['supported']
    assert d.factors['trigger']['supported'] and d.factors['goalInterference']['supported']
    assert not d.admitted and not d.factors['objectSpecificity']['supported']


@pytest.mark.parametrize('changes,factor',[({'visibleTrigger':''},'trigger'),({'normalExpectation':''},'normalExpectation'),({'goalRuleRelationship':'The action does not interfere with hanging the picture.'},'goalInterference')])
def test_missing_trigger_expectation_or_contrived_interference_reject(changes,factor):
    c,ctx=fixture(changes=changes);d=assess(c,ctx)
    assert not d.admitted and not d.factors[factor]['supported']


def test_multiple_unrelated_rules_are_rejected_without_new_taxonomy():
    c,ctx=fixture(changes={'impossibleRule':'Every hammer strike bends the nail. A separate unrelated rule teleports the ceiling.'})
    d=assess(c,ctx);assert not d.admitted
    assert 'MULTIPLE_UNRELATED_RULES' in {r['code'] for r in d.reasons}


def test_unknown_coverage_without_canonical_evidence_is_not_a_free_pass():
    row=next(r for r in SOURCE if r['ideaId']=='raw-026');d=assess(row['candidate'])
    assert not d.admitted and d.coverage=='UNSUPPORTED'


def test_manual_and_semantic_source_do_not_change_admission():
    row=next(r for r in SOURCE if r['ideaId']=='raw-026');a=assess(row['candidate'],source_context(row));b=assess(row['candidate'],source_context(row,'MANUAL'))
    assert a.model_dump()==b.model_dump()


def test_projection_is_bound_to_source_context_and_provenance_does_not_change_scores():
    c,ctx=fixture();d=assess(c,ctx);n=nat.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)
    a=project_naturalness(n,d);b=project_naturalness(n,d.model_copy(update={'provenance':'KNOWN_COMPATIBILITY'}))
    assert a['admitted']==b['admitted']
    for k,value in n.items():assert a[k]==b[k]
    bad=d.model_copy(update={'sourceContextSha256':'0'*64})
    with pytest.raises(ValueError,match='context differs'):project_naturalness(n,bad)


def test_known_incompatibility_with_canonical_input_still_cannot_use_fallback():
    c,ctx=fixture(changes=dict(primaryObject='fork',everydayGoal='Eat food',normalExpectation='The fork carries food to the mouth.',impossibleRule='The fork floats away whenever lifted.',visibleTrigger='Kiko lifts the fork and it floats away.'))
    d=assess(c,ctx)
    assert d.status=='NOT_ADMITTED_INCOMPATIBLE' and d.coverage=='INCOMPATIBLE'
    assert d.provenance=='KNOWN_COMPATIBILITY' and not d.admitted


def test_simile_is_not_a_literal_material_change_or_an_automatic_pass():
    from app.workflow.evidence_supported_admission_v2 import coherence_findings
    fields={'impossibleRule':'Each brush stroke makes another knot in the hair.','beats':[dict(strategy='Use conditioner.',visibleConsequence='The hair becomes like rubber and the knot stretches.',newInformation='The knot is elastic.')]}
    assert not any(r['code']=='UNDECLARED_MATERIAL_OR_FUNCTION' for r in coherence_findings(fields))
    row=next(r for r in SOURCE if r['ideaId']=='raw-013');d=assess(row['candidate'],source_context(row),opening_mandatory=True)
    assert not d.admitted and d.corePremiseSupported and not d.openingPassed
    assert d.factors['causalCoherence']['reviewNotes']


def test_clarification_and_negated_opposite_do_not_invent_rule_violations():
    from app.workflow.evidence_supported_admission_v2 import coherence_findings
    f=dict(impossibleRule='The umbrella always moves to the lowest body part.',beats=[dict(strategy='Crouch.',visibleConsequence='The umbrella moves to the lowest body part.',newInformation='The umbrella moves to the lowest part, not the highest.')])
    assert not coherence_findings(f)
    f=dict(impossibleRule='Every hammer strike bends the nail.',beats=[dict(strategy='Strike.',visibleConsequence='The nail bends.',newInformation='The hammer cannot straighten the nail.')])
    assert not coherence_findings(f)
    f=dict(impossibleRule='The brush paints the complementary color.',beats=[dict(strategy='Use paint.',visibleConsequence='The brush paints the complementary color.',newInformation='The rule includes complementary color, not a hue shift.')])
    assert not coherence_findings(f)


def test_downstream_production_order_does_not_read_admission_provenance():
    from app.workflow.concept_production_selection import select_production
    old=json.loads((ROOT/'intelligence/docs/creative-shape-v1/experiment-seed-42-count-20.json').read_text())
    rows=old['rankingResult']['rankedEligibleCandidates']
    candidates=[deepcopy(r['candidate']) for r in old['candidates']]
    a=deepcopy(candidates);b=deepcopy(candidates)
    for c in a:c['premiseNaturalness']['admissionProvenance']='KNOWN_COMPATIBILITY'
    for c in b:c['premiseNaturalness']['admissionProvenance']='EVIDENCE_SUPPORTED_UNCLASSIFIED'
    x=select_production(rows,a);y=select_production(rows,b)
    assert x['productionSlate'] and y['productionSlate']
    project=lambda s:[(r['candidateId'],r['rankingScore'],r['productionSlateRank']) for r in s['productionSlate']]
    assert project(x)==project(y)


def test_all_real_rule_constraint_quotes_are_exactly_bound_to_source_fields():
    import re
    seen=0
    for row in SOURCE:
        d=assess(row['candidate'],source_context(row))
        for violation in d.factors['causalCoherence']['violations']:
            assert violation['evidenceRefs']
            for ref in violation['evidenceRefs']:
                match=re.fullmatch(r'beats\[(\d+)\]\.(visibleConsequence|newInformation)',ref['sourceField'])
                assert match and row['raw']['beats'][int(match[1])][match[2]]==ref['sourceText']
                seen+=1
            if violation.get('sourceField'):
                assert any(ref['sourceField']==violation['sourceField'] and ref['sourceText']==violation['sourceText'] for ref in violation['evidenceRefs'])
    assert seen>10


def test_same_function_operand_does_not_license_unrelated_magic_property():
    beat=dict(strategy='Kiko touches the fork.',visibleConsequence='The food turns blue on the fork and becomes inedible.',newInformation='The blue food prevents Kiko from eating food.')
    c,ctx=fixture(changes=dict(primaryObject='fork',everydayGoal='Eat food',normalExpectation='A fork carries food toward the mouth.',impossibleRule='Touching the fork makes the food turn blue and become inedible.',visibleTrigger='Kiko touches the fork and the food turns blue.',whyThisObject='The fork changes the food color.',goalRuleRelationship='The food becomes inedible, preventing eating the food.',frameZeroDescription='Kiko tries to eat food with a fork, but the food is blue.',beats=[deepcopy(beat) for _ in range(5)],finalPayoff=beat['visibleConsequence']))
    d=assess(c,ctx)
    assert d.factors['goalInterference']['supported'] and d.factors['trigger']['supported']
    assert d.factors['objectSpecificity']['functionAnchors']
    assert not d.factors['objectSpecificity']['matchedFunctionOperations']
    assert not d.admitted and not d.factors['functionalAffordanceRelationship']['supported']
