"""Opt-in source-bound premise facts and independent admission criteria.

No response/contradiction enums, quality thresholds or compatibility policies are
added. Unresolved criteria remain unresolved; source prose is not a swap proof.
"""
from copy import deepcopy
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict
from .short_form_evidence import tokens

VERSION='premise-admission-opening-evidence-v1'


class ResponseEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    state: Literal['RESPONSE_MISSING','RESPONSE_PRESENT_CLASSIFIED','RESPONSE_PRESENT_UNCLASSIFIED','RESPONSE_PRESENT_INCOMPATIBLE','RESPONSE_AMBIGUOUS']
    sourceText: str
    classification: str | None
    diagnosisCategory: Literal['A','B','C','D','E','F','KNOWN_SUPPORTED']
    compatibility: Literal['SUPPORTED','INCOMPATIBLE','UNRESOLVED','NOT_APPLICABLE']
    evidenceRefs: list[dict]


def meaningful(value):
    return tokens(value)-set('action intended intendedly meant create makes make cause causes prevents prevent preventing impossible fails fail cannot never goal use using normal behavior expected actual response intended effect'.split())


def object_support(name,frame):
    """Literal label or source-spelled compound parts; no object-archetype mapping."""
    label=re.sub(r'[^a-z]','',name.casefold())
    words=set(re.findall(r'[a-z]+',frame.casefold()))
    literal=bool(name and re.search(r'\b'+re.escape(name)+r'\b',frame,re.I))
    joined=[w for w in words if len(w)>=3 and w in label]
    compound=any(a!=b and (a+b==label or b+a==label) for a in joined for b in joined)
    head=bool(name and len(name.split())>1 and name.split()[-1].casefold() in words)
    return dict(present=True if literal or compound or head else None,method='LITERAL_LABEL_OR_SOURCE_COMPOUND_PARTS_OR_LABEL_HEAD',matches=[w for w in joined if w in words])


def response_evidence(fields,canonical,baseline,model):
    rule=fields['impossibleRule'].strip();response=baseline['responseType']
    name=fields['primaryObject'].casefold();known_object=model['objects'].get(name)
    archetype=known_object['archetype'] if known_object else None
    from .premise_naturalness import _policy
    policy=_policy(archetype,response,model) if archetype else None
    ambiguous=bool(re.search(r'^\s*(?:unknown|unclear|maybe|perhaps|possibly|might|could|a mysterious indescribable)\b',rule,re.I))
    if not rule or re.fullmatch(r'(?:none|no response|n/a)[.\s]*',rule,re.I):
        state,category,compat='RESPONSE_MISSING','A','NOT_APPLICABLE'
    elif ambiguous:
        state,category,compat='RESPONSE_AMBIGUOUS','E','UNRESOLVED'
    elif response=='UNSUPPORTED_RESPONSE':
        state,category,compat='RESPONSE_PRESENT_UNCLASSIFIED','B','UNRESOLVED'
    elif policy:
        state,category,compat='RESPONSE_PRESENT_CLASSIFIED','KNOWN_SUPPORTED','SUPPORTED'
    elif known_object and archetype!='GENERIC':
        state,category,compat='RESPONSE_PRESENT_INCOMPATIBLE','C','INCOMPATIBLE'
    else:
        state,category,compat='RESPONSE_PRESENT_CLASSIFIED','D','UNRESOLVED'
    return ResponseEvidence(state=state,sourceText=rule,
        classification=None if response=='UNSUPPORTED_RESPONSE' else response,
        diagnosisCategory=category,compatibility=compat,evidenceRefs=canonical.facts['rule']['source'])


