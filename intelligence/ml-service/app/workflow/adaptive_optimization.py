"""V3 policy helpers for the existing creative workflow. No provider or persistence.

Inputs to this module come from backend-loaded immutable evidence, never browser
claims. Numeric grades remain exclusively the canonical rule engine's contract.
"""
from collections import defaultdict
from math import isfinite
from app.quality.family_weights import CANONICAL_FAMILY_WEIGHTS
from .creative_reconstruction import DIMENSIONS
from .creative_validity import normalize_origin

VERSION = 'adaptive-creative-optimization-v3'
RESEARCH_ELIGIBILITY_VERSION = 'canonical-a-text-research-eligibility-v1'
A_MINIMUM = 92
MODES = ('DEEPSEEK_ONLY', 'OPENAI_ONLY', 'ADAPTIVE')
FIXED_PASS = {'MINI_STORY_LOCK','GOAL_VISIBLE_EARLY','TEMPORAL_COMPLEXITY_SPLIT_GATE','BEAT_DENSITY_RULE'}


def creative_scope_decision(source, canonical):
    """Decide whether another source-bound prompt rewrite has material scope.

    This is independent of canonical scoring.  It uses the existing
    creative-validity evidence to distinguish local presentation work from
    weaknesses that require a proposed and owner-approved story revision.
    """
    from .creative_validity import assess
    validity = assess(source, canonical, {'origin': 'UNKNOWN_ORIGIN', 'reviewerIndependent': False})
    codes = {row.get('code') for row in validity.get('risks', [])}
    story_level = []
    if 'REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE' in codes:
        story_level.append('VIEWER_VISIBLE_CAUSAL_VARIETY_REQUIRES_NEW_SOURCE_CONSEQUENCES')
    if 'ENDING_TIMING_OVERLOAD' in codes:
        story_level.append('ENDING_EVENT_LOAD_REQUIRES_STORY_RETIMING_OR_REDESIGN')
    if 'FRAME_ZERO_STATE_UNVERIFIED' in codes:
        story_level.append('OPENING_PROMISE_REQUIRES_VISUAL_EVIDENCE_OR_STORY_LEVEL_CHANGE')
    prompt_level = []
    if 'CRITICAL_PRODUCIBILITY_RISK' in codes:
        prompt_level.append('SOURCE_BOUND_PRODUCTION_RISK_MITIGATION')
    # Two independent story-level weaknesses establish that another bounded
    # staging pass cannot address the principal creative problem.  Local
    # staging remains useful, but it is classified honestly as presentation.
    limited = {'REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE', 'ENDING_TIMING_OVERLOAD'} <= codes
    return {
        'version': 'creative-scope-decision-v1',
        'state': 'NO_MATERIAL_PROMPT_ONLY_CREATIVE_GAIN' if limited else 'SOURCE_BOUND_PRESENTATION_IMPROVEMENT',
        'promptOnlyGainLimited': limited,
        'promptLevelOpportunities': prompt_level,
        'storyLevelCreativeBlockers': story_level,
        'nextAction': 'OWNER_APPROVED_STORY_EVOLUTION' if limited else 'SOURCE_BOUND_PROMPT_OPTIMIZATION',
        'providerDispatchRecommended': not limited,
        'basis': 'Creative-validity risks are evaluated separately from the canonical score; no audience or render improvement is inferred.',
    }


def rows(canonical):
    return sum((canonical.get(k, []) for k in ('passedRules','failedRules','unknownRules','notApplicableRules')), [])


def points(row):
    if row.get('outcome') not in ('PASS','FAIL') or row.get('details',{}).get('failureBasis') == 'EVIDENCE_INCOMPLETE':
        return None
    severity = row.get('severity')
    return (100 if severity == 'PASS' else 85) if row['outcome']=='PASS' else {'BLOCKER':0,'CRITICAL':40}.get(severity,70)


