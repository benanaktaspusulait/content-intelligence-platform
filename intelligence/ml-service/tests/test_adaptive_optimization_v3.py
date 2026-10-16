"""Offline policy/capability acceptance. Mock grades prove routing, not creativity."""
import hashlib
import json
from copy import deepcopy
from unittest.mock import patch
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.workflow.adaptive_optimization import feasibility, stage_decision, qualify, escalation_brief
from app.workflow.creative_provider_profiles import profile, CreativeCapabilityProvider
from test_model_authored_execution import inputs, contact, execute
from test_authoring_contract_repair_v2 import saved_response, reviewed
from test_optimization_failure_contract import sdk_response


def baseline():
    return {'status':'EVALUATED','rulesetVersion':'1.11','score':85.,'grade':'B',
        'passedRules':[{'ruleId':'NOVELTY_001','family':'visual_novelty','severity':'WARNING','outcome':'PASS','message':'Source-supported production opportunity','details':{}}],
        'failedRules':[],'unknownRules':[],'notApplicableRules':[],'videoPlanIR':{'beats':[]}}


def candidate(score=95,material=True,faithful=True):
    canonical=deepcopy(baseline());canonical.update(score=score,grade='A' if score>=92 else 'B')
    return {'candidateId':'candidate-a','prompt':'Controlled routing evidence, never a prepared creative winner',
        'currentAssessment':{'classification':'PLAUSIBLE_IMPROVEMENT_UNVERIFIED' if material else 'VALID_BUT_EQUIVALENT','approvalEligible':True,'creativeAssessment':{'changeContract':[{'opportunityId':'CONTACT_PLANE:beat_01','observableDifference':'Source-bound contact geometry changes'}]}},
        'review':{'canonicalRuleEvaluation':canonical,'executionReview':{'status':'PASS'}},
        'sourceEventCoverage':{'semanticFidelity':'PASS' if faithful else 'UNKNOWN'}}


def test_mimi_actual_saved_canonical_matches_audit_not_a_new_evaluation():
    f=inputs();c=f['context']['baselineCanonicalEvaluation'];before=deepcopy(c)
    audit=feasibility(c,f['text'],f['context'])
    assert audit['currentScore']==pytest.approx(88.40625)
    assert audit['fixedEvidenceOptimisticCeiling']==pytest.approx(89.3125)
    assert not audit['generationAllowed'] and audit['state']=='TARGET_BLOCKED_BY_STORY_CONSTRAINT'
    assert audit['genuineSourceAttemptCount']==2 and c==before
    assert audit['canonicalGradeContract']=={'minimumA':92,'minimumB':80,'aPlusExists':False}
    assert audit['creativeOpportunity']['state']=='UNKNOWN_REQUIRES_PROMPT_DIAGNOSIS'
    assert audit['canonicalATargetStatus']=='CANONICAL_A_UNATTAINABLE_WITH_CURRENT_EVIDENCE'
    assert audit['creativeQualityTarget']=={'active':False,'state':'CALIBRATION_REQUIRED','gradeThresholdsAvailable':False}
    assert sum(l['overallLoss'] for l in audit['losses'])==pytest.approx(11.59375)
    assert len(audit['missingEvidence'])==13
    assert not audit['researchGenerationEligibility']['allowed']
    assert audit['researchGenerationEligibility']['state']=='BLOCKED_BY_PROTECTED_STORY_CONSTRAINT'


def test_legitimate_numeric_b_to_a_path_is_distinguished_from_mimi():
    audit=feasibility(baseline())
    assert audit['generationAllowed'] and audit['fixedEvidenceOptimisticCeiling']==100
    assert audit['losses'][0]['classification']=='CREATIVE_RECONSTRUCTION_REPAIRABLE'
    assert feasibility(baseline(),context={'creativeQualityTargetActive':True})['creativeQualityTarget']['active'] is True
    # This is a controlled policy input; real canonical integration is tested
    # separately and never manufactures these values for saved Mimi.