def opening_evidence(candidate,canonical,baseline):
    from .short_form_engine import _visual
    fields=canonical.fields;facts=canonical.facts;raw_frame=fields['frameZeroDescription'];frame=_visual(raw_frame);obj=object_support(fields['primaryObject'],raw_frame)
    requires_text=bool(re.search(r'caption|dialogue|narration|shouting bubble|speech bubble|reading text|text explains',raw_frame,re.I))
    source_short_name=fields['normalExpectation'].split()[0].casefold() if fields['normalExpectation'].split() else ''
    if source_short_name in fields['primaryObject'].casefold().split() and re.search(r'\b'+re.escape(source_short_name)+r'\b',raw_frame,re.I):
        obj['present']=True;obj['sourceShortName']=source_short_name
    character=bool(candidate.get('protagonist') and re.search(r'\b'+re.escape(candidate['protagonist'])+r'\b',raw_frame,re.I))
    # These phrases explicitly ask the reader to infer temporal behavior. A still
    # may show the problem but cannot establish the elapsed-time/direction claim.
    motion=bool(re.search(r'moving backward|slowly reappearing|reappearing|flickering|delayed|lag overlay|one second|two seconds',frame,re.I))
    prior=True if re.search(r'earlier|previous scene|as before|remember|already seen|prior context',frame,re.I) else None
    # Source property comparison is independent of response/object taxonomy.
    # It is a still-plan witness only with an explicit use pose and visible goal.
    pairs=[('straight','bent'),('closed','open'),('open','closed'),('dry','wet'),('clean','dirty')]
    contrasts=[dict(expected=x,shown=y) for x,y in pairs
        if re.search(r'\b'+x+r'\b',fields['normalExpectation'],re.I) and re.search(r'\b'+y+r'\b',frame,re.I)]
    colors={'blue','orange','red','green','white','black','yellow','purple','pink','gray','grey'}
    goal_colors=colors & set(re.findall(r'[a-z]+',fields['everydayGoal'].casefold()))
    frame_colors=colors & set(re.findall(r'[a-z]+',frame.casefold()))
    expected_color_witness=any(re.search(r'\b'+c+r'\s+(?:paint|bucket|brush)\b',frame,re.I) for c in goal_colors)
    actual_color_witness=[c for c in frame_colors-goal_colors if re.search(r'(?:painted\s+(?:patch|area|surface)|patch|wall)\s+(?:(?:is|turns?|becomes?|looks?|has become)\s+)?(?:(?:vivid|bright|pure|solid|now)\s+)*'+c+r'\b',frame,re.I)]
    if expected_color_witness and actual_color_witness and re.search(r'paint|color|colour',fields['normalExpectation'],re.I):
        contrasts.append(dict(expected=sorted(goal_colors),shown=sorted(actual_color_witness)))
    use_pose=bool(re.search(r'mid.stroke|mid.swing|mid.sweep|flipping|striking|brushing|painting',frame,re.I))
    source_contrast=bool(contrasts and use_pose and character and obj['present'] and facts['goal']['visibleInOpening']
                         and facts['opening']['anomalyPresent'] and facts['opening']['causalRelationshipVisible'])
    legacy_static=bool(baseline['staticFrameLegibility'] is not None and baseline['staticFrameLegibility']>=65)
    still_supported=bool(not motion and not prior and not requires_text and character and obj['present'] and facts['goal']['visibleInOpening'] and facts['opening']['problemPresent'] and (source_contrast or legacy_static))
    classification=('SOURCE_MISSING' if not raw_frame else 'EVIDENCE_SOURCE_MISMATCH' if not frame else 'MOTION_DEPENDENT_OPENING' if motion else
        'CAUSAL_RELATION_NOT_VISIBLE' if not facts['opening']['causalRelationshipVisible'] or not still_supported else
        'PRESENT_BUT_WEAK' if baseline['instantCausalLegibility']<60 else 'OTHER')
    return dict(frameZeroDescription=raw_frame,sourceFrameVisual=frame,requiresTextOrDialogue=requires_text,characterVisible=character,goalDeclared=facts['goal']['declared'],
        goalVisible=facts['goal']['visibleInOpening'],objectVisible=obj['present'],objectEvidence=obj,
        problemVisible=facts['opening']['problemPresent'],anomalyVisible=facts['opening']['anomalyPresent'],
        triggerVisible=facts['trigger']['visible'],goalProblemRelationship=facts['opening']['causalRelationshipVisible'],
        impossibleRelationVisible=True if still_supported else None,
        ruleInferableFromStill=True if still_supported else None,needsMotionToUnderstand=True if motion else None,
        motionInferenceScope='Explicit temporal claim requires a sequence to verify; the static goal/problem may still be visible.',
        needsPriorContext=prior,canonicalCausalLegibility=facts['opening']['causalRelationshipVisible'],
        stillCausalLegibility='SUPPORTED' if still_supported else 'UNRESOLVED',
        openingFactsState='OPENING_FACTS_PRESENT' if all([character,obj['present'],facts['opening']['problemPresent'],facts['goal']['declared']]) else 'OPENING_FACTS_INCOMPLETE',
        openingQualityState='OPENING_LEGIBILITY_STRONG' if still_supported else 'OPENING_LEGIBILITY_NOT_ESTABLISHED',
        stillPropertyContrast=contrasts,explicitUsePose=use_pose,sourceFunctionalContrastSupported=source_contrast,
        blockerClassification=classification,
        blockerReason=('Raw frame-zero source is present, but the existing visual-text sanitizer returned empty. This is extraction coverage, not absent source or proved poor opening. SFE remains unchanged.' if raw_frame and not frame else 'Score below60. Canonical fact overlap establishes declared/linked plan facts, not frozen-frame functional causality. Motion/context and exact-object contradiction may remain unresolved.'),
        evidenceRefs=facts['opening']['source'],
        scope='SOURCE_TEXT_PLAN_DIAGNOSTIC_NOT_OBSERVED_PIXELS; None means not established, never an invented yes/no.')