def research_eligibility(*, contract_valid, aggregate_matches, ceiling, protected_attempt, visual_missing):
    """A narrow text-only capability-test gate, separate from final admission.

    Missing downstream image evidence may remain an experiment input. A source
    story conflict, stale/invalid canonical contract, or unattainable fixed-
    evidence ceiling may not. This decision never authorizes prompt acceptance,
    image generation, render preparation, or rendering.
    """
    allowed=bool(contract_valid and aggregate_matches and ceiling >= A_MINIMUM and not protected_attempt)
    state=('ELIGIBLE_FOR_EXPLICIT_OWNER_AUTHORIZATION' if allowed else
           'CONTRACT_FAILURE' if not contract_valid or not aggregate_matches else
           'BLOCKED_BY_PROTECTED_STORY_CONSTRAINT' if protected_attempt else
           'BLOCKED_BY_FIXED_EVIDENCE_CEILING')
    reasons=[]
    if not contract_valid: reasons.append('A complete current Ruleset 1.11 evaluation is required.')
    elif not aggregate_matches: reasons.append('Persisted score does not match authoritative aggregation.')
    elif protected_attempt: reasons.append('The source story fails ATTEMPT_001; text research cannot invent another source event.')
    elif ceiling < A_MINIMUM: reasons.append('The fixed-evidence optimistic ceiling is below the Canonical A threshold.')
    elif visual_missing: reasons.append('Downstream visual evidence is pending; it remains mandatory for final admission and render readiness.')
    return {
        'version':RESEARCH_ELIGIBILITY_VERSION,
        'scope':'TEXT_ONLY_SOURCE_BOUND_MODEL_CAPABILITY_RESEARCH',
        'state':state,'allowed':allowed,'reasons':reasons,
        'requiresExplicitOwnerAuthorization':True,
        'requiresIndependentSourceFidelity':True,
        'requiresIndependentCreativeCritic':True,
        'finalCanonicalAAdmitted':False,'promptApprovalAllowed':False,
        'imageGenerationAllowed':False,'renderPreparationAllowed':False,
        'renderAuthorized':False,
    }


