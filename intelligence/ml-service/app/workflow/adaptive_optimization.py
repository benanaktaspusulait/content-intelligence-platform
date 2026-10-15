"""V3 policy helpers for the existing creative workflow. No provider or persistence.

Inputs to this module come from backend-loaded immutable evidence, never browser
claims. Numeric grades remain exclusively the canonical rule engine's contract.
"""
from collections import defaultdict
from math import isfinite
from app.quality.family_weights import CANONICAL_FAMILY_WEIGHTS
from .creative_reconstruction import DIMENSIONS

VERSION = 'adaptive-creative-optimization-v3'
A_MINIMUM = 92
MODES = ('DEEPSEEK_ONLY', 'OPENAI_ONLY', 'ADAPTIVE')
FIXED_PASS = {'MINI_STORY_LOCK','GOAL_VISIBLE_EARLY','TEMPORAL_COMPLEXITY_SPLIT_GATE','BEAT_DENSITY_RULE'}


def rows(canonical):
    return sum((canonical.get(k, []) for k in ('passedRules','failedRules','unknownRules','notApplicableRules')), [])


def points(row):
    if row.get('outcome') not in ('PASS','FAIL') or row.get('details',{}).get('failureBasis') == 'EVIDENCE_INCOMPLETE':
        return None
    severity = row.get('severity')
    return (100 if severity == 'PASS' else 85) if row['outcome']=='PASS' else {'BLOCKER':0,'CRITICAL':40}.get(severity,70)


def feasibility(canonical, source='', context=None):
    """Conditional fixed-evidence ceiling, never impute unknown observations.

    Protected event windows, story and rule semantics are held fixed. Additional
    independent evidence changes the denominator and requires a fresh audit.
    """
    context=context or {}
    if canonical.get('status')!='EVALUATED' or canonical.get('rulesetVersion')!='1.11':
        return {'version':VERSION,'state':'CONTRACT_FAILURE','generationAllowed':False,'reasons':['A feasibility requires a complete current Ruleset 1.11 evaluation.']}
    families=defaultdict(list)
    for row in rows(canonical):
        if points(row) is not None: families[row['family']].append(row)
    denominator=sum(CANONICAL_FAMILY_WEIGHTS.get(f,.05) for f in families)
    if not denominator:
        return {'version':VERSION,'state':'TARGET_BLOCKED_BY_EVIDENCE','generationAllowed':False,'reasons':['No numeric canonical evidence.']}
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
                maximum=value;kind='EVALUATOR_DEFECT';reason='Fragile-interaction substring tags need independent audit; no score change or source-word removal is authorized.'
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
    return {'version':VERSION,'state':state,'generationAllowed':matches and ceiling>=A_MINIMUM and not visual_missing,'canonicalGradeContract':{'minimumA':A_MINIMUM,'minimumB':80,'aPlusExists':False},'currentScore':current,'fixedEvidenceOptimisticCeiling':ceiling,'ceilingScope':'CURRENT_ELIGIBLE_ROWS_AND_PROTECTED_EVENTS; new independent evidence requires recomputation','familyWeightDenominator':denominator,'losses':losses,'missingEvidence':missing,'genuineSourceAttemptCount':len(attempts),'reasons':(['Persisted score does not match authoritative aggregation.'] if not matches else ['Required independent visual evidence is missing.'] if ceiling>=A_MINIMUM and visual_missing else [] if ceiling>=A_MINIMUM else ['No defensible prompt-only path to A with current evidence and protected story.']), 'renderAuthorized':False}


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
    return {'candidateId':candidate.get('candidateId'),'qualified':qualified,'material':material,'regression':regression,'canonicalScore':score,'canonicalGrade':canonical.get('grade'),'sameRuleset':same_ruleset,'sourceFidelity':candidate.get('sourceEventCoverage',{}).get('semanticFidelity','UNKNOWN'),'blockingRules':blockers,'missingApplicableEvidence':gaps,'draftLabel':'TARGET-QUALIFIED FINAL CANDIDATE' if qualified else 'BEST AVAILABLE DRAFT','dimensions':quality_dimensions(candidate),'renderAuthorized':False}


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
