"""Structured mock decisions verify authoring contracts, never real-model creativity."""
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import pytest
from test_creative_reconstruction_v2 import fixture, plan, response, MockProvider, canonical_review
from app.workflow.creative_reconstruction import compile_reconstruction, perform_reconstruction, request_payload, response_format, assess_candidate
from app.workflow.model_authored_execution import AUTHORING_VERSION


def inputs():
    f=fixture();f['context']['optimizationGenerationInstructionsVersion']=AUTHORING_VERSION
    return f


def contact():
    p=plan();i=p['interventions'][0]
    i.update(authorship='MODEL_AUTHORED',fallbackReason=None,production={
        'spatialRelationships':[{'subjectRef':'beat_01.expectedSurface','relation':'BEHIND','objectRef':'beat_01.actualSurface',
            'instruction':'Position {beat_01.expectedSurface} behind {beat_01.actualSurface}, offset to the right so the destination remains visible beside the fingertip.'}],
        'choreography':{'sourceActionRef':'beat_01.action',
            'instruction':'Carry the existing reach diagonally across the lower foreground toward the visible cabinet surface, with the sticky edge facing the viewer.',
            'sourceConsequenceRef':'beat_01.consequence',
            'consequencePresentation':'Keep the cabinet destination visibly clear as the note clings to the finger; leave a narrow visible gap between that finger and the cabinet.'},
        'stateProgression':[],
        'temporalPresentation':'Follow the reach through wrong-surface contact in the existing opening window, allowing the destination and the resulting attachment to be read in the same view.',
        'cameraComposition':'Use a locked wide composition with the fingertip in the lower foreground and the cabinet destination in the upper right; retain the note edge in view.',
        'generatorConstraints':['Maintain the existing bunny identity and continuous finger-to-note contact; avoid overlapping the free hand with the contact edge.']})
    return p


def progression():
    p=plan('candidate-b','COUNTABLE_STATE_PATH:beat_03','COUNTABLE_STATE_PATH','LATERAL');i=p['interventions'][0]
    i.update(authorship='MODEL_AUTHORED',fallbackReason=None,production={
        'spatialRelationships':[],
        'choreography':{'sourceActionRef':'beat_03.action',
            'instruction':'Keep the established pulling motion continuous while the growing notes occupy a widening area across the body silhouette.',
            'sourceConsequenceRef':'beat_03.consequence',
            'consequencePresentation':'Show the existing progressive coverage of arms, legs and face after each count transition without losing the edges of the growing note groups.'},
        'stateProgression':[
            {'sourceStateRef':'beat_03.state.0','placementInstruction':'Present {beat_03.state.0} notes as a separated horizontal pair beside the arms.',
             'transitionPresentation':'Keep both outer note edges visible during the established pull that leads into the next source count.'},
            {'sourceStateRef':'beat_03.state.1','placementInstruction':'Present {beat_03.state.1} notes as two vertical pairs, offset left and right across the body silhouette.',
             'transitionPresentation':'Carry the existing pull continuously across the change, retaining the separated pairs before their next multiplication.'},
            {'sourceStateRef':'beat_03.state.2','placementInstruction':'Present {beat_03.state.2} notes in two horizontal rows of four with gaps, following the existing coverage of arms, legs and face.',
             'transitionPresentation':'Let the established body coverage follow the final source count while retaining the group boundaries in the same view.'}],
        'temporalPresentation':'Use the original five-to-ten-second beat window for the existing pull sequence, with continuous transitions and no extra attempt or invented hold.',
        'cameraComposition':'Keep a locked wide view containing the arms, legs and face throughout the existing escalation; preserve group positions through the pull.',
        'generatorConstraints':['Preserve the source doubling rule and existing count order; do not add a new pull or conceal a multiplication behind an edit.']})
    return p


def execute(plans):
    f=inputs();provider=MockProvider(response(plans));result=perform_reconstruction(f['text'],f['context'],provider,'mock-only')
    return f,provider,result


