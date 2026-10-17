import json
from copy import deepcopy
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.story_experiment import validate, preview, execute, sha
from story_experiment_fixture import inputs, alternatives


@pytest.fixture(autouse=True)
def profiles(monkeypatch):
    monkeypatch.delenv('WORKFLOW_STORY_PILOT_MODEL_POLICY', raising=False)
    for key,value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_STORY_MODEL':'deepseek-chat',
                      'WORKFLOW_STORY_INPUT_USD_PER_MILLION':'.3','WORKFLOW_STORY_OUTPUT_USD_PER_MILLION':'1.2',
                      'WORKFLOW_STORY_REVIEW_MODEL':'gpt-4o-mini-2024-07-18',
                      'WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION':'.15','WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION':'.6'}.items():
        monkeypatch.setenv(key,value)


@pytest.mark.parametrize('count',[0,1,2,3])
def test_exact_count_scoped_to_pilot(count):
    text,context=inputs();values=alternatives(text,context['storyExperiment'])
    supplied=(values+[dict(values[0],candidateId='candidate-3')])[:count]
    gate=validate(text,context,{'alternatives':supplied})
    assert gate['eligible'] is (count==2)
    assert gate.get('semanticFidelity') != 'PASS'


@pytest.mark.parametrize('defect',['id','same','near','short','fields','Rex','Ada','unknown','unmapped','proposal','negation'])
def test_invalid_unknown_and_proposed_protected_changes_are_not_review_eligible(defect):
    text,context=inputs();values=alternatives(text,context['storyExperiment']);bad=values[1]
    if defect=='id':bad['candidateId']=values[0]['candidateId']
    if defect=='same':bad['text']=values[0]['text']
    if defect=='near':bad['text']=values[0]['text'].replace('careful','gentle')
    if defect=='short':bad['text']='Short.'
    if defect=='fields':bad['productionRisks']=42
    if defect in ['Rex','Ada']:bad['text']=('Rex the dragon flies to the moon. Then he sleeps. ' if defect=='Rex' else 'Ada the chef cooks soup. Then she goes home. ')*5
    if defect=='unknown':bad['sourceContract']['status']='UNKNOWN'
    if defect=='unmapped':bad['sourceContract']['bindings']=[]
    if defect=='negation':bad['text']=bad['text'].replace(context['storyExperiment']['protectedAnchors'][-1]['quote'],'Never '+context['storyExperiment']['protectedAnchors'][-1]['quote'])
    if defect=='proposal':bad['sourceContract'].update(status='PROTECTED_CHANGE_PROPOSAL',protectedChanges=[{'anchorId':'ending','proposedChange':'A different ending','justification':'Owner consideration only'}])
    gate=validate(text,context,{'alternatives':values})
    assert not gate['eligible']
    if defect=='proposal':assert gate['candidates'][1]['status']=='PROTECTED_CHANGE_PROPOSAL'


def test_variation_preserves_only_bound_facts_and_keeps_semantics_unknown():
    text,context=inputs();values=alternatives(text,context['storyExperiment'])
    assert values[0]['text']!=values[1]['text'] and all(c['text']!=text for c in values)
    gate=validate(text,context,{'alternatives':values})
    assert gate['eligible'] and all(c['status']=='SOURCE_COMPLIANT' for c in gate['candidates'])
    assert gate['semanticFidelity']=='UNKNOWN_REQUIRES_INDEPENDENT_REVIEW'


def test_jsonb_object_key_reordering_cannot_change_effective_request_fingerprint():
    text,context=inputs()
    def reorder(value):
        if isinstance(value,dict):return {k:reorder(value[k]) for k in reversed(list(value))}
        if isinstance(value,list):return [reorder(x) for x in value]
        return value
    assert preview('STORY',text,context)==preview('STORY',text,reorder(context))


@pytest.mark.parametrize('change',['instruction','model','price','source','budget','fixture'])
def test_dispatch_mismatch_fails_before_provider_construction(monkeypatch,change):
    text,context=inputs();authorized=preview('STORY',text,context);authorized['maxCostUsd']=.1
    context['storyExperimentDispatch']=authorized
    if change=='instruction':authorized['systemSha256']='stale'
    if change=='model':monkeypatch.setenv('WORKFLOW_STORY_MODEL','different-model')
    if change=='price':monkeypatch.setenv('WORKFLOW_STORY_INPUT_USD_PER_MILLION','3')
    if change=='source':context['storyExperiment']['sourceStorySha256']='stale'
    if change=='fixture':monkeypatch.setenv('POMPOM_ISOLATED_ACCEPTANCE','true')
    with patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('Provider must not be constructed')):
        with pytest.raises(ValueError):execute('STORY',text,context,.00001 if change=='budget' else .1)


