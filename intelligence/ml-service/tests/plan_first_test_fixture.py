import json
import re
from pathlib import Path
from copy import deepcopy
from app.workflow.optimization_distinctness import _beats

ROW=json.loads((Path(__file__).parent/'fixtures/optimization-61-split.json').read_text())['payload']
def valid_plan_fixture(source=None,context=None):
    source=source or ROW['sourceRequest']['text'];context=deepcopy(context or ROW['sourceRequest']['context'])
    context['optimizationGenerationContractVersion']='plan-first-v1'
    beats=_beats(source)
    def binding(quote,token,start=0):
        i=quote.index(token,start);return {'quote':token}
    def change(beat,mode,focus,states):
        return {'sourceBeatId':beat['id'],'sourceQuote':beat['sourceQuote'],'framing':'MEDIUM' if mode!='DISTINCT_STATE_HOLDS' else 'WIDE',
                'motion':'STATIC','stagingMode':mode,'focusBindings':focus,'stateSequence':states,'startTime':float(beat['startTime']),'endTime':float(beat['endTime'])}
    first=beats[0]['sourceQuote'];peel=beats[1]['sourceQuote'];multiply=beats[2]['sourceQuote']
    path=re.search(r'multiply from (.+?) as ',multiply);states=[];cursor=path.start(1)
    for state in path[1].split(' to '):
        b=binding(multiply,state,cursor);states.append(b);cursor=multiply.index(state,cursor)+len(state)
    a=change(beats[0],'CAUSE_EFFECT_SAME_FRAME',[binding(first,'the cabinet'),binding(first,'her finger')],[])
    b1=change(beats[1],'ACTION_CONSEQUENCE_PAIR',[binding(peel,'the stuck note'),binding(peel,'one note sticks to each hand')],[])
    b2=change(beats[2],'DISTINCT_STATE_HOLDS',[],states)
    def plan(identity,objective,changes):
        return {'candidateId':identity,'title':'Causal contact staging' if identity=='candidate-a' else 'Explicit escalation exposure',
                'objective':objective,'baselineOpportunity':'Baseline labels do not specify simultaneous target and actual attachment visibility.' if identity=='candidate-a' else 'Baseline multiplication does not explicitly allocate readable holds to each existing state.',
                'proposedVisualConsequence':'Keep intended and actual contact participants in one readable frame; clarity remains a hypothesis.' if identity=='candidate-a' else 'Expose separation and multiplication as distinct existing actions, with ordered state holds in continuous execution.',
                'materialDifference':'Adds source-bound simultaneous causal staging, rather than a closer framing adjective.' if identity=='candidate-a' else 'Adds exact action/consequence pairing and explicit ordered state holds, rather than timestamp labels.',
                'preservedStoryAnchors':deepcopy(context['essentialEvents']),'risksIntroduced':['Compositional density needs visual review.'],
                'risksReducedHypotheses':['Explicit visibility may reduce causal ambiguity.'],'unknowns':['Clarity and generator feasibility require rendered visual evidence.'],
                'evidenceStatus':'HYPOTHESIS_ONLY','changes':changes}
    return source,context,{'plans':[plan('candidate-a','OPENING_CAUSAL_LEGIBILITY',[a]),plan('candidate-b','ESCALATION_EXECUTION_FEASIBILITY',[b1,b2])]}

def source_owned_plan_fixture():
    source,context,full=valid_plan_fixture()
    context['optimizationGenerationInstructionsVersion']='plan-first-owned-source-v3'
    def narrative(plan):
        return {k:v for k,v in plan.items() if k not in ('candidateId','objective','preservedStoryAnchors','changes')}
    def choice(change,kind):
        return {'executionOptionId':f'{kind}:{change["sourceBeatId"]}','framing':change['framing'],'motion':change['motion']}
    a,b=full['plans']
    return source,context,{'openingPlan':{**narrative(a),'openingChange':choice(a['changes'][0],'opening')},
                           'escalationPlan':{**narrative(b),'actionConsequenceChange':choice(b['changes'][0],'action-consequence'),
                                             'progressionChange':choice(b['changes'][1],'progression')}}