def test_new_wire_contract_includes_authoring_but_no_precompiled_winner():
    f=inputs();payload=request_payload(f['text'],f['context']);schema=response_format(f['context'])['json_schema']['schema']
    assert 'AuthoredProduction' in schema['$defs']
    assert payload['sourceReferenceCatalog']['beat_01.actualSurface']['quote']=='her finger'
    for ref in payload['sourceReferenceCatalog'].values():
        a,z=ref['sourceSpan'];assert f['text'][a:z]==ref['quote']
    assert 'lower foreground' not in json.dumps(payload)
    assert 'sourceReferenceCatalog' not in request_payload(f['text'],fixture()['context'])


def test_model_authored_contact_and_state_path_compile_with_exact_attribution():
    a=contact();a['interventions'].extend(progression()['interventions'])
    f,provider,result=execute([a,progression()]);assert provider.calls==1
    assert len(result['result']['candidates'])==2, result['result']['rejectedProposals']
    candidate=result['result']['candidates'][0]
    assert 'locked wide composition' in candidate['prompt']
    assert 'Stage the cabinet and her finger on' not in candidate['prompt']
    assert 'locked-off medium shot;' not in candidate['prompt']
    assert {x['beatId'] for x in candidate['creativeAssessment']['changeContract']}=={'beat_01','beat_03'}
    for beat in candidate['productionProvenance']['beats']:
        for instruction in beat['instructions']:
            assert instruction['author']=='MODEL_AUTHORED'
            a,z=instruction['candidateSpan'];assert candidate['prompt'][a:z]==instruction['text']
            for field in instruction['fields']:
                a,z=field['candidateSpan'];assert candidate['prompt'][a:z]==field['compiledText']
                expected=field['rawText']
                for ref in field['referenceSubstitutions']:
                    expected=expected.replace('{'+ref['referenceId']+'}',ref['source']['quote'])
                assert expected==field['compiledText']
    for mapping in candidate['sourceEventCoverage']['mappings']:
        if mapping['baselineBeatId'] not in {'beat_01','beat_03'}:assert mapping['baselineQuote']==mapping['candidateQuote']
    segments=candidate['productionProvenance']['segments']
    assert ''.join(s['text'] for s in segments)==candidate['prompt']
    assert segments[0]['candidateSpan'][0]==0 and segments[-1]['candidateSpan'][1]==len(candidate['prompt'])
    for left,right in zip(segments,segments[1:]):assert left['candidateSpan'][1]==right['candidateSpan'][0]
    for segment in segments:
        if 'sourceSpan' in segment:
            a,z=segment['sourceSpan'];assert f['text'][a:z]==segment['text']
    assert candidate['creativeAssessment']['semanticStoryFidelity']=='UNKNOWN'


@pytest.mark.parametrize('defect',['third-attempt','ending','wrong-beat','unknown-ref','count','reorder','named-character','physical-rule'])
def test_known_story_deviations_rejected_without_silent_template_fallback(defect):
    p=progression() if defect in {'count','reorder'} else contact();prod=p['interventions'][0]['production']
    if defect=='third-attempt':prod['choreography']['instruction']='Perform a third pull to increase the number of notes before the ending.'
    if defect=='ending':prod['choreography']['instruction']='Remove the mirror event and replace the ending with a clean cabinet.'
    if defect=='wrong-beat':prod['choreography']['sourceActionRef']='beat_05.action'
    if defect=='unknown-ref':prod['choreography']['instruction']='Keep {invented.prop} visible beside the fingertip throughout the existing reach.'
    if defect=='count':prod['stateProgression'][0]['placementInstruction']='Present three notes as a separated horizontal pair beside the arms.'
    if defect=='reorder':prod['stateProgression'].reverse()
    if defect=='named-character':prod['choreography']['instruction']='Bobo reaches alongside the existing finger and takes the sticky note away.'
    if defect=='physical-rule':prod['choreography']['instruction']='Let the sticky notes triple during the existing reach toward the cabinet.'
    _,provider,result=execute([p]);assert provider.calls==1
    assert not result['result']['candidates']
    assert result['result']['rejectedProposals'][0]['classification']=='STORY_FIDELITY_FAILED'


