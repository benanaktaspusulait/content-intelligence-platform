"""Run-local operations for the existing reconstruction pipeline; no persistence.

Only execute_request can construct a provider. Offline evaluation never borrows
parent IR, annotations or grades. All paid calls are separately durable in Java.
"""
from copy import deepcopy
import difflib
import hashlib
import json
import math
import re
import time
from .review import _run_canonical_evaluation
from .creative_reconstruction import diagnose, perform_reconstruction, request_payload, response_format, generation_system
from .creative_provider_profiles import CreativeCapabilityProvider, readiness
from .draft_comparative_review import config, schema as critic_schema, validate as validate_critic, SYSTEM as CRITIC_SYSTEM, INSTRUCTIONS, SCHEMA
from .owner_machine_pilot import schema as source_schema, validate as validate_source, source_events, SOURCE_SYSTEM, SINGLE, capture_accounting

VERSION = 'BOUNDED_OPTIMIZATION_LOOP_V1'
TARGET = 'CANONICAL_RULESET_1_11_A'
ROLES = ('GENERATION', 'SOURCE_FIDELITY', 'CRITIC')


def fingerprint(value):
    return hashlib.sha256((value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))).encode()).hexdigest()


def capabilities():
    observed=readiness()['profiles']
    return dict(version=VERSION, targets=[dict(id=TARGET, label='Canonical Ruleset 1.11: Grade A', supported=True, minimumScore=92), dict(id='CPQ_A_PLUS', supported=False, reason='No approved active calibrated A/A+ target contract is available')],
                profiles={k: {**config(k), 'configured':observed[k]['configured'], 'liveAvailability':observed[k]['liveAvailability'], 'allowedRoles': list(ROLES)} for k in ('deepseek-primary', 'openai-escalation')}, maxRounds=5, maxRequests=15, maxTotalUsd=20, maxRunSeconds=1800, officialCpqGrading='INACTIVE', renderAuthorized=False)


def canonical(prompt, scope):
    result = _run_canonical_evaluation({**scope['request'], 'prompt': prompt, 'canonicalRulesetVersion': '1.11'})
    if result['status'] != 'EVALUATED' or result.get('score') is None:
        raise ValueError('Actual canonical evaluation unavailable')
    return result


def rows(result):
    return {r['ruleId']: r for k in ('passedRules', 'failedRules', 'unknownRules', 'notApplicableRules') for r in result[k]}


def integrity(prompt, result):
    beats = result['videoPlanIR']['beats']
    recognized = sum(b.get('isAttempt') is True for b in beats)
    warnings = []
    # Contradictory source evidence is exposed, never converted into annotations.
    for b in beats:
        quote = b.get('sourceQuote', '')
        if not b.get('isAttempt') and re.search(r'\b(?:tries?\s+(?:once\s+)?to\s+(?:peel|pull)|continuing the same .{0,30}pulling)', quote, re.I):
            warnings.append(dict(classification='EVALUATOR_UNRELIABLE', ruleIds=['ATTEMPT_001', 'CHAR_002'], beatId=b['id'], sourceQuote=quote, reason='Source-directed recovery action conflicts with missing parsed attempt'))
    if recognized == 0 and rows(result).get('GENERATION_EXECUTABLE_ATTEMPTS', {}).get('outcome') == 'PASS':
        warnings.append(dict(classification='EVALUATOR_UNRELIABLE', ruleIds=['GENERATION_EXECUTABLE_ATTEMPTS'], reason='Zero-attempt executability PASS is vacuous, not production improvement'))
    return dict(status='POTENTIALLY_UNRELIABLE' if warnings else 'NO_DETECTED_CONTRADICTION', warnings=warnings, recognizedAttempts=recognized)


def evaluate(data):
    scope = data['scope']; prompt = data['prompt']; result = canonical(prompt, scope)
    from .creative_validity import assess as assess_creative_validity
    findings = []
    for r in rows(result).values():
        if r['outcome'] not in ('FAIL', 'UNKNOWN') and r['severity'] == 'PASS':
            continue
        category = 'EVIDENCE_REQUIRED' if r['outcome'] == 'UNKNOWN' or r.get('details', {}).get('failureBasis') == 'EVIDENCE_INCOMPLETE' else 'TEXT_REPAIRABLE'
        if r['ruleId'] == 'ATTEMPT_001': category = 'PROTECTED_STORY_CHANGE_REQUIRED'
        if r['outcome'] == 'PASS' and r['severity'] != 'PASS': category = 'FIXED_POLICY_CONSTRAINT'
        findings.append(dict(ruleId=r['ruleId'], classification=category, message=r['message']))
    context = generation_context(scope, prompt, result, data.get('feedback', {}))
    validity=assess_creative_validity(prompt,result,data.get('provenance'))
    return dict(canonical=result, integrity=integrity(prompt, result), diagnosis=diagnose(prompt, {**context,'creativeValidityDiagnosis':validity}),
                creativeValidity=validity, findings=findings, promptSha256=fingerprint(prompt), renderAuthorized=False)


