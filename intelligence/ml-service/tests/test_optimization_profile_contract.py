import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.creative_roles import perform_role
from app.workflow.optimization_profile_contract import ProfileContractError, normalize_candidate_profiles
from optimization_test_fixture import valid_optimization_fixture

FIXTURE=json.loads((Path(__file__).parent/'fixtures/optimization-c7-profile.json').read_text())
class SavedProvider:
    def __init__(self,values):self.values=values
    def complete(self,prompt,system='',**kwargs):
        self.payload=json.loads(prompt);self.system=system
        return json.dumps({'candidates':self.values})

def evaluate(values=None,source=None,context=None):
    text,ctx,valid=valid_optimization_fixture()
    provider=SavedProvider(values or valid)
    result=perform_role('PROMPT_OPTIMIZATION',source or text,context or ctx,provider,'mock')
    return result,provider

@pytest.mark.parametrize('historical', ['AUTO','EDUCATIONAL','CURIOSITY_ADVENTURE'])
def test_authoritative_target_does_not_mutate_baseline(historical):
    source,ctx,values=valid_optimization_fixture();source=source.replace('Content profile: AUTO','Content profile: '+historical)
    result,p=evaluate(values,source,ctx)
    assert p.payload['baselinePromptText']==source
    assert p.payload['profileOwnership']['baselinePromptHistoricalProfile']==historical
    assert p.payload['profileOwnership']['targetContentProfile']=='ABSURD_PHYSICS'
    assert 'historical only' in p.system
    assert all(c['sourcePlan']['contentProfile']=='ABSURD_PHYSICS' for c in result['result']['candidates'])
    assert all(c['executionDistinctness']['approvedStorySemanticFidelity']=='UNKNOWN' for c in result['result']['candidates'])

@pytest.mark.parametrize('echo',['AUTO','absurd physics','ABSURD-PHYSICS'])
def test_metadata_mapping_retains_raw_echo_without_false_semantic_approval(echo):
    source,ctx,values=valid_optimization_fixture()
    for c in values:
        c['prompt']=c['prompt'].replace('Content profile: ABSURD_PHYSICS','Content profile: '+echo)
        c['sourcePlan']={'contentProfile':echo}
    raw=deepcopy(values);result,p=evaluate(values)
    assert result['rawProviderResult']['candidates']==raw
    for c in result['result']['candidates']:
        assert c['sourcePlan']['contentProfile']=='ABSURD_PHYSICS'
        assert c['profileValidation']['rawProviderPrompt']==raw[0 if c['candidateId']=='candidate-a' else 1]['prompt']
        assert c['profileValidation']['semanticFidelity']=='UNKNOWN'
        assert c['profileValidation']['status']==('PROFILE_METADATA_MISMATCH' if echo=='AUTO' else 'PROFILE_ALIGNED')

@pytest.mark.parametrize('location',['prompt','plan-directive','plan-instructions'])
@pytest.mark.parametrize('wrong_profile',['AUTO','EDUCATIONAL'])
def test_material_wrong_profile_is_rejected(location,wrong_profile):
    _,_,values=valid_optimization_fixture()
    if location=='prompt':values[0]['prompt']=values[0]['prompt'].replace('VISUAL STYLE','VISUAL STYLE\nTarget content profile: '+wrong_profile+'.')
    if location=='plan-directive':values[0]['sourcePlan']={'creativeProfile':wrong_profile}
    if location=='plan-instructions':values[0]['sourcePlan']={'creativeInstructions':'Optimize for '+wrong_profile}
    with pytest.raises(ProfileContractError) as error:evaluate(values)
    assert error.value.profile_validation['status']=='MATERIAL_CREATIVE_PROFILE_CONFLICT'

@pytest.mark.parametrize('bad',['baseline','duplicate'])
def test_metadata_mapping_does_not_make_duplicates_valid(bad):
    source,ctx,values=valid_optimization_fixture()
    if bad=='baseline':values[0]['prompt']=source
    else:values[1]['prompt']=values[0]['prompt']
    with pytest.raises(ValueError):evaluate(values)


def test_real_c7_response_profile_is_mapped_but_invalid_source_coverage_remains_rejected():
    p=FIXTURE['attempt']['payload'];request=p['sourceRequest'];raw=p['attemptDiagnostics']['providerResultForRecovery']
    provider=SavedProvider(raw['candidates'])
    with pytest.raises(ValueError,match='beat 1 narrative/staging/consequence'):
        perform_role('PROMPT_OPTIMIZATION',request['text'],request['context'],provider,'saved-response')
    assert provider.last_role_result==raw
    mapped=deepcopy(raw['candidates']);normalize_candidate_profiles(request['text'],mapped,request['context'])
    assert all(c['profileValidation']['status']=='PROFILE_METADATA_MISMATCH' for c in mapped)
    assert all(c['sourcePlan']['contentProfile']=='ABSURD_PHYSICS' for c in mapped)
    isolated=deepcopy(raw['candidates'])
    isolated[0]['prompt']=request['text'].replace('[close-up on','[extreme close-up on',1)
    with pytest.raises(ValueError,match='candidate-b: source-plan event coverage differs'):
        perform_role('PROMPT_OPTIMIZATION',request['text'],request['context'],SavedProvider(isolated),'mock-isolation')


def test_actual_local_recovery_api_cannot_create_provider_or_dispatch():
    source,ctx,values=valid_optimization_fixture()
    for c in values:c['prompt']=c['prompt'].replace('Content profile: ABSURD_PHYSICS','Content profile: AUTO')
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('Paid provider forbidden')):
        response=TestClient(app).post('/api/v1/workflow/optimization-recovery',json={'text':source,'context':ctx,'providerResult':{'candidates':values},'diagnostics':{'model':'saved-model'}})
    assert response.status_code==200,response.text
    assert response.json()['calls']==0
    assert len(response.json()['result']['candidates'])==2