@pytest.mark.parametrize('kind',['camera','repeated-state','baseline-relation'])
def test_verbose_cosmetic_variations_are_not_material(kind):
    p=progression() if kind=='repeated-state' else contact();i=p['interventions'][0]
    if kind=='camera':i['operation']='CAMERA_LABEL'
    if kind=='repeated-state':
        for s in i['production']['stateProgression']:
            s['placementInstruction']='Keep the notes in the same horizontal row with an attractive, clear, vivid, visually legible arrangement.'
    if kind=='baseline-relation':
        r=i['production']['spatialRelationships'][0];r['relation']='IN_FRONT_OF'
        r['instruction']='Keep {beat_01.actualSurface} in front of {beat_01.expectedSurface} with very clear and beautifully visible staging.'
    _,_,result=execute([p]);assert not result['result']['candidates']
    assert result['result']['rejectedProposals'][0]['classification']=='VALID_BUT_EQUIVALENT'


@pytest.mark.parametrize('kind',['moving-camera','occluded-transition','contradictory-camera'])
def test_new_execution_risks_detected(kind):
    p=contact();i=p['interventions'][0]
    if kind=='moving-camera':i['camera']='TRACK'
    if kind=='occluded-transition':i['production']['choreography']['instruction']='Hide the contact transition behind the free hand during the existing reach.'
    if kind=='contradictory-camera':i['production']['cameraComposition']='Use a tracking camera following the moving finger across the cabinet destination.'
    _,_,result=execute([p]);assert not result['result']['candidates']
    assert result['result']['rejectedProposals'][0]['classification']=='REGRESSION'


def test_explicit_template_fallback_is_server_attributed_and_not_model_authorship():
    p=contact();i=p['interventions'][0];i.update(authorship='BOUNDED_TEMPLATE_FALLBACK',production=None,fallbackReason='The bounded contact-plane treatment is sufficient for this limited source opportunity.')
    _,_,result=execute([p]);c=result['result']['candidates'][0]
    assert c['productionProvenance']['beats'][0]['instructions'][0]['author']=='SERVER_TEMPLATE'
    assert c['productionProvenance']['beats'][0]['instructions'][0]['fields']==[]


def test_complete_mock_provider_source_canonical_critic_and_comparison_gates():
    p=contact();p['interventions']+=progression()['interventions']
    f,_,result=execute([p]);c=result['result']['candidates'][0]
    with patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No real provider calls')):
        c['review']=canonical_review(f,c)
    evidence=assess_candidate(f['text'],c,f['context'],f['baselineScore'])
    assert c['review']['canonicalRuleEvaluation']['status']=='EVALUATED'
    assert evidence['classification']=='PLAUSIBLE_IMPROVEMENT_UNVERIFIED', evidence
    assert evidence['creativeAssessment']['provenBetter'] is False
    assert c['review']['canonicalRuleEvaluation']['score']==pytest.approx(f['baselineScore'])
    assert evidence['creativeAssessment']['newCanonicalFailures']==[]
    assert evidence['creativeAssessment']['executionRiskReviewRequired'] is True
    assert evidence['approvalEligible'] is False
    assert evidence['creativeAssessment']['executionCritic']['findings']
    assert c['review']['family8']['renderAuthorization']['status']=='BLOCKED_PENDING_EVIDENCE'


def test_different_provider_authored_decisions_are_preserved_not_replaced_by_templates():
    f=inputs();first=contact();second=deepcopy(first)
    second['interventions'][0]['production']['choreography']['instruction']='Carry the existing reach horizontally across the upper foreground, keeping the sticky edge below the finger silhouette until wrong-surface contact.'
    a=compile_reconstruction(f['text'],f['context'],first);b=compile_reconstruction(f['text'],f['context'],second)
    assert a['prompt']!=b['prompt']
    assert first['interventions'][0]['production']['choreography']['instruction'] in a['prompt']
    assert second['interventions'][0]['production']['choreography']['instruction'] in b['prompt']
    # Controlled structured decisions prove transport/compilation responsiveness only.
    assert a['creativeAssessment']['provenBetter']==b['creativeAssessment']['provenBetter']==False


