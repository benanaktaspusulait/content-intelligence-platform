"""No network: native IDEA role and shared environment direction contracts."""
import json
import pytest
from app.workflow import creative_roles as roles
from app.workflow import start_frame_generation as images

IDEA=dict(title='A New Picnic',concept='Arda saves a place.',firstStaticFrame='Arda beside a prepared empty garden seat.',viewerQuestion='Who needs the large seat?',discovery='A gentle guest arrives.',payoff='They share the space.',productionRisk='Scale continuity')
class Provider:
    calls=[]
    last_usage={'prompt_tokens':10,'completion_tokens':20,'total_tokens':30}
    last_response_metadata={'model':'gpt-6-sol','finishReason':'stop'}
    def __init__(self,**kwargs):pass
    def complete(self,prompt,system='',**kwargs):
        self.calls.append((prompt,system));self.last_raw_response=json.dumps(IDEA);return self.last_raw_response

def test_one_idea_is_not_a_timecoded_story_and_retains_paid_receipt(monkeypatch):
    Provider.calls=[]
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','true')
    monkeypatch.delenv('POMPOM_ISOLATED_ACCEPTANCE',raising=False)
    monkeypatch.setattr(roles,'OpenAIProvider',Provider)
    result=roles.run_paid_role('IDEA','A surprising picnic.',{'characterRecord':{'id':'arda','name':'Arda'}},.1)
    assert len(Provider.calls)==1 and result['result']==IDEA
    assert result['calls']==1 and result['visualInspected'] is False
    assert result['requestedModel']=='gpt-6-sol' and result['usage']['total_tokens']==30
    assert result['actualCostUsd']>0 and result['validationStatus']=='NOT_VALIDATED'
    assert 'not a timecoded story' in Provider.calls[0][1]

def test_unconfigured_model_cannot_be_selected_or_dispatched(monkeypatch):
    Provider.calls=[]
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','true')
    monkeypatch.delenv('POMPOM_ISOLATED_ACCEPTANCE',raising=False)
    monkeypatch.setattr(roles,'OpenAIProvider',Provider)
    with pytest.raises(ValueError,match='configured supported model'):
        roles.run_paid_role('IDEA','A concept',{'storyModel':'invented-model'},.1)
    assert Provider.calls==[]

def test_incomplete_idea_is_rejected_without_a_second_completion():
    class Incomplete(Provider):
        def complete(self,*a,**kw):return '{"title":"Incomplete"}'
    with pytest.raises(ValueError,match='complete concept'):
        roles.perform_role('IDEA','A concept',{},Incomplete(),'configured')

def test_shared_environment_preserves_source_location_and_not_impossible_physics():
    prompt=images._build_image_prompt('Arda outdoors in a garden, saving a place.','Arda','','9:16','CURIOSITY_ADVENTURE',True)
    assert images.SCENE_DIRECTION in prompt
    assert 'preserve its indoor/outdoor location' in prompt
    assert 'do not invent impossible physics' in prompt
    assert 'exact character identity' in prompt