@pytest.mark.parametrize('score,material,faithful,qualified,state',[
    (95,True,True,True,'A_QUALIFIED'),(90,True,True,False,'IMPROVED_BELOW_TARGET'),
    (85,True,True,False,'IMPROVED_BELOW_TARGET'),(95,False,True,False,'TARGET_NOT_REACHED'),
    (95,True,False,False,'IMPROVED_BELOW_TARGET'),(82,True,True,False,'TARGET_NOT_REACHED')])
def test_grade_creativity_source_and_regression_are_independent(score,material,faithful,qualified,state):
    c=candidate(score,material,faithful);q=qualify(c,baseline())
    assert q['qualified']==qualified
    d=stage_decision({'candidates':[c]},baseline())
    assert d['state']==state and d['escalationJustified'] is not qualified
    assert q['renderAuthorized'] is False
    assert len(q['dimensions'])==6 and all(r['audienceEvidence'] is None for r in q['dimensions'])
    if not faithful:assert q['sourceFidelity']=='UNKNOWN'


@pytest.mark.parametrize('defect',['stale-ruleset','critic','approval','blocker','visual-evidence','semantic-evidence','source-regression'])
def test_numerical_a_never_overrides_independent_gates(defect):
    c=candidate();canonical=c['review']['canonicalRuleEvaluation']
    if defect=='stale-ruleset':canonical['rulesetVersion']='1.10'
    if defect=='critic':c['review']['executionReview']['status']='REWRITE'
    if defect=='approval':c['currentAssessment']['approvalEligible']=False
    if defect=='blocker':canonical['failedRules']=[{'ruleId':'ATTEMPT_001','outcome':'FAIL','severity':'BLOCKER','details':{}}]
    if defect=='visual-evidence':canonical['failedRules']=[{'ruleId':'ENGINE_SILHOUETTE_DUPLICATE','outcome':'FAIL','severity':'BLOCKER','details':{'failureBasis':'EVIDENCE_INCOMPLETE'}}]
    if defect=='semantic-evidence':canonical['unknownRules']=[{'ruleId':'ATTEMPT_002','outcome':'UNKNOWN','severity':'CRITICAL'}]
    if defect=='source-regression':c['currentAssessment']['classification']='STORY_FIDELITY_FAILED'
    assert not qualify(c,baseline())['qualified']


def test_missing_visual_evidence_stops_even_when_numeric_ceiling_is_high():
    c=baseline();c['failedRules']=[{'ruleId':'ENGINE_SILHOUETTE_DUPLICATE','family':'visual_novelty','severity':'BLOCKER','outcome':'FAIL','details':{'failureBasis':'EVIDENCE_INCOMPLETE'}}]
    audit=feasibility(c)
    assert audit['state']=='TARGET_BLOCKED_BY_EVIDENCE' and not audit['generationAllowed']
    research=audit['researchGenerationEligibility']
    assert research['allowed'] and research['state']=='ELIGIBLE_FOR_EXPLICIT_OWNER_AUTHORIZATION'
    assert not research['finalCanonicalAAdmitted'] and not research['promptApprovalAllowed']
    assert not research['imageGenerationAllowed'] and not research['renderAuthorized']


def test_schema_contract_failure_is_not_a_creative_failure_to_escalate():
    value={'creativeEvidence':{'rejectedProposals':[{'classification':'AUTHORING_CONTRACT_INVALID','errors':['bad catalog ID']}]},'candidates':[]}
    result=stage_decision(value,baseline())
    assert result['state']=='CONTRACT_FAILURE' and not result['escalationJustified']
    value={'optimizationFailed':True,'category':'SOURCE_PLAN_VALIDATION_FAILED'}
    assert not stage_decision(value,baseline())['escalationJustified']