def feasibility(canonical, source='', context=None):
    """Conditional fixed-evidence ceiling, never impute unknown observations.

    Protected event windows, story and rule semantics are held fixed. Additional
    independent evidence changes the denominator and requires a fresh audit.
    """
    context=context or {}
    if canonical.get('status')!='EVALUATED' or canonical.get('rulesetVersion')!='1.11':
        return {'version':VERSION,'state':'CONTRACT_FAILURE','generationAllowed':False,'reasons':['A feasibility requires a complete current Ruleset 1.11 evaluation.'],
                'researchGenerationEligibility':research_eligibility(contract_valid=False,aggregate_matches=False,ceiling=0,protected_attempt=False,visual_missing=False)}
    families=defaultdict(list)
    for row in rows(canonical):
        if points(row) is not None: families[row['family']].append(row)
    denominator=sum(CANONICAL_FAMILY_WEIGHTS.get(f,.05) for f in families)
    if not denominator:
        return {'version':VERSION,'state':'TARGET_BLOCKED_BY_EVIDENCE','generationAllowed':False,'reasons':['No numeric canonical evidence.'],
                'researchGenerationEligibility':research_eligibility(contract_valid=False,aggregate_matches=False,ceiling=0,protected_attempt=False,visual_missing=False)}
    # Genuine source attempts are inspected from the saved canonical IR; no
    # camera count, client-supplied waiver or new model assertion can add one.
    beats=canonical.get('videoPlanIR',{}).get('beats',[])
    attempts=[b for b in beats if b.get('isAttempt') is True]
    protected_attempt=any(r.get('ruleId')=='ATTEMPT_001' and r.get('outcome')=='FAIL' for r in rows(canonical))
    losses=[]; current=0.; ceiling=0.
    for family, group in families.items():
        coefficient=CANONICAL_FAMILY_WEIGHTS.get(family,.05)/denominator/len(group)
        for row in group:
            value=points(row); rid=row['ruleId']; maximum=100; kind='TEXT_REPAIRABLE'
            reason='Requires a supported source-bound production change and fresh canonical evaluation.'
            if rid in FIXED_PASS:
                maximum=85;kind='NOT_CURRENTLY_ATTAINABLE';reason='Successful Ruleset 1.11 branch retains non-PASS configured severity and earns 85.'
            elif rid=='ATTEMPT_001' and protected_attempt:
                maximum=value;kind='PROTECTED_STORY_CONFLICT';reason=f'{len(attempts)} genuine saved source-bound attempts; adding an event violates the protected story. An admission exception cannot change score.'
            elif rid=='PRODUCIBILITY_003' and value<100:
                maximum=value;kind='EVIDENCE_REQUIRED';reason='Source still contains fragile note/face interaction; substring detection has limited specificity. No independent risk-reduction evidence or authorized evaluator correction supports removing this penalty.'
            elif rid in {'ESCALATION_004','PAYOFF_002'} and value<100:
                maximum=value;kind='PROTECTED_STORY_CONFLICT';reason='Protected event windows and ending/fake-win events cannot be rewritten to obtain points.'
            elif rid in {'NOVELTY_001','PAYOFF_004'} and value<100:
                kind='CREATIVE_RECONSTRUCTION_REPAIRABLE';reason='Optimistic conditional improvement only; no invented sub-beat timing or unsupported salience evidence.'
            current+=value*coefficient;ceiling+=maximum*coefficient
            if value<100:losses.append({'ruleId':rid,'family':family,'rowPoints':value,'familyWeight':CANONICAL_FAMILY_WEIGHTS.get(family,.05),'scoredFamilyRows':len(group),'overallLoss':(100-value)*coefficient,'maximumRowPoints':maximum,'classification':kind,'reason':reason,'sourceEvidence':row.get('message'),'details':row.get('details',{})})
    missing=[{'ruleId':r['ruleId'],'classification':'EVIDENCE_REQUIRED','reason':r.get('message'),'details':r.get('details',{})} for r in rows(canonical) if r.get('outcome')=='UNKNOWN' or r.get('details',{}).get('failureBasis')=='EVIDENCE_INCOMPLETE']
    matches=isinstance(canonical.get('score'),(int,float)) and abs(current-canonical['score'])<1e-7
    state='DIAGNOSING' if ceiling>=A_MINIMUM else 'TARGET_BLOCKED_BY_STORY_CONSTRAINT' if protected_attempt else 'TARGET_BLOCKED_BY_EVIDENCE'
    visual_missing=any(r['ruleId'] in {'INSTANT_VISUAL_ABSURDITY_GATE','ENGINE_SILHOUETTE_DUPLICATE'} for r in missing)
    if ceiling>=A_MINIMUM and visual_missing:state='TARGET_BLOCKED_BY_EVIDENCE'
    if not matches:state='CONTRACT_FAILURE'
    quality_active=context.get('creativeQualityTargetActive') is True
    creative_scope=creative_scope_decision(source,canonical)
    prompt_scope_limited=creative_scope['promptOnlyGainLimited']
    if matches and prompt_scope_limited:state='NO_MATERIAL_PROMPT_ONLY_CREATIVE_GAIN'
    reasons=(['Persisted score does not match authoritative aggregation.'] if not matches else
             ['Principal creative weaknesses require owner-approved Story Evolution; another source-bound staging round is not justified.'] if prompt_scope_limited else
             ['Required independent visual evidence is missing.'] if ceiling>=A_MINIMUM and visual_missing else
             [] if ceiling>=A_MINIMUM else ['No defensible prompt-only path to A with current evidence and protected story.'])
    research=research_eligibility(contract_valid=True,aggregate_matches=matches,ceiling=ceiling,protected_attempt=protected_attempt,visual_missing=visual_missing)
    if prompt_scope_limited:
        research.update(allowed=False,state='NO_MATERIAL_PROMPT_ONLY_CREATIVE_GAIN',
                        reasons=['Prompt-only capability research is stopped because the principal weaknesses require Story Evolution.'])
    return {'version':VERSION,'state':state,'generationAllowed':matches and ceiling>=A_MINIMUM and not visual_missing and not prompt_scope_limited,'canonicalGradeContract':{'minimumA':A_MINIMUM,'minimumB':80,'aPlusExists':False},'currentScore':current,'fixedEvidenceOptimisticCeiling':ceiling,'ceilingScope':'CURRENT_ELIGIBLE_ROWS_AND_PROTECTED_EVENTS; new independent evidence requires recomputation','familyWeightDenominator':denominator,'losses':losses,'missingEvidence':missing,'genuineSourceAttemptCount':len(attempts),'creativeOpportunity':creative_scope,'canonicalATargetStatus':'CANONICAL_A_UNATTAINABLE_WITH_CURRENT_EVIDENCE' if ceiling<A_MINIMUM else 'CANONICAL_A_POTENTIALLY_ATTAINABLE','creativeQualityTarget':{'active':quality_active,'state':'ACTIVE_CALIBRATED_TARGET' if quality_active else 'CALIBRATION_REQUIRED','gradeThresholdsAvailable':quality_active},'reasons':reasons,
            'researchGenerationEligibility':research,
            'renderAuthorized':False}