def generation_context(scope, prompt, result, feedback):
    from .review import enrich_production_evidence
    from .creative_validity import assess as assess_creative_validity
    # Extract editable actions anew from the current full text, with original
    # approved story as a separate immutable contract in every round.
    request={k:v for k,v in scope['request'].items() if k not in ('structuredPlan','authorizationEvidence')}
    evidence = enrich_production_evidence({**request, 'prompt': prompt})
    from .optimization_distinctness import _beats
    feedback=dict(rejectionReason=feedback.get('rejectionReason'), sourceFidelity=feedback.get('sourceFidelity','UNKNOWN'), rejectedFailureModes=[dict(classification=r.get('classification'),reasons=r.get('reasons',[])) for r in feedback.get('rejectedProposals',[])], remainingFindings=[dict(ruleId=r['ruleId'],outcome=r['outcome'],severity=r['severity'],message=r['message']) for r in rows(result).values() if r['outcome'] in ('FAIL','UNKNOWN')][:20])
    anchors=[re.sub(r'^\d+(?:\.\d+)?-\d+(?:\.\d+)?s:\s*','',b['sourceQuote']).split('[',1)[0].split('->',1)[0].strip() for b in _beats(prompt)]
    creative_validity=assess_creative_validity(prompt,result,{'origin':'UNKNOWN_ORIGIN','reviewerIndependent':False})
    return dict(optimizationGenerationContractVersion='creative-reconstruction-v2', optimizationGenerationInstructionsVersion='model-authored-production-v2',
                adaptiveVersion='adaptive-creative-optimization-v3', openingStrategy=scope['request'].get('openingStrategy', 'AUTO'),
                baselineCanonicalEvaluation=result, baselineCanonicalFailures=result.get('failedRules', []), approvedStoryText=scope['approvedStory']['text'],
                creativeValidityDiagnosis=creative_validity,
                storyRevisionId=scope['approvedStory']['revision'], storyApprovalRecordId=scope['approvedStory']['approvalRecordId'],
                essentialEvents=anchors, protectedIntent=scope['request'].get('protectedIntent', []),
                targetConfiguration=dict(contentProfile=scope['request']['contentProfile'], generator=scope['request']['generator'], duration=scope['request']['desiredDuration'], settings=scope['request']['settings']),
                targetAwarePreflight=scope.get('targetAwarePreflight', {}),
                escalationBrief=dict(originalProtectedStory=scope['approvedStory']['text'], originalBaseline=scope['baselinePrompt'], currentBestPrompt=prompt, remainingWeaknesses=feedback, ownerInterpretations=scope.get('ownerDecisions', [])),
                autonomousSingleCandidate=True)


def source_input(scope, prompt, candidate_id):
    story = scope['approvedStory']; settings = scope['settings']; original = scope['baselinePrompt']
    old = re.findall(r'(?m)^\d+(?:\.\d+)?-\d+(?:\.\d+)?s:.*$', original)
    new = re.findall(r'(?m)^\d+(?:\.\d+)?-\d+(?:\.\d+)?s:.*$', prompt)
    changes = [dict(beatId=f'beat_{i+1:02}', originalExecution=a, newExecution=b) for i, (a,b) in enumerate(zip(old,new)) if a != b]
    binding = dict(promptSha256=fingerprint(prompt), approvedStorySha256=fingerprint(story['text']), productionSettingsSha256=fingerprint(settings), sourceIdentity=candidate_id, storyId=str(story['storyId']), revision=str(story['revision']), approvalRecordId=str(story['approvalRecordId']))
    return dict(policyVersion='OWNER_MACHINE_PILOT_V1', purpose='SOURCE_FIDELITY', evidenceType='MACHINE_REVIEW', evaluationUnit=SINGLE,
                ownerInterpretations=scope.get('ownerDecisions', []), packets=[dict(neutralId='Q01', prompt=prompt, promptSha256=fingerprint(prompt), productionSettings=settings, approvedStory=story['text'], sourceBinding=binding, requiredEvents=source_events(story['text']), changedBeats=changes)])


