import json
from copy import deepcopy
import pytest
from optimization_test_fixture import valid_optimization_fixture
from app.workflow.creative_roles import perform_role

class Provider:
    def __init__(self,candidates):self.candidates=candidates;self.system=None
    def complete(self,prompt,system='',**kwargs):self.payload=json.loads(prompt);self.system=system;return json.dumps({'candidates':self.candidates})

def evaluate(candidates,source=None,context=None):
    original,ctx,_=valid_optimization_fixture();p=Provider(candidates)
    return perform_role('PROMPT_OPTIMIZATION',source or original,context or ctx,p,'fixture'),p

def test_two_material_candidates_preserve_all_source_events_and_remain_hypotheses():
    source,ctx,candidates=valid_optimization_fixture();before=deepcopy(ctx)
    result,p=evaluate(candidates)
    assert ctx==before
    for c in result['result']['candidates']:
        assert all(event in c['prompt'] for event in ctx['essentialEvents'])
        d=c['executionDistinctness'];assert d['status']=='MATERIAL_TEXT_EXECUTION_DIFFERENCE'
        assert d['approvedStorySemanticFidelity']=='UNKNOWN' and d['generatorSuccess']=='UNKNOWN'
        for e in d['changes']:
            a,b=e['baselineSourceSpan'];x,y=e['candidateSourceSpan']
            assert source[a:b]==e['baselineQuote'] and c['prompt'][x:y]==e['candidateQuote']
    assert 'first-frame' in p.system and 'Seedance' in p.system
    assert 'protected narrative action stays unchanged' in p.system
    assert p.payload['context']['targetConfiguration']==ctx['targetConfiguration']

@pytest.mark.parametrize('kind',['baseline','identical','camera-paraphrase','commentary','same-execution','story-deviation','early-ending-in-camera','ending','identity','physical-rule','gap','duration','generator','aspect-ratio'])
def test_invalid_revisions_are_rejected_without_relaxing_duplicate_checks(kind):
    source,ctx,c=valid_optimization_fixture()
    if kind=='baseline':c[0]['prompt']=source
    if kind=='identical':c[1]['prompt']=c[0]['prompt']
    if kind=='camera-paraphrase':c[0]['prompt']=source.replace('Content profile: AUTO','Content profile: ABSURD_PHYSICS').replace('[close-up on', '[tight shot on',1)
    if kind=='commentary':c[0]['prompt']=source+'\nImprove curiosity and pacing.'
    if kind=='same-execution':c[1]['prompt']=c[0]['prompt'].replace('extreme close-up','extreme close up')
    if kind=='story-deviation':c[0]['prompt']=c[0]['prompt'].replace('Mimi is overwhelmed by notes','Mimi is overwhelmed by notes and another character arrives')
    if kind=='early-ending-in-camera':c[0]['prompt']=c[0]['prompt'].replace('[extreme close-up on', '[extreme close-up Mimi sneezes on',1)
    if kind=='ending':c[0]['prompt']=c[0]['prompt'].replace('cabinet remains visibly messy','cabinet becomes tidy')
    if kind=='identity':c[0]['prompt']=c[0]['prompt'].replace('established anthropomorphic bunny','established human')
    if kind=='physical-rule':c[0]['prompt']=c[0]['prompt'].replace('doubles the number','triples the number')
    if kind=='gap':c[1]['prompt']=c[1]['prompt'].replace('6-10s:','7-10s:')
    if kind=='duration':c[1]['prompt']=c[1]['prompt'].replace('12-15s:','12-14s:')
    if kind=='generator':c[0]['prompt']=c[0]['prompt'].replace('SEEDANCE_2_0_MINI','OTHER_MODEL')
    if kind=='aspect-ratio':c[0]['prompt']=c[0]['prompt'].replace('9:16','16:9')
    with pytest.raises(ValueError):evaluate(c)

def test_generic_camera_proposals_can_differ_without_rewriting_narrative():
    source,ctx,c=valid_optimization_fixture()
    c[0]['prompt']=source.replace('Content profile: AUTO','Content profile: ABSURD_PHYSICS').replace('[close-up on','[static close-up on',1)
    result,_=evaluate(c)
    assert result['result']['candidates'][0]['executionDistinctness']['changes'][0]['after'][3]=='STATIC'

def test_generic_character_object_and_supported_camera_timing_changes():
    source='Duration: 6s\nCHARACTER\nNori\nTIMED SHOT PLAN\n0-2s: Nori lifts a wooden coin [wide shot] -> coin is visible\n2-4s: Nori flips the coin [medium shot] -> coin turns\n4-6s: Nori catches the coin [close-up] -> coin is held\nAUDIO\nQuiet music'
    c=[dict(candidateId='candidate-a',title='Clarity',hypothesis='Closer opening framing.',prompt=source.replace('[wide shot]','[close-up]',1)),dict(candidateId='candidate-b',title='Pacing',hypothesis='More time on the flip.',prompt=source.replace('2-4s:','2-5s:').replace('4-6s:','5-6s:'))]
    ctx={'essentialEvents':['Nori lifts a wooden coin','Nori flips the coin','Nori catches the coin'],'targetConfiguration':{'duration':6},'approvedStoryText':'Nori lifts, flips and catches a wooden coin.'}
    result,_=evaluate(c,source,ctx)
    assert result['result']['candidates'][0]['optimizationObjective']!=result['result']['candidates'][1]['optimizationObjective']

def test_actual_b2_response_is_nonmaterial_before_generic_fidelity_classification():
    from pathlib import Path
    fixture=json.loads((Path(__file__).parent/'fixtures/optimization-b2-rejected.json').read_text())
    source=fixture['request']['text'];ctx=fixture['request']['context'];values=deepcopy(fixture['providerResult']['candidates'])
    with pytest.raises(ValueError,match='candidate-a: materially unchanged execution') as failure:evaluate(values,source,ctx)
    from app.workflow.creative_roles import _optimization_validation_category
    assert _optimization_validation_category(failure.value)=='CANDIDATE_STRUCTURE_INVALID'
    # The second candidate has a real timing change but loses source-linked escalation coverage.
    _,_,valid=valid_optimization_fixture();values[0]=valid[0]
    # Isolate B's source-coverage failure after correcting its independent stale settings label in the fixture only.
    values[1]['prompt']=values[1]['prompt'].replace('Content profile: AUTO','Content profile: ABSURD_PHYSICS')
    with pytest.raises(ValueError,match='candidate-b: source-plan beat') as failure:evaluate(values,source,ctx)
    assert _optimization_validation_category(failure.value)=='SOURCE_PLAN_VALIDATION_FAILED'

def test_provider_receives_concrete_baseline_camera_and_timing_decisions():
    _,_,values=valid_optimization_fixture();result,provider=evaluate(values)
    baseline=provider.payload['context']['baselineExecution']
    assert baseline[0]['framing']=='CLOSE' and baseline[0]['startTime']==0 and baseline[0]['endTime']==2
    assert baseline[0]['cameraMotion']=='UNSPECIFIED'
    assert 'Do not propose the same existing shot' in provider.system