def quality_dimensions(candidate):
    creative=candidate.get('currentAssessment',{}).get('creativeAssessment',candidate.get('creativeAssessment',{}))
    changes=creative.get('changeContract',[])
    regression=candidate.get('currentAssessment',{}).get('classification')=='REGRESSION'
    result=[]
    for dim in DIMENSIONS:
        relevant=[c for c in changes if c.get('dimension')==dim or (dim=='SCROLL_STOP_VISUAL_PROMISE' and c.get('opportunityId','').startswith('CONTACT_PLANE:')) or (dim=='CAUSAL_PROGRESSION' and c.get('opportunityId','').startswith('COUNTABLE_STATE_PATH:')) or dim in {'VISUAL_STORYTELLING','PRODUCTION_EXECUTABILITY','DISTINCTIVE_CREATIVE_VALUE'}]
        # A concrete instruction difference supports textual change, never an
        # audience/visual benefit. Unaffected dimensions make no improvement claim.
        state='REGRESSION' if regression else 'PLAUSIBLE_UNVERIFIED_IMPROVEMENT' if relevant else 'NO_MATERIAL_CHANGE'
        result.append({'dimension':dim,'state':state,'evidence':relevant,'audienceEvidence':None,'visualEvidence':None})
    return result


def qualify(candidate, baseline):
    assessment=candidate.get('currentAssessment',{})
    canonical=candidate.get('review',{}).get('canonicalRuleEvaluation',{})
    score=canonical.get('score'); base_score=baseline.get('score')
    same_ruleset=canonical.get('rulesetVersion')==baseline.get('rulesetVersion')=='1.11'
    material=assessment.get('classification') in ('PLAUSIBLE_IMPROVEMENT_UNVERIFIED','MATERIAL_IMPROVEMENT_SUPPORTED')
    critic=candidate.get('review',{}).get('executionReview',{})
    critic_status=critic.get('status',critic.get('recommendation'))
    blockers=[r['ruleId'] for r in canonical.get('failedRules',[]) if r.get('severity')=='BLOCKER' and r.get('details',{}).get('failureBasis')!='EVIDENCE_INCOMPLETE']
    # Waivers apply to admission only. Do not label a failed protected-story
    # requirement as target-qualified by observing a sufficiently high number.
    gaps=[r['ruleId'] for r in rows(canonical) if (r.get('outcome')=='UNKNOWN' or r.get('details',{}).get('failureBasis')=='EVIDENCE_INCOMPLETE') and r.get('severity') in ('BLOCKER','CRITICAL')]
    regression=assessment.get('classification') in ('REGRESSION','STORY_FIDELITY_FAILED','STORY_CHANGE_REQUIRES_APPROVAL') or (isinstance(score,(int,float)) and isinstance(base_score,(int,float)) and score<base_score)
    faithful=candidate.get('sourceEventCoverage',{}).get('semanticFidelity')=='PASS'
    # UNKNOWN fidelity stays UNKNOWN. Source anchor preservation alone cannot
    # create independent semantic evidence or canonical PASS.
    eligible=all((same_ruleset,canonical.get('status')=='EVALUATED',material,assessment.get('approvalEligible') is True,faithful,not regression,not blockers,not gaps,critic_status not in ('REWRITE','BLOCKED','FAIL','UNKNOWN',None)))
    qualified=eligible and isinstance(score,(int,float)) and isfinite(score) and score>=A_MINIMUM and canonical.get('grade')=='A'
    return {'candidateId':candidate.get('candidateId'),'canonicalRegression':isinstance(score,(int,float)) and isinstance(base_score,(int,float)) and score<base_score,'creativeRegression':assessment.get('creativeAssessment',{}).get('creativeRegression'),'productionRiskRegression':assessment.get('creativeAssessment',{}).get('productionRiskIndicatorRegression',False),'sourceFidelityFailed':assessment.get('classification') in ('STORY_FIDELITY_FAILED','STORY_CHANGE_REQUIRES_APPROVAL'),'qualified':qualified,'material':material,'regression':regression,'canonicalScore':score,'canonicalGrade':canonical.get('grade'),'sameRuleset':same_ruleset,'sourceFidelity':candidate.get('sourceEventCoverage',{}).get('semanticFidelity','UNKNOWN'),'blockingRules':blockers,'missingApplicableEvidence':gaps,'draftLabel':'TARGET-QUALIFIED FINAL CANDIDATE' if qualified else 'BEST AVAILABLE DRAFT','dimensions':quality_dimensions(candidate),'renderAuthorized':False}


