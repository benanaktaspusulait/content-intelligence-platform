import json
from pathlib import Path
from copy import deepcopy
import pytest
from app.workflow.creative_roles import perform_role

ROW=json.loads((Path(__file__).parent/'fixtures/optimization-61-split.json').read_text())['payload']
class SavedProvider:
    def __init__(self,result):self.result=result
    def complete(self,*args,**kwargs):return json.dumps(self.result)

def validate(result):
    request=ROW['sourceRequest']
    return perform_role('PROMPT_OPTIMIZATION',request['text'],request['context'],SavedProvider(result),'saved-response')

def test_actual_paid_response_preserves_five_events_across_six_shots():
    raw=deepcopy(ROW['attemptDiagnostics']['providerResultForRecovery'])
    result=validate(raw)
    assert result['rawProviderResult']==raw
    coverage=result['result']['candidates'][1]['sourceEventCoverage']
    assert coverage['sourceEventCount']==5 and coverage['candidateShotCount']==6
    assert coverage['mappings'][2]['method']=='EXACT_TEXT_PROGRESSION_EDGES'
    assert coverage['semanticFidelity']=='UNKNOWN'

@pytest.mark.parametrize('mutation',['missing-stage','wrong-number','wrong-consequence','wrong-mechanic','reorder','gap','duplicate'])
def test_split_shots_do_not_bypass_source_or_execution_validation(mutation):
    raw=deepcopy(ROW['attemptDiagnostics']['providerResultForRecovery']);b=raw['candidates'][1]
    if mutation=='missing-stage':b['prompt']=b['prompt'].replace('from four to eight','from four to sixteen')
    if mutation=='wrong-number':b['prompt']=b['prompt'].replace('from two to four','from two to six')
    if mutation=='wrong-consequence':b['prompt']=b['prompt'].replace('Mimi is overwhelmed by notes','Mimi destroys the cabinet',1)
    if mutation=='wrong-mechanic':b['prompt']=b['prompt'].replace('each pull doubles','each pull halves',1)
    if mutation=='reorder':b['prompt']=b['prompt'].replace('from two to four','from four to eight',1)
    if mutation=='gap':b['prompt']=b['prompt'].replace('8-10s:','9-10s:')
    if mutation=='duplicate':b['prompt']=raw['candidates'][0]['prompt']
    with pytest.raises(ValueError):validate(raw)