def critic_input(scope, prompt, order=0):
    packets=[dict(label='A',prompt=scope['baselinePrompt']),dict(label='B',prompt=prompt)]
    return dict(purpose='DRAFT_COMPARATIVE_REVIEW_V1', instructionVersion=INSTRUCTIONS, responseSchemaVersion=SCHEMA,
                reviewerInstructions='Compare both exact texts. Each preference requires literal excerpts from both sides or a concrete missing-evidence explanation. No intended winner or source verdict is supplied.', productionSettings=scope['settings'], packets=packets if order%2==0 else list(reversed(packets)))


def parts(data):
    role=data['role']; scope=data['scope']; prompt=data['prompt']
    if role == 'GENERATION':
        c=canonical(prompt,scope);context=generation_context(scope,prompt,c,data.get('feedback',{}))
        payload=request_payload(prompt,context);fmt=response_format(context,prompt)
        # One generation round means one proposal; optional self-revision remains
        # in that same single inference, never a second round/call.
        fmt=deepcopy(fmt);fmt['json_schema']['schema']['properties']['proposals']['maxItems']=1
        payload['maxCandidates']=1
        return generation_system(context),json.dumps(payload,ensure_ascii=False),fmt,context
    if role == 'SOURCE_FIDELITY':
        d=source_input(scope,prompt,data['candidateId'])
        system=SOURCE_SYSTEM+' Review exactly one subject. Echo sourceBinding. Map every requiredEvents full source span, all six anchors and every complete changed-beat newExecution. Owner interpretations are OWNER_DECISION, never a replacement for your raw verdict. Missing support remains UNKNOWN. Single-event coverage is mandatory; bounded consecutive EVENT_ORDER citations do not replace it.'
        return system,json.dumps(d,ensure_ascii=False),dict(type='json_schema',json_schema=dict(name='loop_source',strict=True,schema=source_schema(True,True))),d
    if role == 'CRITIC':
        d=critic_input(scope,prompt,data.get('round',0))
        return CRITIC_SYSTEM,json.dumps(d,ensure_ascii=False),dict(type='json_schema',json_schema=dict(name='loop_critic',strict=True,schema=critic_schema())),d
    raise ValueError('Unauthorized role')


def preflight(data):
    auth=data['authorization'];cfg=config(auth['profileId'])
    if data['role'] not in ROLES: raise ValueError('Unsupported role')
    for k in ('provider','model','reasoningEffort'):
        if auth.get(k)!=cfg[k]: raise ValueError('Exact current profile configuration required')
    tokens=auth['maxOutputTokens']; cap=auth['maxCostUsd']
    if type(tokens) is not int or not 1024 <= tokens <= cfg['reviewMaxOutputTokens']:raise ValueError('Role output limit outside configured bounds')
    system,prompt,fmt,context=parts(data)
    bound=len((system+prompt+json.dumps(fmt)).encode())+1000
    estimate=(bound*cfg['inputUsdPerMillion']+tokens*cfg['outputUsdPerMillion'])/1e6
    if not isinstance(cap,(int,float)) or not math.isfinite(cap) or cap<estimate or bound+tokens>cfg['contextTokens']:raise ValueError('Insufficient bounded request reservation/context')
    return dict(inputTokenUpperBound=bound,maxCalculatedCostUsd=estimate,effectiveConfiguration={**cfg,'maxOutputTokens':tokens,'maxCostUsd':cap})


def preview(data):
    """Compile the outbound role request without constructing a provider."""
    checked=preflight(data)
    system,prompt,fmt,context=parts(data)
    return {
        **checked,
        'systemSha256':fingerprint(system),
        'userPayloadSha256':fingerprint(prompt),
        'responseSchemaSha256':fingerprint(fmt),
        'instructionContextSha256':fingerprint({'system':system,'context':context,'responseSchema':fmt}),
        'sourceScopeSha256':fingerprint(data['scope']),
        # This is a routing assertion, not evidence that a provider ran.  The
        # bounded optimization endpoint has no fixture-provider fallback: its
        # only executable factory is the checked-in real capability adapter.
        'transportOrigin':'REAL_PROVIDER_ADAPTER',
        'providerAdapter':'CreativeCapabilityProvider',
        'fixtureFallbackAllowed':False,
        'providerDispatched':False,
    }


