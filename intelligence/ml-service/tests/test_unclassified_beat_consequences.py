"""Presence/quality separation, source binding, and zero-taxonomy-change goldens."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest

from app.workflow import beat_grammar as bg
from app.workflow.beat_consequence_evidence import presence,action_evidence
from app.workflow.canonical_creative_evidence import from_structured
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.concept_ranking import normalize
from app.workflow.structured_sfe_replay import structured_input
from app.workflow.short_concept_generation import ranking_input

ROOT=Path(__file__).parents[3]
DOC=ROOT/'intelligence/docs/beat-grammar-unclassified-consequence-v1'
SOURCE=json.loads((ROOT/'intelligence/docs/canonical-evidence-propagation-v1/audit-only-baseline.json').read_text())['candidates']
BEFORE={r['ideaId']:r for r in json.loads((DOC/'baseline.json').read_text())['candidates']}


def context(row):
    c=row['candidate']
    return from_structured(normalize(ranking_input(c))['evaluationText'],structured_input(row['sourceRow']['rawProviderIdea'],c))


def new_report(row):
    return bg.assess(row['candidate']['structuredBeatPlan'],canonical_creative_evidence=context(row),unclassified_consequence_support=True)


@pytest.mark.parametrize('row',SOURCE,ids=lambda r:r['ideaId'])
def test_all18_presence_before_mode_parity_and_sfe_ranking_fixed(row):
    c=row['candidate'];id=row['ideaId'];ctx=context(row)
    before=bg.assess(c['structuredBeatPlan'],canonical_creative_evidence=ctx)
    assert before==BEFORE[id]['after']['beatGrammar']
    after=new_report(row)
    assert after['beatGrammarQuality'] in ['STRONG','ACCEPTABLE','MECHANICAL','BROKEN']
    assert not any(f['code']=='UNKNOWN_CONSEQUENCE' for f in after['flags'])
    assert len(after['canonicalBeatEvidence'])==5
    assert all(b['strategyPresent'] and b['consequencePresent'] for b in after['canonicalBeatEvidence'])
    evaluated,validation,_=evaluate(c,structured_input(row['sourceRow']['rawProviderIdea'],c))
    assert validation==BEFORE[id]['after']['validation']
    assert evaluated['premiseNaturalness']==BEFORE[id]['after']['naturalness']
    assert after['canonicalCreativeEvidence']==before['canonicalCreativeEvidence']


@pytest.mark.parametrize('id',['raw-013','raw-007','raw-026','raw-027'])
def test_four_diagnostic_goldens(id):
    r=next(r for r in SOURCE if r['ideaId']==id);v=new_report(r)
    assert v['beatGrammarQuality']=='ACCEPTABLE'
    assert any(x['consequenceClassificationStatus']=='CONSEQUENCE_PRESENT_UNCLASSIFIED' for x in v['canonicalBeatEvidence'])
    assert v['bodyStateProgressionScore']==0 and v['spatialProgressionScore']==0
    assert all(not x['bodyStateChangeSupported'] and not x['spatialChangeSupported'] for x in v['canonicalBeatEvidence'])
    assert any(f['code']=='STATIC_SPATIAL_PROGRESSION' for f in v['flags'])
    assert BEFORE[id]['after']['validation']['eligibility']=='ELIGIBLE'


@pytest.mark.parametrize('text,expected',[('', 'MISSING'),('none','MISSING'),('Maybe the wall changes','AMBIGUOUS'),('Unknown','AMBIGUOUS'),('The painted surface turns orange.','PRESENT_UNCLASSIFIED')])
def test_missing_ambiguous_and_explicit_are_distinct(text,expected):
    assert presence(text,None,'CONSEQUENCE')[1]=='CONSEQUENCE_'+expected
    assert presence(text,None,'STRATEGY')[1]=='STRATEGY_'+expected


def test_unclassified_strategy_requires_action_target_evidence():
    assert not action_evidence('Opa gives up','Opa')['supported']
    assert not action_evidence('Opa','Opa')['supported']
    a=action_evidence('Opa pulls the brush slowly, hoping it comes free.','Opa')
    b=action_evidence('Opa pulls the brush quickly, expecting it comes free.','Opa')
    assert a['predicate']==b['predicate'] and a['target']==b['target']
    assert a['supported']


class EvidenceFixture:
    """Metamorphic evidence-only fixture: no generator, no saved new concepts."""
    def __init__(self,base,rows):self.base=base;self.rows=rows
    is_structured=True
    def beat_plan(self,plan,data):return self.base.beat_plan(plan,data)
    @property
    def facts(self):
        facts=self.base.facts;facts['beats']=deepcopy(self.rows);return facts


def projected_rows(repeat=False,information=True,state=True):
    from app.workflow.beat_consequence_evidence import project
    r=next(r for r in SOURCE if r['ideaId']=='raw-013');ctx=context(r);rows=ctx.facts['beats']
    if repeat:
        for b in rows:
            b['strategy']=rows[0]['strategy'];b['visibleConsequence']=rows[0]['visibleConsequence']
            b['newInformation']=rows[0]['newInformation'] if information else ''
            b['supportedStateChange']=state
    else:
        for b in rows:
            b['supportedStateChange']=state
            if not information:b['newInformation']=''
    # Preserve exact objectResponse binding in the fixture projection.
    plan=deepcopy(r['candidate']['structuredBeatPlan'])
    for p,b in zip(plan,rows):p['objectResponse']=b['visibleConsequence']
    fixture=EvidenceFixture(ctx,rows)
    # The real context checks source integrity; this evidence fixture isolates the
    # projector's no-credit rules, without forged public context inputs.
    fixture.beat_plan=lambda p,d:[{**x,'objectResponse':rows[i]['visibleConsequence']} for i,x in enumerate(ctx.beat_plan(r['candidate']['structuredBeatPlan'],d))]
    return project(fixture,plan,bg.load_data(),'Opa'),plan


def test_unclassified_presence_does_not_grant_progression():
    beats,plan=projected_rows(information=False,state=False)
    assert all(b.consequencePresent for b in beats)
    assert all(not b.progressionSupported for b in beats)
    assert all(b.consequenceDiversityKey is None for b in beats if b.consequenceClassification is None)
    report=bg.assess(plan,_beat_evidence=beats)
    assert report['beatGrammarQuality']=='MECHANICAL'


def test_repeated_result_and_information_remain_mechanical():
    beats,plan=projected_rows(repeat=True)
    assert not any(b.stateChangeSupported or b.informationProgressionSupported for b in beats[1:])
    assert bg.assess(plan,_beat_evidence=beats)['beatGrammarQuality']=='MECHANICAL'


def test_new_information_independent_of_consequence_class():
    beats,_=projected_rows(state=False)
    unclassified=[b for b in beats if b.consequenceClassification is None]
    assert unclassified and all(b.informationProgressionSupported and not b.stateChangeSupported for b in unclassified)
    assert all(b.consequenceDiversityKey is None for b in unclassified)


def test_state_changing_unclassified_result_and_payoff():
    r=next(r for r in SOURCE if r['ideaId']=='raw-013');v=new_report(r)
    assert any(b['stateChangeSupported'] for b in v['canonicalBeatEvidence'] if b['consequenceClassificationStatus']=='CONSEQUENCE_PRESENT_UNCLASSIFIED')
    # Unclassified final payoff in another existing source; no taxonomy requirement.
    existing=[new_report(x) for x in SOURCE]
    assert any(v['canonicalBeatEvidence'][-1]['consequenceClassificationStatus']=='CONSEQUENCE_PRESENT_UNCLASSIFIED' for v in existing)


def test_raw013_can_still_fail_when_progression_is_genuinely_removed():
    beats,plan=projected_rows(repeat=True,information=False,state=False)
    assert bg.assess(plan,_beat_evidence=beats)['beatGrammarQuality']=='MECHANICAL'


def test_missing_and_ambiguous_are_blocking_not_unclassified():
    r=next(r for r in SOURCE if r['ideaId']=='raw-013');facts=context(r).beat_evidence(r['candidate']['structuredBeatPlan'],bg.load_data())
    plan=context(r).beat_plan(r['candidate']['structuredBeatPlan'],bg.load_data())
    for status in ['CONSEQUENCE_MISSING','CONSEQUENCE_AMBIGUOUS']:
        data=list(facts);data[0]=facts[0].model_copy(update={'consequenceClassificationStatus':status,'consequencePresent':status.endswith('AMBIGUOUS')})
        report=bg.assess(plan,_beat_evidence=data)
        assert report['beatGrammarQuality']=='BROKEN'
        assert status in {f['code'] for f in report['flags']}


def test_manual_source_no_bonus():
    r=SOURCE[0];c=r['candidate'];data=structured_input(r['sourceRow']['rawProviderIdea'],c);text=normalize(ranking_input(c))['evaluationText']
    a=from_structured(text,data,'MANUAL');b=from_structured(text,data,'SEMANTIC')
    x=bg.assess(c['structuredBeatPlan'],canonical_creative_evidence=a,unclassified_consequence_support=True)
    y=bg.assess(c['structuredBeatPlan'],canonical_creative_evidence=b,unclassified_consequence_support=True)
    x.pop('canonicalCreativeEvidence');y.pop('canonicalCreativeEvidence');assert x==y


def test_explicit_mode_required():
    with pytest.raises(ValueError,match='requires an explicit canonical'):bg.assess([],unclassified_consequence_support=True)


def test_all18_legacy_deterministic_adapter_reports_byte_equal():
    import types
    # Exact pre-task source oracle from the accepted implementation, never imported in runtime.
    source=(DOC/'legacy-beat_grammar.py.txt').read_text()
    module=types.ModuleType('app.workflow.legacy_bg');module.__package__='app.workflow';module.__file__=bg.__file__
    exec(compile(source,str(DOC/'legacy-beat_grammar.py.txt'),'exec'),module.__dict__)
    for r in SOURCE:
        plan=r['candidate']['structuredBeatPlan']
        assert bg.assess(plan)==module.assess(plan)


def test_unresolved_comparisons_are_not_reported_as_duplicate_pairs():
    r=next(r for r in SOURCE if r['ideaId']=='raw-013');ctx=context(r)
    facts=ctx.beat_evidence(r['candidate']['structuredBeatPlan'],bg.load_data())
    plan=ctx.beat_plan(r['candidate']['structuredBeatPlan'],bg.load_data())
    # Leave three supported duplicate attempts, and two entirely unknown ones.
    shared=facts[0].model_copy(update={'strategyDiversityKey':'same-action','consequenceDiversityKey':'same-state'})
    for i in range(3):facts[i]=shared.model_copy(update={'beatNumber':i+1})
    for i in range(3,5):facts[i]=facts[i].model_copy(update={'strategyDiversityKey':None,'consequenceDiversityKey':None})
    for row in plan:row['trigger']='UNCLASSIFIED_TRIGGER'
    report=bg.assess(plan,_beat_evidence=facts)
    unresolved={tuple(p['beats']) for p in report['attemptComparisons'] if p['classification']=='UNRESOLVED_ATTEMPT'}
    assert unresolved
    duplicates=next(f['pairs'] for f in report['flags'] if f['code']=='NEAR_DUPLICATE_ATTEMPTS')
    assert not unresolved.intersection(map(tuple,duplicates))