def test_historical_real_response_recompiles_byte_for_byte_without_new_authorship_claims():
    path=Path(__file__).parents[3]/'output/verification/creative-optimization-v2-real-provider-acceptance-2026-10-15/saved-real-provider-role.json'
    saved=json.loads(path.read_text());request=saved['sourceRequest']
    compiled=compile_reconstruction(request['text'],request['context'],saved['rawProviderResult']['proposals'][0]['initial'])
    assert compiled['prompt']==saved['result']['candidates'][0]['prompt']
    assert 'productionProvenance' not in compiled


def test_authored_fields_cannot_claim_audience_evidence():
    p=contact();p['interventions'][0]['production']['generatorConstraints']=['This production treatment will boost retention by 20 percent.']
    _,_,r=execute([p]);assert not r['result']['candidates']
    assert 'UNSUPPORTED_AUDIENCE_OR_RENDER_CLAIM' in r['result']['rejectedProposals'][0]['reasons']


def test_real_http_adapter_mocked_sdk_budget_recovery_and_source_comparison(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from openai.types.chat import ChatCompletion
    for key,value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_PROMPT_OPTIMIZATION_MODEL':'mock-authored',
        'WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION':'.15','WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION':'.6',
        'OPENAI_API_KEY':'mock-only'}.items():monkeypatch.setenv(key,value)
    f=inputs();p=contact();p['interventions']+=progression()['interventions'];raw=response([p]);client=TestClient(app)
    answer=ChatCompletion.model_validate({'id':'mock-authored','object':'chat.completion','created':1,'model':'mock-authored',
        'choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(raw)},'finish_reason':'stop'}],
        'usage':{'prompt_tokens':5000,'completion_tokens':1800,'total_tokens':6800}})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=answer
        result=client.post('/api/v1/workflow/creative-role',json={'role':'PROMPT_OPTIMIZATION','text':f['text'],'context':f['context'],'maxCostUsd':.1})
        assert result.status_code==200,result.text
        sdk.return_value.chat.completions.create.assert_called_once()
        assert sdk.call_args.kwargs['max_retries']==0
        request=sdk.return_value.chat.completions.create.call_args.kwargs
        assert request['max_tokens']==4000
        assert 'AuthoredProduction' in request['response_format']['json_schema']['schema']['$defs']
        assert result.json()['actualCostUsd']==pytest.approx(.00183) # Simulated usage only.
    candidate=result.json()['result']['candidates'][0]
    with patch('app.workflow.creative_roles.OpenAIProvider',side_effect=AssertionError('Recovery must not dispatch')):
        recovered=client.post('/api/v1/workflow/optimization-recovery',json={'text':f['text'],'context':f['context'],'providerResult':raw,'diagnostics':{}})
    assert recovered.status_code==200,recovered.text
    assert recovered.json()['calls']==0 and recovered.json()['result']['candidates'][0]['prompt']==candidate['prompt']
    with patch('app.llm.semantic_checks.get_provider',side_effect=AssertionError('No real providers')):
        candidate['review']=canonical_review(f,candidate)
    compared=client.post('/api/v1/workflow/optimization-assessment',json={'text':f['text'],'context':f['context'],'candidates':[candidate],'baselineScore':f['baselineScore']})
    assert compared.status_code==200,compared.text
    assert compared.json()['recommendation']=='KEEP_ORIGINAL' # Existing critic's unresolved risks remain enforceable.
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        rejected=client.post('/api/v1/workflow/creative-role',json={'role':'PROMPT_OPTIMIZATION','text':f['text'],'context':f['context'],'maxCostUsd':.000001})
        assert rejected.status_code!=200
        sdk.assert_not_called()


@pytest.mark.parametrize('text',[
    'Render Mimi as a human while retaining the existing cabinet contact choreography.',
    'Do not triple the notes; triple the notes during contact to simplify the frame.'
])
def test_protected_identity_and_negation_scope_cannot_smuggle_story_changes(text):
    p=contact();p['interventions'][0]['production']['choreography']['instruction']=text
    _,_,r=execute([p]);assert not r['result']['candidates']
    assert r['result']['rejectedProposals'][0]['classification']=='STORY_FIDELITY_FAILED'