def execute_request(data, provider_factory=None):
    factory=provider_factory or CreativeCapabilityProvider
    pre=preflight(data);auth=data['authorization'];cfg=pre['effectiveConfiguration'];system,prompt,fmt,context=parts(data)
    timeout=min(120,max(1,int(data['timeoutSeconds'])))
    provider=factory(cfg,auth['maxOutputTokens'],timeout);provider.response_format=fmt
    start=time.monotonic()
    envelope=dict(executionStatus='FAILED_OR_AMBIGUOUS',role=data['role'],requestId=data['requestId'],provider=cfg['provider'],model=cfg['model'],effectiveRequestConfiguration=cfg,providerDispatched=False,
                  providerOutcome='NOT_DISPATCHED',billingStatus='NO_USAGE_REPORTED',processingOutcome='NOT_STARTED')
    try:
        envelope['providerDispatched']=True
        if data['role']=='GENERATION':
            # Existing compiler and validators; only the transported format is
            # tightened to one candidate by the run-local context hook.
            result=perform_reconstruction(data['prompt'],context,provider,cfg['model'])
            if len(result['result']['candidates'])>1:raise ValueError('One candidate per generation round required')
            envelope['result']=result['result']
        else:
            raw=provider.complete(prompt,system=system,temperature=0)
            provider.last_raw_response=raw
            value=json.loads(raw)
            envelope['result']=validate_critic(value,context) if data['role']=='CRITIC' else dict(results=validate_source(value,context))
        envelope.update(rawResponse=getattr(provider,'last_raw_response',''),usage=getattr(provider,'last_usage',None),providerMetadata=getattr(provider,'last_response_metadata',{}))
        capture_accounting(envelope,cfg)
        if envelope['usageAccountingStatus']!='COMPLETE' or envelope['costUsd']>auth['maxCostUsd'] or envelope['usage']['completion_tokens']>auth['maxOutputTokens']:raise ValueError('Incomplete/out-of-bound accounting')
        if envelope['providerMetadata'].get('finishReason')!='stop' or envelope['providerMetadata'].get('model')!=cfg['model']:raise ValueError('Incomplete or changed provider response')
        envelope['executionStatus']='COMPLETED';envelope['providerOutcome']='RESPONSE_RECEIVED'
        envelope['billingStatus']='KNOWN_INCURRED';envelope['processingOutcome']='ACCEPTED_RESEARCH_RESULT'
        if data['role']=='GENERATION' and not envelope['result'].get('candidates'):
            rejected=envelope['result'].get('rejectedProposals',[])
            envelope['processingOutcome']='PLAN_REJECTED_'+(rejected[0].get('classification','VALIDATION') if rejected else 'NO_JUSTIFIED_IMPROVEMENT')
    except Exception as error:
        envelope.update(rawResponse=getattr(provider,'last_raw_response',''),usage=getattr(provider,'last_usage',None),providerMetadata=getattr(provider,'last_response_metadata',{}))
        capture_accounting(envelope,cfg)
        received=bool(envelope['rawResponse'] or envelope['providerMetadata'])
        message=str(error)
        if received:
            outcome=('SOURCE_FIDELITY_FAILED' if 'STORY_FIDELITY' in message else
                     'STRUCTURED_RESPONSE_INVALID' if type(error).__name__ in {'ValidationError','JSONDecodeError'} else
                     'LOCAL_COMPILER_VALIDATION_FAILED')
            envelope.update(providerOutcome='RESPONSE_RECEIVED',billingStatus='KNOWN_INCURRED' if envelope.get('usageAccountingStatus')=='COMPLETE' else 'USAGE_ACCOUNTING_INCOMPLETE',processingOutcome=outcome)
        else:
            envelope.update(providerOutcome='DISPATCH_AMBIGUOUS' if envelope['providerDispatched'] else 'NOT_DISPATCHED',billingStatus='UNKNOWN' if envelope['providerDispatched'] else 'NO_USAGE_REPORTED',processingOutcome='PROVIDER_TRANSPORT_FAILED')
        envelope['failure']=dict(layer='RECONSTRUCTION_OR_REVIEW' if received else 'PROVIDER_TRANSPORT',exceptionCategory=type(error).__name__,failureCategory=envelope['processingOutcome'],httpStatus=getattr(error,'status_code',None),providerRequestId=getattr(error,'request_id',None),responseReceived=received,usageAccountingStatus=envelope.get('usageAccountingStatus'),billingStatus=envelope['billingStatus'],timeoutSeconds=timeout,retrySafe=False)
    envelope['elapsedSeconds']=time.monotonic()-start
    return envelope