@pytest.mark.parametrize('mode',['valid','malformed','missing-usage','truncated','timeout','over-budget','one'])
def test_every_post_dispatch_outcome_returns_authentic_raw_usage_and_billing(mode):
    text,context=inputs();auth=preview('STORY',text,context);auth['maxCostUsd']=.1;context['storyExperimentDispatch']=auth
    class Adapter:
        def complete(self,*args,**kwargs):
            if mode=='timeout':raise TimeoutError('Offline timeout')
            self.last_usage=None if mode=='missing-usage' else {'prompt_tokens':1000000 if mode=='over-budget' else 100,'completion_tokens':200}
            self.last_response_metadata={'model':'deepseek-chat','finishReason':'length' if mode=='truncated' else 'stop'}
            values=alternatives(text,context['storyExperiment'])
            self.last_raw_response='{bad' if mode=='malformed' else json.dumps({'alternatives':values[:1] if mode=='one' else values})
            return self.last_raw_response
    with patch('app.workflow.deepseek.DeepSeekTextProvider',return_value=Adapter()):
        result=execute('STORY',text,context,.1)
    assert result['retrySafe'] is False
    assert (result['processingStatus']=='CANDIDATES_ACCEPTED') is (mode=='valid')
    if mode=='timeout':assert result['billingStatus']=='USAGE_UNKNOWN' and result['rawProviderResponse'] is None
    else:
        assert result['rawProviderResponse'] and result['responseSha256']==sha(result['rawProviderResponse'])
        assert (result['billingStatus']=='KNOWN_INCURRED') is (mode!='missing-usage')
        if mode=='malformed':assert result['actualCostUsd']==pytest.approx(.00027)


def test_unsigned_pilot_http_request_is_denied_without_transport():
    text,context=inputs()
    with patch('app.workflow.creative_roles.run_paid_role',side_effect=AssertionError('No dispatch')):
        result=TestClient(app).post('/api/v1/workflow/creative-role',json={'role':'STORY','text':text,'context':context,'maxCostUsd':.1})
    assert result.status_code==403


@pytest.mark.parametrize('returned',['deepseek-chat','deepseek-flash','unknown-model',None,''])
def test_exact_identity_billing_and_raw_preservation(returned):
    text,context=inputs();auth=preview('STORY',text,context);auth['maxCostUsd']=.1;context['storyExperimentDispatch']=auth
    class Adapter:
        def complete(self,*args,**kwargs):
            self.last_usage={'prompt_tokens':100,'completion_tokens':200}
            self.last_response_metadata={'model':returned,'finishReason':'stop'}
            self.last_raw_response=json.dumps({'alternatives':alternatives(text,context['storyExperiment'])})
            return self.last_raw_response
    with patch('app.workflow.deepseek.DeepSeekTextProvider',return_value=Adapter()):
        result=execute('STORY',text,context,.1)
    assert result['rawProviderResponse'] and result['configuredRateCostUsd']==pytest.approx(.00027)
    assert result['modelIdentity']['actualReturnedModel']==returned
    assert result['modelIdentity']['aliasApplied'] is False
    if returned=='deepseek-chat':assert result['processingStatus']=='CANDIDATES_ACCEPTED'
    else:
        assert result['processingStatus']=='LOCALLY_REJECTED'
        assert result['actualCostUsd'] is None and result['billingStatus']=='MODEL_IDENTITY_UNVERIFIED'


def test_direct_flash_requires_explicit_profile_and_exact_fresh_grant(monkeypatch):
    text,context=inputs();old=preview('STORY',text,context);old['maxCostUsd']=.1
    monkeypatch.setenv('WORKFLOW_STORY_MODEL','deepseek-flash')
    with pytest.raises(ValueError):preview('STORY',text,context)
    monkeypatch.setenv('WORKFLOW_STORY_PILOT_MODEL_POLICY','DIRECT_FLASH_TEXT_V1')
    current=preview('STORY',text,context)
    assert current['modelIdentityPolicy']['requestParameters']=={'thinking':{'type':'disabled'}}
    assert current['modelIdentityPolicy']['aliasPolicy']=='NONE'
    context['storyExperimentDispatch']=old
    with patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('No constructor')):
        with pytest.raises(ValueError):execute('STORY',text,context,.1)


@pytest.mark.parametrize('offset',['candidate','source'])
def test_supplied_offsets_cannot_disagree_with_exact_excerpt(offset):
    text,context=inputs();values=alternatives(text,context['storyExperiment']);binding=values[1]['sourceContract']['bindings'][0]
    binding.update({offset+'Start':1,offset+'End':3})
    gate=validate(text,context,{'alternatives':values})
    assert not gate['eligible'] and gate['candidates'][1]['status']=='SOURCE_VIOLATION'
    assert any('offsets' in e for e in gate['candidates'][1]['errors'])