def stage_decision(comparison, baseline):
    if comparison.get('optimizationFailed'):
        return {'state':'CONTRACT_FAILURE' if comparison.get('category') in ('SOURCE_PLAN_VALIDATION_FAILED','CANONICAL_EVALUATION_FAILED','CANDIDATE_STRUCTURE_INVALID') else 'PROVIDER_FAILURE','escalationJustified':False,'qualifications':[]}
    evidence=comparison.get('creativeEvidence',{})
    rejected=evidence.get('rejectedProposals',[])
    if any(r.get('classification')=='AUTHORING_CONTRACT_INVALID' for r in rejected):
        return {'state':'CONTRACT_FAILURE','escalationJustified':False,'qualifications':[],'reasons':['Repair shared authoring contract offline before spending on escalation.']}
    qualifications=[qualify(c,baseline) for c in comparison.get('candidates',[])]
    qualified=next((q for q in qualifications if q['qualified']),None)
    return {'state':'A_QUALIFIED' if qualified else 'IMPROVED_BELOW_TARGET' if any(q['material'] and not q['regression'] for q in qualifications) else 'TARGET_NOT_REACHED','escalationJustified':not bool(qualified),'qualifiedCandidateId':qualified['candidateId'] if qualified else None,'qualifications':qualifications}


def escalation_brief(source, context, comparison, decision):
    keep=[c for c in comparison.get('candidates',[]) if any(q['candidateId']==c.get('candidateId') and q['material'] and not q['regression'] for q in decision['qualifications'])]
    return {'originalPrompt':source,'approvedStory':context.get('approvedStoryText'),'baselineCanonicalEvaluation':context.get('baselineCanonicalEvaluation'),'validatedDrafts':[{'prompt':c['prompt'],'changeContract':c.get('creativeAssessment',{}).get('changeContract',[]),'canonical':c.get('review',{}).get('canonicalRuleEvaluation'),'executionRisk':c.get('review',{}).get('executionReview')} for c in keep],'rejectedEvidence':comparison.get('creativeEvidence',{}).get('rejectedProposals',[]),'remainingGaps':decision['qualifications'],'instruction':'Independently reason from the original and diagnosis. Preserve only source-validated material changes; rejected proposals are failure evidence, never preferred instructions. Do not polish wording or invent evidence.'}