def compare(data):
    scope=data['scope'];candidate=data['candidate'];prompt=candidate['prompt'];evaluation=evaluate(dict(scope=scope,prompt=prompt));base=data['baselineEvaluation'];parent=data['parentEvaluation']
    current=evaluation['canonical']; original=base['canonical'];delta=current['score']-original['score']
    warnings=evaluation['integrity']['warnings']
    # Score recovery driven by recognition is recorded, never creative progress.
    recognition_changed=evaluation['integrity']['recognizedAttempts']!=parent['integrity']['recognizedAttempts']
    source=data.get('sourceReview',{});critic=data.get('criticReview',{})
    source_verdict=(source.get('results') or [{}])[0].get('decision','UNKNOWN')
    from .creative_reconstruction import assess_candidate
    from .critic import LocalExecutionCritic
    from .review import enrich_production_evidence
    req={k:v for k,v in scope['request'].items() if k not in ('structuredPlan','authorizationEvidence')}
    req['prompt']=prompt
    local_critic=LocalExecutionCritic().review(req,enrich_production_evidence(req),dict(capabilityStatus='SUPPORTED',selectedGenerator=scope['request']['generator']))
    checked=deepcopy(candidate);checked['review']=dict(canonicalRuleEvaluation=current,executionReview=local_critic)
    validation=assess_candidate(data['parentPrompt'],checked,generation_context(scope,data['parentPrompt'],parent['canonical'],{}),parent['canonical']['score'])
    material=bool(candidate.get('creativeAssessment',{}).get('changeContract'))
    serious=bool(candidate.get('creativeAssessment',{}).get('critique',{}).get('reasons')) or validation.get('classification') in ('REGRESSION','STORY_FIDELITY_FAILED')
    from .adaptive_optimization import points
    from app.quality.family_weights import CANONICAL_FAMILY_WEIGHTS
    def terms(c):
        rr=rows(c);families={}
        for r in rr.values():
            if points(r) is not None: families.setdefault(r['family'],[]).append(r)
        den=sum(CANONICAL_FAMILY_WEIGHTS.get(f,.05) for f in families)
        return {k:dict(eligible=points(r) is not None,contribution=points(r)*CANONICAL_FAMILY_WEIGHTS.get(r['family'],.05)/den/len(families[r['family']]) if points(r) is not None else None,familyRows=len(families.get(r['family'],[]))) for k,r in rr.items()}
    before_terms,after_terms=terms(parent['canonical']),terms(current)
    exclusions=[k for k in before_terms if before_terms[k]['eligible'] and not after_terms[k]['eligible']]
    evidence_exclusion_gain=bool(exclusions) and current['score']>parent['canonical']['score']
    allowed=not warnings and not serious and not evidence_exclusion_gain and source_verdict=='PASS'
    best=allowed and current['score']>=parent['canonical']['score'] and material and not recognition_changed
    support=critic.get('overall',{}).get('judgment')=='B_BETTER' and not critic.get('overall',{}).get('blockingRegressions')
    reached=not warnings and not serious and not evidence_exclusion_gain and source_verdict!='FAIL' and current['score']>=92 and material and not recognition_changed
    return dict(evaluation=evaluation,sourceFidelity=source_verdict,materiality='SOURCE_BOUND_PRODUCTION_HYPOTHESIS' if material else 'EQUIVALENT',
                numericalDeltaFromOriginal=delta,numericalDeltaFromParent=current['score']-parent['canonical']['score'],recognitionChanged=recognition_changed,
                progressKind='PARSER_RECOGNITION_CHANGE' if recognition_changed else 'CANONICAL_NUMERIC_PROGRESS' if delta>0 else 'SAME_SCORE_PRODUCTION_HYPOTHESIS',
                retained=best,independentSupport=support,executionRiskReview=local_critic,compilerAssessment=validation,evidenceExclusionGain=evidence_exclusion_gain,excludedPreviouslyScoredRows=exclusions,scoreTermsBefore=before_terms,scoreTermsAfter=after_terms,targetState='TARGET_REACHED_REVIEW_REQUIRED' if reached else 'BELOW_TARGET',
                rejectionReason='EVALUATION_INTEGRITY_PROBLEM' if warnings or evidence_exclusion_gain else 'SOURCE_FIDELITY_REVIEW_REQUIRED' if source_verdict!='PASS' else 'REGRESSION' if current['score']<parent['canonical']['score'] or serious else 'NO_DEFENSIBLE_PROGRESS' if not best else '',
                ruleChanges=[dict(ruleId=k,before=rows(parent['canonical']).get(k),after=r) for k,r in rows(current).items() if rows(parent['canonical']).get(k)!=r],
                exactDiff=''.join(difflib.unified_diff(scope['baselinePrompt'].splitlines(keepends=True),prompt.splitlines(keepends=True),fromfile='original',tofile='run-draft')),
                renderAuthorized=False,officialCpqGrading='INACTIVE')
