"""Provider transport only is fake. Every reported canonical score is real."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.workflow import optimization_loop as loop
from app.workflow.creative_reconstruction import compile_reconstruction
from app.parser.actor_attempts import classify_content
from test_model_authored_execution import contact, inputs


def scope():
    f=inputs();c=f['context']
    return dict(baselinePrompt=f['text'],originalPrompt=f['text'],request=f['boundRequest'],settings=c['targetConfiguration'],approvedStory=dict(text=c['approvedStoryText'],storyId='test-story',approvalRecordId='test-approval',revision='test-revision'),ownerDecisions=[],targetAwarePreflight=dict(state='TARGET_BLOCKED_BY_STORY_CONSTRAINT',generationAllowed=False,fixedEvidenceOptimisticCeiling=89.3125,reasons=['No defensible prompt-only path to A.'],losses=[dict(ruleId='ATTEMPT_001',classification='PROTECTED_STORY_CONFLICT')]))


def auth(role='GENERATION',identity='deepseek-primary'):
    c=loop.config(identity)
    return dict(role=role,profileId=identity,provider=c['provider'],model=c['model'],reasoningEffort=c['reasoningEffort'],maxOutputTokens=c['reviewMaxOutputTokens'],maxCostUsd=1.)


def data(role='GENERATION'):
    s=scope();return dict(role=role,scope=s,prompt=s['baselinePrompt'],candidateId='isolated-candidate',round=1,authorization=auth(role),requestId='isolated-request',timeoutSeconds=20)


def proposal():
    p=contact()
    for i in p['interventions']:i.update(dependsOnBeatIds=[],dependencyJustification=None)
    return dict(proposals=[dict(initial=p,revision=None)],noImprovementReason=None)


class Transport:
    calls=0
    value=proposal()
    failure=False
    def __init__(self,cfg,tokens,timeout):self.cfg=cfg;self.timeout=timeout;self.last_usage=None;self.last_response_metadata={}
    def complete(self,prompt,**kw):
        Transport.calls+=1
        if self.failure:raise TimeoutError('never log private payload')
        self.last_raw_response=json.dumps(self.value)
        self.last_usage=dict(prompt_tokens=2000,completion_tokens=1500)
        self.last_response_metadata=dict(model=self.cfg['model'],finishReason='stop',requestId='test-fixture')
        return self.last_raw_response


def test_real_mimi_control_scores_and_integrity_no_grade_mocks():
    s=scope();doc=Path(__file__).resolve().parents[2]/'docs'
    actual=[]
    for version in ['original','V2','V3']:
        text=s['baselinePrompt'] if version=='original' else (doc/f'CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_{version}.txt').read_text().split('PROMPT BODY\n\n',1)[1].rstrip('\n')
        e=loop.evaluate(dict(scope=s,prompt=text));actual.append(e)
    assert [e['canonical']['score'] for e in actual]==pytest.approx([88.40625,80.25520833333334,88.40625])
    assert [e['integrity']['recognizedAttempts'] for e in actual]==[2,0,2]
    assert actual[1]['integrity']['status']=='POTENTIALLY_UNRELIABLE'
    assert actual[1]['integrity']['warnings'][0]['sourceQuote']
    assert actual[2]['integrity']['status']=='NO_DETECTED_CONTRADICTION'


def test_generation_reuses_actual_compiler_and_only_fake_transport():
    Transport.calls=0
    r=loop.execute_request(data(),Transport)
    assert r['executionStatus']=='COMPLETED',r
    assert Transport.calls==1
    c=r['result']['candidates'][0]
    assert c['productionProvenance'] and c['sourceEventCoverage']['semanticFidelity']=='UNKNOWN'
    e=loop.evaluate(dict(scope=scope(),prompt=c['prompt']))
    assert e['canonical']['score']==pytest.approx(88.40625)
    assert 'first-frame' not in c['prompt'] or c['prompt']!=scope()['baselinePrompt']


def test_one_candidate_wire_contract_and_no_whole_prompt_answer():
    d=data();_,raw,fmt,_=loop.parts(d)
    payload=json.loads(raw)
    assert payload['maxCandidates']==1
    assert fmt['json_schema']['schema']['properties']['proposals']['maxItems']==1
    assert 'sourceReferenceCatalog' in payload
    assert 'prompt' not in fmt['json_schema']['schema']['properties']


def test_generation_wire_payload_contains_versioned_actual_rule_feedback():
    d=data();evaluation=loop.evaluate(dict(scope=d['scope'],prompt=d['prompt']))['canonical']
    _,raw,_,context=loop.parts(d);payload=json.loads(raw);rules=payload['canonicalImprovementContext']
    assert rules['version']=='canonical-rule-improvement-context-v1'
    assert rules['rulesetVersion']=='1.11'
    assert rules['baselineScore']==pytest.approx(evaluation['score'])
    assert rules['target']=={'grade':'A','minimumScore':92,'requiresNoDisqualifyingMandatoryBlocker':True}
    expected={(r['ruleId'],r['outcome'],r['severity'],r['message']) for key in ('failedRules','unknownRules') for r in evaluation[key]}
    actual={(r['ruleId'],r['outcome'],r['severity'],r['reason']) for r in rules['failedAndUnknownFindings']}
    assert actual==expected
    assert len(rules['sha256'])==64
    assert rules['previousRoundFeedback']['remainingFindings']
    assert 'canonicalImprovementContext' not in context  # outbound contract is compiled, not trusted input


def test_unknown_and_protected_story_findings_cannot_be_advertised_as_prompt_passes():
    _,raw,_,_=loop.parts(data());rules=json.loads(raw)['canonicalImprovementContext']
    by_id={row['ruleId']:row for row in rules['failedAndUnknownFindings']}
    assert by_id['ATTEMPT_001']['classification']=='PROTECTED_STORY_CHANGE_REQUIRED'
    assert not by_id['ATTEMPT_001']['promptRewriteCanEstablishPass']
    unknown=next(row for row in rules['failedAndUnknownFindings'] if row['outcome']=='UNKNOWN')
    assert unknown['classification']=='EVIDENCE_REQUIRED_NOT_PROMPT_PROOF'
    assert not unknown['promptRewriteCanEstablishPass']


@pytest.mark.parametrize('field,value',[('model','unlisted'),('reasoningEffort','high'),('maxOutputTokens',400),('maxCostUsd',.00001)])
def test_ungranted_or_underbudget_parameters_before_transport(field,value):
    d=data();d['authorization'][field]=value;Transport.calls=0
    with pytest.raises(ValueError):loop.execute_request(d,Transport)
    assert Transport.calls==0


def test_timeout_retains_safe_details_unknown_cost_and_no_retry():
    class Failed(Transport):failure=True
    Transport.calls=0
    r=loop.execute_request(data(),Failed)
    assert Transport.calls==1 and r['executionStatus']=='FAILED_OR_AMBIGUOUS'
    assert r['costUsd'] is None and r['failure']['exceptionCategory']=='TimeoutError'
    assert not r['failure']['retrySafe'] and not r['failure']['responseReceived']
    assert 'private payload' not in json.dumps(r)


def test_source_bound_story_violation_never_compiles():
    class Changed(Transport):value=deepcopy(proposal())
    Changed.value['proposals'][0]['initial']['storyChangeRequested']=True
    r=loop.execute_request(data(),Changed)
    assert not r['result']['candidates']
    assert r['result']['rejectedProposals'][0]['classification']=='STORY_CHANGE_REQUIRES_APPROVAL'


def test_unknown_source_cannot_become_best_and_diagnostic_not_render():
    r=loop.execute_request(data(),Transport);c=r['result']['candidates'][0];s=scope();base=loop.evaluate(dict(scope=s,prompt=s['baselinePrompt']))
    compared=loop.compare(dict(scope=s,candidate=c,parentPrompt=s['baselinePrompt'],parentEvaluation=base,baselineEvaluation=base))
    assert not compared['retained'] and compared['sourceFidelity']=='UNKNOWN'
    assert compared['rejectionReason']=='SOURCE_FIDELITY_REVIEW_REQUIRED'
    assert compared['officialCpqGrading']=='INACTIVE' and not compared['renderAuthorized']


def test_mimi_parser_recovery_not_certified_as_creative_gain():
    s=scope();doc=Path(__file__).resolve().parents[2]/'docs'
    v2=(doc/'CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V2.txt').read_text().split('PROMPT BODY\n\n',1)[1].rstrip('\n')
    e=loop.evaluate(dict(scope=s,prompt=v2))
    assert e['canonical']['score']==pytest.approx(80.25520833333334)
    assert e['integrity']['status']=='POTENTIALLY_UNRELIABLE'
    # No synthetic canonical A or invented source verdict is used here.


def test_inactive_target_is_not_a_grade_and_missing_images_do_not_block_text():
    caps=loop.capabilities()
    assert caps['targets'][0]['minimumScore']==92 and not caps['targets'][1]['supported']
    s=scope();s['request']['references']=[];s['request']['acceptedStartFrame']=False
    assert loop.evaluate(dict(scope=s,prompt=s['baselinePrompt']))['canonical']['status']=='EVALUATED'


def test_unrelated_story_uses_same_real_evaluator_and_frozen_story():
    s=scope();text='TITLE / FORMAT\nZed / 15s\n0-2s: Zed tries to lift the box.\n2-5s: Zed continues to pull the box.\n5-10s: Zed pushes the box onto the mat.\n10-12s: Zed sees the box.\n12-15s: Zed stops beside the box.'
    s['baselinePrompt']=text;s['approvedStory']['text']='Zed moves the box onto a mat and stops beside it.'
    e=loop.evaluate(dict(scope=s,prompt=text))
    assert e['canonical']['status']=='EVALUATED' and e['canonical']['rulesetVersion']=='1.11'
    assert 'Mimi' not in json.dumps(e)


def test_attempt_parser_requires_source_bound_actor_for_pull_consequence():
    baseline=classify_content('Pip continues to pull; each pull doubles the sticky notes from two to four to eight.', 'Pip')
    generated=classify_content('Each pull doubles the sticky notes from two to four to eight.', 'Pip')
    assert baseline['actions'][0]['classification']=='CHARACTER_ATTEMPT'
    assert baseline['actions'][0]['primaryVerb']=='PULL'
    assert generated['actions']==[]
    assert generated['classification']=='NOT_AN_ATTEMPT'