def quality_evidence(fields,canonical,baseline,response,model):
    goal=meaningful(fields['everydayGoal']);expectation=meaningful(fields['normalExpectation']);rule=meaningful(fields['impossibleRule'])
    relation=meaningful(fields['goalRuleRelationship']);why=meaningful(fields['whyThisObject']);obj=meaningful(fields['primaryObject'])
    effects=meaningful(' '.join(b['visibleConsequence'] for b in fields['beats']))
    function_matches=sorted((expectation & goal)-obj)
    effect_matches=sorted((goal & effects)-obj)
    rule_goal_relation=bool((relation & goal) and (relation & rule))
    prevention=bool(re.search(r'prevent\w*|impossible|cannot|can.t|never|fails?|instead|worse',fields['goalRuleRelationship'],re.I))
    direct=bool(canonical.facts['rule']['visible'] and rule_goal_relation and effect_matches and prevention)
    explicitly_portable=bool(re.search(r'any object|unrelated|arbitrary magic|random magic|no functional|regardless of (?:the )?object',fields['whyThisObject']+' '+fields['impossibleRule'],re.I))
    compatible=response.compatibility=='SUPPORTED'
    incompatible=response.compatibility=='INCOMPATIBLE' and response.classification!='ORDINARY_RESPONSE'
    goal_type='DIRECT' if direct else 'CONTRIVED' if incompatible or explicitly_portable else None
    if re.search(r'does not interfere|no interference',fields['goalRuleRelationship'],re.I):goal_type='NONE'
    known_dependency=compatible and baseline['objectSpecificityScore']>=70
    # A supplied whyThisObject statement is not independently verified substitution evidence.
    # The current canonical contract contains no cross-object counterfactual witnesses.
    independent_dependency=None
    return dict(
        normalExpectation=dict(present=bool(fields['normalExpectation']),source=fields['normalExpectation'],
            functionGoalMatches=function_matches,qualitySupport='SUPPORTED_SOURCE_LINK' if len(function_matches)>=2 else 'UNRESOLVED',
            limitation='Explicit expected function is a plan fact; correctness of an unknown object model is not independently verified.'),
        exactObjectRelevance=dict(source=fields['whyThisObject'],present=bool(fields['whyThisObject']),
            sourceFunctionMatches=sorted(why & (rule|expectation|goal)),
            qualitySupport='SUPPORTED' if known_dependency else 'CONTRADICTED' if incompatible or explicitly_portable else 'UNRESOLVED',
            independentlyVerified=known_dependency,independentCounterfactualEvidence=independent_dependency,
            reason='Configured functional swap dependency verified.' if known_dependency else
                'Existing known-object compatibility does not support this response, or source explicitly describes a portable unrelated effect.' if incompatible or explicitly_portable else
                'Why-this-object is explicit, but the supplied18 sources contain no independent cross-object swap/counterfactual witness. Unknown label is not the failure criterion.'),
        expectedBehaviorContradiction=dict(present=bool(fields['normalExpectation'] and fields['impossibleRule']),
            classification=baseline['contradictionType'],qualitySupport='SUPPORTED' if compatible else 'UNRESOLVED',
            expected=fields['normalExpectation'],actual=fields['impossibleRule']),
        goalInterference=dict(present=bool(fields['goalRuleRelationship']),source=fields['goalRuleRelationship'],classification=goal_type,
            qualitySupport='SUPPORTED_SOURCE_LINK' if direct else 'CONTRADICTED' if goal_type=='CONTRIVED' else 'UNRESOLVED',
            relationMatchesGoal=sorted(relation&goal),relationMatchesRule=sorted(relation&rule),visibleEffectGoalMatches=effect_matches,
            method='EXPLICIT_PREVENTION_PLUS_GOAL_RULE_EFFECT_LINKS_AND_ACCEPTED_CANONICAL_RULE_SUPPORT'),
        triggerNaturalness=dict(present=canonical.facts['trigger']['present'],source=fields['visibleTrigger'],
            classificationStatus=canonical.facts['trigger']['classificationStatus'],configuredScore=baseline['triggerNaturalness'],
            sourceExpectationMatches=sorted(meaningful(fields['visibleTrigger']) & expectation),
            qualitySupport='SUPPORTED' if compatible and baseline['triggerNaturalness']>=70 else 'UNRESOLVED',
            limitation='An explicit use-trigger is not automatically compatible with every object model.'),
        physicalRelationship=dict(source=fields['whyThisObject'],qualitySupport='SUPPORTED' if compatible else 'CONTRADICTED' if incompatible or explicitly_portable else 'UNRESOLVED'),
        arbitraryMagicRisk=dict(qualitySupport='HIGH' if incompatible or explicitly_portable else 'LOW' if compatible or response.classification=='ORDINARY_RESPONSE' else 'UNRESOLVED',
            explicitlyPortable=explicitly_portable,reason='Unknown taxonomy alone does not establish arbitrary magic.'),
        functionalIrony=dict(sourceExpected=fields['normalExpectation'],sourceActual=fields['impossibleRule'],
            qualitySupport='SUPPORTED' if compatible and baseline['functionalIrony']=='HIGH' else 'UNRESOLVED'),
    )