def test_escalation_keeps_original_and_validated_changes_not_rejected_preferred_prompt():
    f=inputs();good=candidate(90);good['creativeAssessment']=good['currentAssessment']['creativeAssessment'];bad=candidate(82);bad['candidateId']='candidate-b';bad['prompt']='Rejected production instructions';bad['currentAssessment']['classification']='REGRESSION'
    comparison={'candidates':[good,bad],'creativeEvidence':{'rejectedProposals':[{'classification':'VALID_BUT_EQUIVALENT'}]}}
    brief=escalation_brief(f['text'],f['context'],comparison,stage_decision(comparison,baseline()))
    assert brief['originalPrompt']==f['text'] and brief['approvedStory']==f['context']['approvedStoryText']
    assert [c['prompt'] for c in brief['validatedDrafts']]==[good['prompt']]
    assert 'Rejected production instructions' not in json.dumps(brief['validatedDrafts'])


@pytest.mark.parametrize('identity,mode,token_parameter',[('deepseek-primary','json_object','max_tokens'),('openai-escalation','json_schema','max_completion_tokens')])
def test_exact_provider_capabilities_serialized_without_fallback_or_retry(monkeypatch,identity,mode,token_parameter):
    monkeypatch.setenv('DEEPSEEK_API_KEY','offline-only');monkeypatch.setenv('OPENAI_API_KEY','offline-only')
    f=inputs();from app.workflow.creative_reconstruction import response_format
    p=profile(identity)
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=sdk_response('{"proposals":[],"noImprovementReason":"No grounded change"}')
        provider=CreativeCapabilityProvider(p,4000,5);provider.response_format=response_format(f['context'],f['text'])
        provider.complete('full source context','Return JSON')
        args=sdk.return_value.chat.completions.create.call_args.kwargs
        assert args['model']==p['model'] and args['response_format']['type']==mode
        assert args[token_parameter]==4000 and 'temperature' not in args
        assert args['reasoning_effort']=='high'
        if mode=='json_object':assert 'beat_01.actualSurface' in args['messages'][0]['content']
        assert sdk.call_args.kwargs['max_retries']==0
        sdk.return_value.chat.completions.create.assert_called_once()
        assert provider.last_usage['completion_tokens']==1500
        assert provider.last_response_metadata['apiStatus']=='COMPLETED'


def test_direct_ml_v3_dispatch_without_backend_signature_is_rejected_without_sdk(monkeypatch):
    f=inputs();context={**f['context'],'adaptiveVersion':'adaptive-creative-optimization-v3'}
    with patch('app.workflow.creative_roles.run_paid_role',side_effect=AssertionError('No dispatch')):
        response=TestClient(app).post('/api/v1/workflow/creative-role',json={'role':'PROMPT_OPTIMIZATION','text':f['text'],'context':context,'maxCostUsd':.2})
    assert response.status_code==403


def test_historical_outputs_replay_exactly_while_controlled_authored_plan_compiles():
    _,_,reviews=reviewed(saved_response())
    assert [len(r['technicalDiagnostics']) for r in reviews]==[2,4]
    assert all(r['sourceFidelity']=='UNKNOWN' and r['materiality']['classification']=='VALID_BUT_EQUIVALENT' for r in reviews)
    f,provider,result=execute([contact()]);assert provider.calls==1
    c=result['result']['candidates'][0]
    assert c['sourceEventCoverage']['semanticFidelity']=='UNKNOWN'
    assert c['productionProvenance']['segments']
    assert c['creativeAssessment']['provenBetter'] is False


