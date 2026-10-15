"""Offline, source-bound comparison. Similarity never proves semantic equivalence."""
from copy import deepcopy
from difflib import SequenceMatcher
from .optimization_distinctness import _beats, _signature, _coverage_groups, validate_execution_candidates
from .optimization_profile_contract import normalize_candidate_profiles

COMPARISON_CONTRACT='optimization-value-and-approval-v1'

def assess_comparison(source,candidates,context,baseline_score=None):
    if context.get('optimizationGenerationContractVersion') == 'creative-reconstruction-v2':
        from .creative_reconstruction import assess_candidate, VERSION
        identities = [c.get('candidateId') for c in candidates]
        complete = len(candidates) <= 2 and len(set(identities)) == len(identities) and all(i in ('candidate-a','candidate-b') for i in identities)
        duplicate = len(candidates) == 2 and candidates[0].get('prompt') == candidates[1].get('prompt')
        assessments = [assess_candidate(source,c,context,baseline_score) for c in candidates]
        if not complete or duplicate:
            for item in assessments: item.update(approvalEligible=False,approvalBlockReason='Invalid or duplicate candidate set')
        eligible = any(x['approvalEligible'] for x in assessments)
        return {'contractVersion':VERSION,'integrityStatus':'COMPLETE_CANDIDATE_SET' if complete else 'INCOMPLETE_CANDIDATE_SET',
                'actualCandidateCount':len(candidates),'recommendation':'REVIEW_MATERIAL_CANDIDATE' if eligible else 'KEEP_ORIGINAL',
                'conclusion':'Review source-bound execution changes; creative benefit remains unverified.' if eligible else 'No defensible material improvement available. Keep Original.',
                'baselineScore':baseline_score,'candidates':assessments,'providerCalls':0,'rawCandidatesPreserved':True}
    originals=deepcopy(candidates);values=deepcopy(candidates);baseline=_beats(source)
    complete=len(values)==2 and [c.get('candidateId') for c in values]==['candidate-a','candidate-b']
    duplicate=len(values)==2 and values[0].get('prompt')==values[1].get('prompt')
    assessments=[]
    for i,c in enumerate(values):
        similarity=SequenceMatcher(None,source,str(c.get('prompt','')),autojunk=False).ratio()
        item={'candidateId':c.get('candidateId'),'contractVersion':COMPARISON_CONTRACT,
              'textSimilarity':round(similarity,5),'similarityScreen':'HIGH_SIMILARITY_REVIEW' if similarity>=.90 else 'TEXT_DIFFERENCES_PRESENT',
              'classification':'STRUCTURALLY_INVALID','approvalEligible':False,'actualChanges':[],
              'qualityScore':c.get('review',{}).get('canonicalRuleEvaluation',{}).get('score'),
              'scoreDelta':c.get('review',{}).get('canonicalRuleEvaluation',{}).get('score')-baseline_score if isinstance(c.get('review',{}).get('canonicalRuleEvaluation',{}).get('score'),(int,float)) and isinstance(baseline_score,(int,float)) else None,
              'evidenceLabels':['OBSERVED_TEXTUAL_CHANGE','DETERMINISTIC_VALIDATION_RESULT','CREATIVE_HYPOTHESIS','UNKNOWN_UNTIL_RENDER'],
              'unknowns':['Semantic story fidelity remains UNKNOWN.','First-frame causal readability requires visual review.','Seedance success and viewer response are unmeasured.'],
              'generatorFeasibility':'UNKNOWN_UNTIL_RENDER','storyCoverage':'UNKNOWN','endingPreservation':'UNKNOWN'}
        try:
            if not complete:raise ValueError(f'Incomplete comparison: expected candidate-a and candidate-b, received {len(values)} candidate(s).')
            if duplicate:raise ValueError('Duplicate candidates; no independent alternative.')
            if not isinstance(c.get('prompt'),str) or not c['prompt'].strip():raise ValueError('Candidate prompt is missing.')
            if any(anchor not in c['prompt'] for anchor in context.get('essentialEvents',[])):raise ValueError('Essential source event missing.')
            normalize_candidate_profiles(source,[c],context)
            beats=_beats(c['prompt']);groups=_coverage_groups(baseline,beats,context.get('essentialEvents'),c['candidateId'])
            try:validate_execution_candidates(source,values,context,candidate_indices={i})
            except ValueError as error:
                if 'materially unchanged execution' in str(error):
                    item.update(classification='BASELINE_EQUIVALENT',conclusion='No different execution decisions from baseline.',approvalBlockReason='Baseline-equivalent candidate cannot be approved.')
                    assessments.append(item);continue
                raise
            changed=[];motion=False;framing=False;timing=False
            for original,group in zip(baseline,groups):
                before=_signature(original);after=[_signature(b) for b in group]
                if len(group)>1:
                    changed.append(f"{original['id']}: one source progression split into {len(group)} camera shots; action and consequence unchanged.")
                    timing=True
                elif before[:2]!=after[0][:2]:
                    changed.append(f"{original['id']}: timing {before[0]}–{before[1]}s → {after[0][0]}–{after[0][1]}s.");timing=True
                if any(before[2]!=a[2] for a in after):
                    changed.append(f"{original['id']}: framing {before[2] or 'UNSPECIFIED'} → {after[0][2] or 'UNSPECIFIED'}.");framing=True
                if any(before[3]!=a[3] for a in after):
                    changed.append(f"{original['id']}: camera motion {before[3] or 'UNSPECIFIED'} → {after[0][3] or 'UNSPECIFIED'}.");motion=True
            material=motion or (framing and timing)
            if c.get('executionPlan'):
                from .optimization_plans import compile_plan
                compiled=compile_plan(source,context,c['executionPlan'])
                if compiled['prompt']!=c['prompt']:raise ValueError('Plan-first prompt does not match its validated deterministic compilation')
                material=True
                for change in c['executionPlan']['changes']:
                    bindings=' → '.join(x['quote'] for x in change['focusBindings'])
                    if change['stagingMode']=='CAUSE_EFFECT_SAME_FRAME': detail='simultaneous causal staging of '+bindings
                    elif change['stagingMode']=='ACTION_CONSEQUENCE_PAIR': detail='continuous source action/consequence focus: '+bindings
                    else: detail='explicit ordered state holds: '+' → '.join(x['quote'] for x in change['stateSequence'])
                    changed.append(change['sourceBeatId']+': '+detail+'; source story action and consequence preserved.')
                item['planValidation']=compiled['planValidation']

            minor_reason=('Framing label changes, but stronger opening clarity is unproven.' if framing and not timing else
                          'Timing boundaries change, but source actions and consequences remain unchanged; pacing improvement is unproven.')
            item.update(classification='VALID_WITH_UNPROVEN_BENEFIT' if material else 'VALID_MINOR_VARIATION',
                        materiality='MATERIAL_EXECUTION_INTERVENTION' if material else 'MINOR_EXECUTION_VARIATION',
                        actualChanges=changed,validationStatus='SOURCE_TEXT_CONTRACT_PASSED',
                        sourceEventCount=len(baseline),cameraShotCount=len(beats),baselineShotCount=len(baseline),
                        temporalComplexity='INCREASED_SHOT_COUNT' if len(beats)>len(baseline) else 'SAME_SHOT_COUNT',
                        productionRiskChange='Additional temporal transitions require review.' if len(beats)>len(baseline) else 'No validated production-risk reduction.',
                        storyCoverage='SOURCE_EVENTS_COVERED; SEMANTIC_FIDELITY_UNKNOWN',endingPreservation='PROTECTED_ENDING_TEXT_PRESERVED',
                        conclusion='Concrete execution intervention; creative benefit remains unproven.' if material else minor_reason,
                        approvalEligible=material,approvalBlockReason=None if material else 'No material intervention beyond framing labels or timing boundaries; keep the original.')
        except (ValueError,KeyError,TypeError) as error:
            item.update(validationStatus='CURRENT_CONTRACT_FAILED',conclusion=str(error),approvalBlockReason=str(error))
        assessments.append(item)
    eligible=[x for x in assessments if x['approvalEligible']]
    return {'contractVersion':COMPARISON_CONTRACT,'integrityStatus':'COMPLETE_TWO_CANDIDATES' if complete else 'INCOMPLETE_CANDIDATE_SET',
            'actualCandidateCount':len(values),'recommendation':'REVIEW_MATERIAL_CANDIDATE' if eligible else 'KEEP_ORIGINAL',
            'conclusion':'Review the material execution hypothesis; benefit is not demonstrated.' if eligible else 'Neither candidate demonstrates a defensible improvement over the saved baseline. Keep Original.',
            'baselineScore':baseline_score,'candidates':assessments,'providerCalls':0,'rawCandidatesPreserved':True}