def test_equivalent_text_form_does_not_mean_semantic_pass():
    text,context=inputs();values=alternatives(text,context['storyExperiment']);a=context['storyExperiment']['protectedAnchors'][2]
    quote=a['quote'].upper()
    for c in values:
        c['text']=c['text'].replace(a['quote'],quote)
        next(b for b in c['sourceContract']['bindings'] if b['anchorId']==a['id'])['candidateQuote']=quote
    gate=validate(text,context,{'alternatives':values})
    assert gate['eligible'] and gate['semanticFidelity']=='UNKNOWN_REQUIRES_INDEPENDENT_REVIEW'
    # Synonym or pronoun interpretation is not established deterministically.
    values[1]['text']=values[1]['text'].replace(quote,'each hand-off makes more paper')
    next(b for b in values[1]['sourceContract']['bindings'] if b['anchorId']==a['id'])['candidateQuote']='each hand-off makes more paper'
    assert not validate(text,context,{'alternatives':values})['eligible']


def test_story_instructions_explain_own_exact_excerpts_and_creative_scope():
    from app.workflow.creative_roles import preview_story_request
    text,context=inputs();system=preview_story_request('STORY',text,context)['system']
    for required in ('exact contiguous substrings','sourceQuote exactly','Metadata never overrides','all other narrative wording','new multiplication triggers'):
        assert required in system


def test_saved_authentic_response_replay_does_not_repair_or_change_evidence():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2];folder=root/'docs/first-real-story-evolution-evidence'
    raw=(folder/'raw-model-response.txt').read_text()
    assert sha(raw)=='34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1'
    saved=json.loads((folder/'provider-receipt.json').read_text());source=json.loads((root/'docs/REAL_STORY_EXPERIMENT_REPAIRED_MANIFEST.json').read_text())['sourceScope']
    text=source['sourceStory'];_,context=inputs();context['storyExperiment'].update(sourceScopeSha256=source['sourceScopeSha256'],protectedAnchors=source['protectedAnchors'])
    gate=validate(text,context,json.loads(raw));old=json.loads((folder/'offline-source-gate.json').read_text())['result']
    assert gate==old and all(c['status']=='UNKNOWN' and not c['eligible'] for c in gate['candidates'])
    auth=preview('STORY',text,context);auth['maxCostUsd']=.1;context['storyExperimentDispatch']=auth
    class SavedAdapter:
        def complete(self,*args,**kwargs):
            self.last_raw_response=raw;self.last_usage=saved['usage'];self.last_response_metadata=saved['providerResponseMetadata'];self.last_provider_response=saved['providerApiResponse']
            return raw
    with patch('app.workflow.deepseek.DeepSeekTextProvider',return_value=SavedAdapter()):
        result=execute('STORY',text,context,.1)
    assert result['rawProviderResponse']==raw and result['providerApiResponse']==saved['providerApiResponse']
    assert result['modelIdentity']['actualReturnedModel']=='deepseek-flash' and not result['modelIdentity']['verified']
    assert result['billingStatus']=='MODEL_IDENTITY_UNVERIFIED' and result['actualCostUsd'] is None
    assert result['configuredRateCostUsd']==pytest.approx(.0028389)
    assert (folder/'raw-model-response.txt').read_text()==raw


def test_flash_transport_sends_explicit_non_thinking_without_model_rewrite(monkeypatch):
    from unittest.mock import MagicMock
    from app.workflow.deepseek import DeepSeekTextProvider
    monkeypatch.setenv('DEEPSEEK_API_KEY','test-only-not-a-real-key')
    with patch('app.workflow.deepseek.OpenAI') as sdk:
        response=MagicMock();response.model='deepseek-flash';response.choices[0].message.content='{}'
        sdk.return_value.chat.completions.create.return_value=response
        provider=DeepSeekTextProvider('deepseek-flash');provider.request_parameters={'thinking':{'type':'disabled'}}
        provider.complete('{}','system',temperature=0)
        sent=sdk.return_value.chat.completions.create.call_args.kwargs
        assert sent['model']=='deepseek-flash' and sent['extra_body']=={'thinking':{'type':'disabled'}}
        assert sent['max_tokens']==4000 and sdk.call_args.kwargs['max_retries']==0


def test_no_authorization_cannot_construct_either_provider():
    text,context=inputs()
    with patch('app.workflow.deepseek.DeepSeekTextProvider',side_effect=AssertionError('No provider')), patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('No provider')):
        with pytest.raises(ValueError):execute('STORY',text,context,.1)
        with pytest.raises(ValueError):execute('STORY_REVIEW',text,context,.1)


def test_offset_violation_cannot_be_downgraded_by_later_unknown_binding():
    text,context=inputs();values=alternatives(text,context['storyExperiment']);bindings=values[1]['sourceContract']['bindings']
    bindings[0].update(candidateStart=0,candidateEnd=1)
    bindings[2]['candidateQuote']=''
    gate=validate(text,context,{'alternatives':values})
    assert gate['candidates'][1]['status']=='SOURCE_VIOLATION' and not gate['eligible']