def assess(candidate,model,canonical):
    from . import premise_naturalness as natural
    canonical.assert_candidate(candidate)
    baseline=natural.assess(candidate,model,canonical_creative_evidence=canonical)
    fields=canonical.fields;response=response_evidence(fields,canonical,baseline,model)
    opening=opening_evidence(candidate,canonical,baseline)
    quality=quality_evidence(fields,canonical,baseline,response,model)
    if opening['sourceFunctionalContrastSupported']:
        for dimension in ('expectedBehaviorContradiction','functionalIrony','physicalRelationship','triggerNaturalness'):
            quality[dimension]['qualitySupport']='SUPPORTED_SOURCE_LINK'
            quality[dimension]['sourceWitness']=opening['stillPropertyContrast']
    result=deepcopy(baseline)
    unresolved=response.compatibility=='UNRESOLVED'
    missing=response.state=='RESPONSE_MISSING' or not fields['everydayGoal'] or not fields['primaryObject']
    ambiguous=response.state=='RESPONSE_AMBIGUOUS'
    low=quality['arbitraryMagicRisk']['qualitySupport']=='HIGH'
    result['responseType']=response.classification
    result['responseEvidenceState']=response.state
    result['legacyResponseClassification']=baseline['responseType']
    result['goalInterferenceType']=quality['goalInterference']['classification'] or (baseline['goalInterferenceType'] if response.compatibility=='SUPPORTED' else None)
    if missing or ambiguous:
        result['premiseNaturalness']='BROKEN';result['premiseReviewStatus']='BROKEN'
    elif unresolved:
        # Preserve conservative compatibility grade, but never diagnose missing/broken
        # just because a behavior lacks a response name. Real quality remains unresolved.
        result['premiseNaturalness']='CONTRIVED';result['premiseReviewStatus']='CONTRIVED'
        result['expectationDistance']=None
        result['functionalIrony']=None
        result['whyThisObject']=quality['exactObjectRelevance']['reason']
        result['objectSwapTest']=dict(classification=None,portableArchetypeFraction=None,comparisons=[],
            scope='UNRESOLVED_SOURCE_BOUND_COUNTERFACTUAL; absence of a mapped policy is not proof of portable random magic.')
    if low and not missing and not ambiguous:
        result['premiseNaturalness']='CONTRIVED';result['premiseReviewStatus']='ARBITRARY'
    # Keep the accepted opening formula's numeric outcomes for these18. The new
    # still-frame test can prevent an unsupported strong opening, never add a bonus.
    if opening['sourceFunctionalContrastSupported'] and opening['stillCausalLegibility']=='SUPPORTED':
        # Same 90/85 strong branch: the direct source contradiction is now
        # witnessed without a response name. No admission or object-swap credit.
        result['instantCausalLegibility']=90
        result['staticFrameLegibility']=85
        result['expectationDistance']='CLEAR_CONTRADICTION'
        opening['openingQualityState']='OPENING_LEGIBILITY_STRONG'
        opening['blockerClassification']='OTHER'
        opening['blockerReason']='No opening blocker: source goal/use pose/contrasting state witness satisfies the existing strong branch.'
    if result['instantCausalLegibility']>=60 and opening['stillCausalLegibility']!='SUPPORTED':
        result['instantCausalLegibility']=35 if canonical.facts['opening']['causalRelationshipVisible'] else 15
        result['staticFrameLegibility']=25 if canonical.facts['opening']['causalRelationshipVisible'] else 15
    result['admitted']=(result['premiseNaturalness'] in ('STRONG','ACCEPTABLE')
        and result['goalInterferenceType']=='DIRECT' and result['expectationDistance']=='CLEAR_CONTRADICTION')
    flags=[]
    for f in baseline['flags']:
        if unresolved and f['code'] in ('ARBITRARY_MAGIC_RELATIONSHIP','GENERIC_ENGINE_APPLICATION'):continue
        f=deepcopy(f)
        if f['code']=='CAUSE_NOT_VISIBLE_AT_FRAME_ZERO' and opening['stillCausalLegibility']=='SUPPORTED':continue
        if f['code']=='CAUSE_NOT_VISIBLE_AT_FRAME_ZERO':
            f['reason']=opening['blockerReason'];f['openingEvidenceClassification']=opening['blockerClassification']
        flags.append(f)
    if response.state in ('RESPONSE_MISSING','RESPONSE_AMBIGUOUS','RESPONSE_PRESENT_UNCLASSIFIED','RESPONSE_PRESENT_INCOMPATIBLE'):
        flags.append(dict(code=response.state,scope='EVIDENCE_STATE_NOT_AUTOMATIC_VERDICT'))
    if not quality['exactObjectRelevance']['independentlyVerified']:
        flags.append(dict(code='EXACT_OBJECT_DEPENDENCY_NOT_VERIFIED',reason=quality['exactObjectRelevance']['reason']))
    if low and not any(f['code']=='ARBITRARY_MAGIC_RELATIONSHIP' for f in flags):
        flags.append(dict(code='ARBITRARY_MAGIC_RELATIONSHIP',reason='A covered object-response pair is incompatible or source explicitly declares a portable unrelated effect.'))
    if opening['stillCausalLegibility']!='SUPPORTED':flags.append(dict(code='STILL_FRAME_CAUSALITY_NOT_ESTABLISHED',reason=opening['blockerReason']))
    result['flags']=flags
    result['evidenceMode']=VERSION
    result['responseEvidence']=response.model_dump()
    result['openingEvidence']=opening
    result['qualityEvidence']=quality
    result['qualityAssessmentStatus']='MISSING_OR_AMBIGUOUS' if missing or ambiguous else 'PRESENT_BUT_LOW_QUALITY' if low or response.classification=='ORDINARY_RESPONSE' else 'UNRESOLVED' if unresolved else 'ASSESSED'
    result['admissionEvidenceStatus']='UNSUPPORTED' if missing or ambiguous or low else 'KNOWN_SUPPORTED' if response.compatibility=='SUPPORTED' else 'UNCLASSIFIED_BUT_EVIDENCE_SUPPORTED'
    result['metricInterpretation']=dict(objectSpecificityScore='UNCHANGED_CONFIGURED_MODEL_ESTIMATE; unresolved comparison is not observed low specificity',
        triggerNaturalness='UNCHANGED_CONFIGURED_MODEL_ESTIMATE; unknown classification is not missing trigger',
        premiseNaturalness='CONSERVATIVE_COMPATIBILITY_GRADE; qualityAssessmentStatus distinguishes unresolved from proved weak')
    result['admissionCriteria']=dict(naturalnessSupported=result['premiseNaturalness'] in ('STRONG','ACCEPTABLE'),
        directGoalInterference=result['goalInterferenceType']=='DIRECT',clearContradiction=result['expectationDistance']=='CLEAR_CONTRADICTION',
        exactObjectDependency=quality['exactObjectRelevance']['qualitySupport'],
        responseCompatibility=response.compatibility,knownResponseLabelRequiredAtPresenceStage=False,
        taxonomyCoupledAdmissionDetected=unresolved,
        taxonomyDependentCriteriaRemainUnresolved=unresolved,
        unresolvedCriteria=[k for k,v in quality.items() if v.get('qualitySupport')=='UNRESOLVED'],
        exactRule='naturalness in {STRONG,ACCEPTABLE} AND goalInterferenceType=DIRECT AND expectationDistance=CLEAR_CONTRADICTION',
        reason='No automatic admission from field presence or label. No independent object-swap evidence supplied for the unclassified functional relationships; unresolved criteria remain unverified.')
    result['responseDiagnosis']=dict(responsePresent=response.state!='RESPONSE_MISSING',category=response.diagnosisCategory,
        classification=response.state,compatibility=response.compatibility,
        meaning='Source behavior existence and configured response/admission compatibility are separate.')
    return result
