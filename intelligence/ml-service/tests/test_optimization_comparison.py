import json
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.optimization_comparison import assess_comparison

ROW=json.loads((Path(__file__).parent/'fixtures/optimization-61-split.json').read_text())['payload']
def fixture():
    r=ROW['sourceRequest'];c=deepcopy(ROW['attemptDiagnostics']['providerResultForRecovery']['candidates'])
    for value in c:value['review']={'canonicalRuleEvaluation':{'score':85,'grade':'B'}}
    return r['text'],deepcopy(r['context']),c

def test_real_candidates_same_score_minor_changes_keep_original():
    source,context,values=fixture();raw=deepcopy(values)
    result=assess_comparison(source,values,context,85)
    assert result['recommendation']=='KEEP_ORIGINAL' and values==raw
    a,b=result['candidates']
    assert a['textSimilarity']>=.98 and a['classification']=='VALID_MINOR_VARIATION'
    assert b['classification']=='VALID_MINOR_VARIATION' and b['temporalComplexity']=='INCREASED_SHOT_COUNT'
    assert not a['approvalEligible'] and not b['approvalEligible']
    assert all(c['validationStatus']=='SOURCE_TEXT_CONTRACT_PASSED' for c in result['candidates'])

@pytest.mark.parametrize('kind',['missing','duplicate','wrong-story','equivalent'])
def test_invalid_or_equivalent_history_cannot_be_approved(kind):
    source,context,values=fixture()
    if kind=='missing':values.pop()
    if kind=='duplicate':values[1]['prompt']=values[0]['prompt']
    if kind=='wrong-story':values[0]['prompt']=values[0]['prompt'].replace('the sticky notes fly off','the cabinet explodes')
    if kind=='equivalent':values[0]['prompt']=source
    out=assess_comparison(source,values,context,85)
    assert not out['candidates'][0]['approvalEligible']
    assert out['candidates'][0]['classification']==('BASELINE_EQUIVALENT' if kind=='equivalent' else 'STRUCTURALLY_INVALID')
    assert out['actualCandidateCount']==len(values)

def test_material_execution_intervention_has_unknown_benefit_even_at_same_score():
    source,context,values=fixture()
    values[0]['prompt']=values[0]['prompt'].replace('[extreme close-up on', '[static extreme close-up on',1)
    out=assess_comparison(source,values,context,85)
    a=out['candidates'][0]
    assert a['classification']=='VALID_WITH_UNPROVEN_BENEFIT' and a['approvalEligible']
    assert 'unproven' in a['conclusion'] and out['baselineScore']==85


def test_actual_assessment_endpoint_has_no_provider_path():
    source,context,values=fixture()
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('Paid provider forbidden')):
        response=TestClient(app).post('/api/v1/workflow/optimization-assessment',json={'text':source,'context':context,'candidates':values,'baselineScore':85})
    assert response.status_code==200 and response.json()['providerCalls']==0