def test_paid_adapter_contract_uses_exact_v3_profile_budget_and_one_mock_call(monkeypatch):
    from app.workflow.creative_roles import run_paid_role
    from app.workflow.creative_provider_profiles import readiness
    from test_creative_reconstruction_v2 import response
    f=inputs();monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','true');monkeypatch.setenv('DEEPSEEK_API_KEY','offline-only')
    context={**f['context'],'adaptiveVersion':'adaptive-creative-optimization-v3','providerProfileId':'deepseek-primary',
        'providerCapabilityBinding':readiness()['profiles']['deepseek-primary'],'authorizedOutputTokens':4000,'authorizedTimeoutSeconds':5}
    with patch('app.workflow.creative_provider_profiles.OpenAI') as sdk:
        sdk.return_value.chat.completions.create.return_value=sdk_response(json.dumps(response([contact()])))
        result=run_paid_role('PROMPT_OPTIMIZATION',f['text'],context,.2)
        assert result['provider']=='deepseek' and result['model']==profile('deepseek-primary')['model']
        assert result['calls']==1 and result['result']['candidates']
        assert result['actualCostUsd']<=result['approvedCostCeilingUsd']
        assert 'UPPER_BOUND' in result['costBasis']
        sdk.return_value.chat.completions.create.assert_called_once()
    with patch('app.workflow.creative_provider_profiles.OpenAI',side_effect=AssertionError('No dispatch')):
        with pytest.raises(ValueError,match='cost ceiling'):run_paid_role('PROMPT_OPTIMIZATION',f['text'],context,.000001)
        bad={**context,'providerCapabilityBinding':{**context['providerCapabilityBinding'],'model':'unapproved'}}
        with pytest.raises(ValueError,match='changed after authorization'):run_paid_role('PROMPT_OPTIMIZATION',f['text'],bad,.2)


def test_metrics_keep_mock_and_real_separate_and_absent_acceptance_audience_unknown():
    from app.workflow.adaptive_optimization import optimization_metrics
    c=candidate(90);decision=stage_decision({'candidates':[c]},baseline())
    run={'mode':'ADAPTIVE','evidenceOrigin':'MOCK_PROVIDER','providerCalls':1,'targetQualified':False,
         'stages':[{'provider':'deepseek','model':'mock','decision':decision,'comparison':{'candidates':[c]},'costUsd':.001}]}
    result=optimization_metrics([run,{**run,'evidenceOrigin':'REAL_PROVIDER'}])
    assert len(result['cohorts'])==2
    for cohort in result['cohorts']:
        assert cohort['aQualificationRate']==0 and cohort['materialImprovementRate']==1
        assert cohort['operatorAcceptanceRate'] is None and cohort['audienceOutcome'] is None
        assert cohort['calculatedCostUpperBoundPerA'] is None
    fixture=next(c for c in result['cohorts'] if c['evidenceOrigin']=='DETERMINISTIC_FIXTURE')
    real=next(c for c in result['cohorts'] if c['evidenceOrigin']=='REAL_AI_PROVIDER')
    assert fixture['realCreativeEffectiveness']=='EXCLUDED_NON_REAL_PROVIDER_EVIDENCE'
    assert not fixture['realProviderCapabilityStatisticsEligible'] and not fixture['officialAPlusCalibrationEligible']
    assert real['realProviderCapabilityStatisticsEligible']


def test_cross_beat_changes_must_identify_real_justified_dependencies():
    from app.workflow.creative_reconstruction import perform_reconstruction
    from test_creative_reconstruction_v2 import response, MockProvider
    from test_model_authored_execution import progression
    f=inputs();context={**f['context'],'adaptiveVersion':'adaptive-creative-optimization-v3'}
    p=contact();p['interventions']+=progression()['interventions']
    p['interventions'][0].update(dependsOnBeatIds=['beat_03'],dependencyJustification='Maintain the same contact-side composition through the existing count progression without changing events.')
    value=perform_reconstruction(f['text'],context,MockProvider(response([p])),'mock-only')
    assert value['result']['candidates']
    p['interventions'][0]['dependsOnBeatIds']=['invented-beat']
    invalid=perform_reconstruction(f['text'],context,MockProvider(response([p])),'mock-only')
    assert not invalid['result']['candidates']
    assert 'UNJUSTIFIED_CROSS_BEAT_DEPENDENCY' in str(invalid['result']['rejectedProposals'])