def optimization_metrics(runs):
    """Concise cohort contract: mock/real, model and mode never share a bucket.

    Acceptance must come from persisted explicit prompt-version provenance,
    supplied by the backend reporting projection, not inferred from drafting.
    """
    groups=defaultdict(list)
    for run in runs:
        origin=run.get('evidenceOrigin','UNKNOWN')
        for stage in run.get('stages',[]):
            groups[(origin,run.get('mode'),stage.get('provider'),stage.get('model'))].append((run,stage))
    reports=[]
    for (origin,mode,provider,model),entries in groups.items():
        n=len(entries);qualified=sum(s.get('decision',{}).get('state')=='A_QUALIFIED' for _,s in entries)
        qualifications=[q for _,s in entries for q in s.get('decision',{}).get('qualifications',[])]
        rejected=[r for _,s in entries for r in s.get('comparison',{}).get('creativeEvidence',{}).get('rejectedProposals',[])]
        attempted=len(qualifications)+len(rejected)
        costs=[s.get('costUsd') for _,s in entries]
        def rate(count, denominator=attempted):return count/denominator if denominator else None
        normalized_origin=normalize_origin(origin)
        real_eligible=normalized_origin=='REAL_AI_PROVIDER'
        reports.append({'evidenceOrigin':normalized_origin,'mode':mode,'provider':provider,'model':model,'attempts':n,
            'realProviderCapabilityStatisticsEligible':real_eligible,'officialAPlusCalibrationEligible':False,
            'aQualificationRate':qualified/n,'materialImprovementRate':rate(sum(bool(q.get('material')) for q in qualifications)),
            'canonicalRegressionRate':rate(sum(q.get('canonicalRegression',False) for q in qualifications)),
            'creativeRegressionRate':rate(sum(q.get('creativeRegression') is True for q in qualifications),sum(isinstance(q.get('creativeRegression'),bool) for q in qualifications)),
            'sourceFidelityFailureRate':rate(sum(r.get('classification') in ('STORY_FIDELITY_FAILED','STORY_CHANGE_REQUIRES_APPROVAL') for r in rejected)),
            'contractFailureRate':sum(s.get('decision',{}).get('state')=='CONTRACT_FAILURE' for _,s in entries)/n,
            'productionRiskRegressionRate':rate(sum(q.get('productionRiskRegression',False) for q in qualifications)+sum(r.get('classification')=='REGRESSION' for r in rejected)),
            'averageCallsToA':sum(r.get('providerCalls',0) for r,s in entries if s.get('decision',{}).get('state')=='A_QUALIFIED')/qualified if qualified else None,
            'calculatedCostUpperBoundPerA':sum(costs)/qualified if qualified and all(isinstance(c,(int,float)) for c in costs) else None,
            'primaryStopRate':sum(r.get('providerCalls')==1 and r.get('targetQualified') is True for r,_ in entries)/n,
            'escalationRate':sum(r.get('providerCalls',0)>1 for r,_ in entries)/n,
            'belowTargetAfterEscalationRate':sum(r.get('providerCalls',0)>1 and not r.get('targetQualified') for r,_ in entries)/n,
            'operatorAcceptanceRate':None,'audienceOutcome':None,'realCreativeEffectiveness':'UNVERIFIED' if real_eligible else 'EXCLUDED_NON_REAL_PROVIDER_EVIDENCE'})
    routes=defaultdict(list)
    for run in runs:routes[(normalize_origin(run.get('evidenceOrigin','UNKNOWN')),run.get('mode'))].append(run)
    routing=[]
    for (origin,mode),items in routes.items():
        qualified=[r for r in items if r.get('targetQualified') is True]
        costs=[r.get('calculatedCostUpperBoundUsd') for r in items]
        reviewed=[r for r in items if isinstance(r.get('operatorAcceptanceEvidence'),dict) and r['operatorAcceptanceEvidence'].get('persistedDecisionId')]
        routing.append({'evidenceOrigin':origin,'mode':mode,'runs':len(items),'aQualificationRate':len(qualified)/len(items),
            'realProviderCapabilityStatisticsEligible':origin=='REAL_AI_PROVIDER','officialAPlusCalibrationEligible':False,
            'averageCallsToA':sum(r.get('providerCalls',0) for r in qualified)/len(qualified) if qualified else None,
            'calculatedTotalCostUpperBoundPerA':sum(costs)/len(qualified) if qualified and all(isinstance(c,(int,float)) for c in costs) else None,
            'deepseekStopRate':sum(r.get('providerCalls')==1 and (r.get('stages') or [{}])[0].get('provider')=='deepseek' and r.get('targetQualified') is True for r in items)/len(items),
            'escalationRate':sum(r.get('providerCalls',0)>1 for r in items)/len(items),
            'belowAAfterEscalationRate':sum(r.get('providerCalls',0)>1 and not r.get('targetQualified') for r in items)/len(items),
            'operatorAcceptanceRate':sum(r['operatorAcceptanceEvidence'].get('accepted') is True for r in reviewed)/len(reviewed) if reviewed else None,
            'audienceOutcome':None})
    return {'version':'adaptive-optimization-metrics-v3','cohorts':reports,'routingCohorts':routing,'acceptanceSource':'EXPLICIT_IMMUTABLE_PROMPT_VERSION_PROVENANCE_ONLY'}
