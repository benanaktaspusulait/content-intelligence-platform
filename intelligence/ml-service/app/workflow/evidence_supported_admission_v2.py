"""Independent premise admission: known compatibility OR source-supported factors.

No taxonomic classes, Naturalness scores or downstream thresholds are changed.
Decisions are source-bound planned-evidence inferences, never observed physics.
"""
from copy import deepcopy
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict
from . import premise_naturalness as natural
from .concept_fingerprint import digest
from .short_form_evidence import tokens
from .beat_consequence_evidence import action_evidence

VERSION='evidence-supported-premise-admission-v2'
OPENING_FLOOR=60  # Exact existing production opening floor; not configurable here.


class AdmissionDecision(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    version: Literal['evidence-supported-premise-admission-v2']=VERSION
    admitted: bool
    status: Literal['ADMITTED_KNOWN_COMPATIBILITY','ADMITTED_EVIDENCE_SUPPORTED_UNCLASSIFIED',
        'NOT_ADMITTED_INSUFFICIENT_EVIDENCE','NOT_ADMITTED_INCOMPATIBLE','NOT_ADMITTED_ARBITRARY',
        'NOT_ADMITTED_OPENING_WEAK','NOT_ADMITTED_RULE_INCOHERENT']
    provenance: Literal['KNOWN_COMPATIBILITY','EVIDENCE_SUPPORTED_UNCLASSIFIED','NONE']
    coverage: Literal['KNOWN_TAXONOMY_SUPPORTED','EVIDENCE_SUPPORTED_UNCLASSIFIED','UNSUPPORTED','INCOMPATIBLE']
    responseClassificationStatus: str
    responseClassification: str | None
    openingMandatory: bool
    openingPassed: bool
    corePremiseSupported: bool
    productionOpeningRequirementSatisfied: bool
    factors: dict
    reasons: list[dict]
    sourceContextSha256: str | None
    evidenceScope: str='SOURCE_BOUND_PLAN_INFERENCE_NOT_OBSERVED_PIXELS'


FUNCTION_STOP=set('the a an object thing objects normal action behavior behaviour expected ordinary function response event happens does do did core should may can might any just only intended impossible goal instead same other different now new more less expected time each every whenever always gives makes causes meant itself primary'.split())
PLACEHOLDER=re.compile(r'^\s*(?:|none|n/a|unknown|unclear|no (?:trigger|response)|something happens|an event occurs|unspecified|not shown)[.\s]*$',re.I)


def terms(text):return tokens(text)-FUNCTION_STOP


def source_ref(field,text):
    return dict(sourceField=field,sourceText=text,confidence='EXPLICIT_SOURCE')


def coherence_findings(fields):
    """Check explicit source constraints, not a whitelist of response classes.

    Absence of a detected contradiction is not semantic proof. Findings retain
    exact source spans so an editor can challenge any interpretation.
    """
    rule=fields['impossibleRule'];lower=rule.casefold();findings=[]
    def positive_match(pattern,text):
        for match in re.finditer(pattern,text,re.I):
            prefix=text[max(0,match.start()-25):match.start()]
            if not re.search(r'\b(?:not|never|no|cannot)\s+(?:the\s+|a\s+|an\s+)?$',prefix,re.I):
                return match
        return None
    def add(code,i,quote,reason):
        beat=fields['beats'][i]
        refs=[source_ref(f'beats[{i}].'+field,beat[field]) for field in ('visibleConsequence','newInformation')
              if beat[field] and beat[field] in quote]
        exact=next((ref['sourceField'] for ref in refs if ref['sourceText']==quote),None)
        findings.append(dict(code=code,beatNumber=i+1,sourceField=exact,
            sourceFields=[ref['sourceField'] for ref in refs],sourceText=quote,
            evidenceRefs=refs,sourceTextScope='EXACT_FIELD' if exact else 'DERIVED_COMPARISON_WITH_EXACT_REFS',
            declaredRule=rule,reason=reason,confidence='SOURCE_CONSTRAINT_COMPARISON'))
    # Lexical state oppositions, not added canonical response/contradiction labels.
    oppositions=[(r'\bbend\w*|\bbent\b',r'\bstraighten\w*',r'\bstraighten\w*'),
                 (r'\blowest\b',r'\bhighest\b',r'\bhighest\b')]
    if re.search(r'\b(?:unrelated rule|separate rule|independently of|independent rule)\b',rule,re.I):
        findings.append(dict(code='MULTIPLE_UNRELATED_RULES',sourceField='impossibleRule',sourceText=rule,
            reason='The declared source itself introduces an independent rule, rather than one coherent object response.',evidenceRefs=[source_ref('impossibleRule',rule)],confidence='EXPLICIT_SOURCE'))
    for i,b in enumerate(fields['beats']):
        consequence=b['visibleConsequence'];info=b['newInformation']
        for antecedent,opposite,allowed in oppositions:
            if re.search(antecedent,rule,re.I) and not re.search(allowed,rule,re.I) and positive_match(opposite,consequence+' '+info):
                add('DECLARED_RULE_OUTCOME_REVERSED',i,consequence+' '+info,
                    'A source outcome asserts the opposite of the declared response without a declared exception.')
        restriction=re.search(r'only (?:when|if)\b.{0,100}|except (?:when|if)\b.{0,100}',info,re.I)
        if restriction and terms(restriction[0])-terms(rule):
            add('UNDECLARED_TRIGGER_RESTRICTION',i,info,
                'A new exclusive input/actor condition is asserted outside the declared rule; no invisible exception is assumed.')
        revised=re.search(r'(?:rule includes|failure mode changes|finally allows)\s+(.+)',info,re.I)
        payload=re.split(r',\s*not\b',revised[1],maxsplit=1,flags=re.I)[0] if revised else ''
        novel_payload=bool(payload and not re.match(r'(?:no|not)\b',payload,re.I) and terms(payload)-terms(rule))
        new_bidirectionality=bool(re.search(r'link is now bidirectional',info,re.I) and not re.search(r'bidirectional',rule,re.I))
        if novel_payload or new_bidirectionality:
            add('RULE_MODEL_CHANGED',i,info,
                'New information explicitly changes the response mapping/allowed outcome rather than only its magnitude.')
        scope_change=re.search(r'controls? ([^,;.]+), not ([^,;.]+)',info,re.I)
        if scope_change and terms(scope_change[2])&terms(rule) and not terms(scope_change[1])&terms(rule):
            add('DECLARED_TARGET_SCOPE_NEGATED',i,info,
                'The later source explicitly says it controls a different target, not the target class described in the rule.')
        # Autonomous agency is admissible when it is actually the declared engine.
        agency=positive_match(r'actively pursues|wants to be|can control (?:her|his|their|the)|starts sweeping itself',info+' '+consequence)
        if agency and not re.search(r'pursu|wants?|controls? (?:the )?character|autonom|itself|alive|living',rule,re.I):
            add('UNDECLARED_AGENCY',i,info+' '+consequence,
                'An autonomous control/intention mechanism is introduced although the declared rule describes a passive function or state.')
        transformation=positive_match(r'becomes? (?:a |an )?(rubber|mirror)\b',consequence)
        if transformation and transformation[1].casefold() not in lower:
            add('UNDECLARED_MATERIAL_OR_FUNCTION',i,consequence,
                'The source introduces another material/function (beyond the declared input/output relation).')
        if re.search(r'hidden camera|unseen camera',consequence,re.I) and not re.search(r'camera',rule,re.I):
            add('INVISIBLE_CAUSAL_DEPENDENCY',i,consequence,
                'A new unseen information-acquisition mechanism is required but absent from the declared cause chain.')
    if re.search(r'\bbackward\b',rule,re.I) and not re.search(r'\bforward\b',rule,re.I):
        for i,b in enumerate(fields['beats']):
            if re.search(r'\b(?:jump|jumps|move|moves|spin|spins|run|runs)\s+(?:\w+\s+){0,3}forward\b',b['visibleConsequence'],re.I):
                add('DECLARED_DIRECTION_REVERSED',i,b['visibleConsequence'],
                    'The explicit response moves forward although the declared response moves backward, without a declared exception.')
    # Exact declared timing constants cannot silently change. These are story
    # facts, not new quality thresholds or response taxonomy.
    numbers={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
    def value(t):return int(t) if t.isdigit() else numbers.get(t.casefold())
    constant=re.search(r'(?:exactly|delayed by)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+seconds?',rule,re.I)
    if constant:
        target=value(constant[1])
        for i,b in enumerate(fields['beats']):
            # A timestamp/timer mention alone is not a contradictory delay.
            changed=re.search(r'(?:delay (?:increases|changes) to|stays put for a full|delay (?:is|to))\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+seconds?',b['visibleConsequence']+' '+b['newInformation'],re.I)
            if changed and value(changed[1])!=target:
                add('DECLARED_TIMING_CONSTANT_CHANGED',i,b['visibleConsequence']+' '+b['newInformation'],
                    f'Declared duration {target} seconds differs from the explicit later duration {value(changed[1])} seconds.')
    return findings


def _factor(supported,reason,refs,**details):
    return dict(supported=bool(supported),reason=reason,evidenceRefs=refs,**details)


def assess(candidate,canonical=None,*,opening_mandatory=False):
    """Premise-level default; production opening stays an independent gate.

    Set opening_mandatory=True for the stricter combined decision. The known
    compatibility path always projects the unchanged legacy premise decision.
    No external report/score/pass flag is accepted as evidence.
    """
    model=natural.load_model()
    legacy=natural.assess(candidate,canonical_creative_evidence=canonical)
    if canonical is not None:
        if not canonical.is_structured:canonical=None
        else:canonical.assert_candidate(candidate)
    if canonical is None:
        name=str(candidate.get('primaryObject','')).casefold();obj=model['objects'].get(name)
        response=natural.infer_response(candidate);policy=natural._policy(obj['archetype'],response,model) if obj else None
        incompatible=bool(obj and obj['archetype']!='GENERIC' and response not in ('UNSUPPORTED_RESPONSE','ORDINARY_RESPONSE') and not policy)
        admitted=bool(legacy['admitted'])
        return AdmissionDecision(admitted=admitted,status='ADMITTED_KNOWN_COMPATIBILITY' if admitted else 'NOT_ADMITTED_INCOMPATIBLE' if incompatible else 'NOT_ADMITTED_INSUFFICIENT_EVIDENCE',
            provenance='KNOWN_COMPATIBILITY' if policy else 'NONE',coverage='KNOWN_TAXONOMY_SUPPORTED' if policy else 'INCOMPATIBLE' if incompatible else 'UNSUPPORTED',
            responseClassificationStatus='PRESENT_CLASSIFIED' if response!='UNSUPPORTED_RESPONSE' else 'PRESENT_UNCLASSIFIED' if candidate.get('impossibleRule') else 'MISSING',
            responseClassification=None if response=='UNSUPPORTED_RESPONSE' else response,openingMandatory=opening_mandatory,
            openingPassed=legacy['instantCausalLegibility']>=OPENING_FLOOR,corePremiseSupported=admitted,
            productionOpeningRequirementSatisfied=legacy['instantCausalLegibility']>=OPENING_FLOOR,factors={'legacyKnownPath':legacy},
            reasons=[] if admitted else [dict(code='LEGACY_ADMISSION_REJECTED',reason='Unchanged existing Naturalness/compatibility decision. A coverage gap without canonical source evidence cannot use fallback.')],sourceContextSha256=None)
    report=natural.assess(candidate,canonical_creative_evidence=canonical,generalized_premise_evidence=True)
    response=report['responseEvidence'];opening_passed=report['instantCausalLegibility']>=OPENING_FLOOR
    context_id=canonical.receipt()['contextSha256']
    if response['compatibility'] in ('SUPPORTED','INCOMPATIBLE'):
        compatible=response['compatibility']=='SUPPORTED';admitted=bool(legacy['admitted']) if compatible else False
        return AdmissionDecision(admitted=admitted,status='ADMITTED_KNOWN_COMPATIBILITY' if admitted else 'NOT_ADMITTED_INCOMPATIBLE' if not compatible else 'NOT_ADMITTED_INSUFFICIENT_EVIDENCE',
            provenance='KNOWN_COMPATIBILITY',coverage='KNOWN_TAXONOMY_SUPPORTED' if compatible else 'INCOMPATIBLE',responseClassificationStatus='PRESENT_CLASSIFIED',responseClassification=response['classification'],
            openingMandatory=opening_mandatory,openingPassed=opening_passed,corePremiseSupported=admitted,productionOpeningRequirementSatisfied=opening_passed,
            factors={'knownCompatibility':dict(compatibility=response['compatibility'],legacyAdmitted=legacy['admitted'],legacyReasons=legacy['flags'])},
            reasons=[] if admitted else [dict(code='KNOWN_INCOMPATIBLE' if not compatible else 'KNOWN_PATH_QUALITY_FAILED',reason='Existing covered compatibility and quality decisions are authoritative; fallback cannot bypass them.')],sourceContextSha256=context_id)
    fields=canonical.fields;facts=canonical.facts
    normal=terms(fields['normalExpectation']);rule=terms(fields['impossibleRule']);why=terms(fields['whyThisObject']);trigger=terms(fields['visibleTrigger'])
    # Tool identity is not a functional-dependency witness. Compound modifier
    # operands (hair in hairbrush) may still be the function's affected target.
    name=fields['primaryObject'].casefold();allwords=set(re.findall(r'[a-z]+',' '.join(fields[k] for k in ('normalExpectation','impossibleRule','visibleTrigger')).casefold()))
    heads=terms(fields['primaryObject'])
    for word in allwords:
        if name.replace(' ','').endswith(word) and len(word)>=4:heads|=terms(word)
    anchors=(normal & rule)-heads
    effect_refs=[];effect_support=[];effect_subjects=[]
    def subject(value):
        value=re.sub(r'^\s*(?:(?:the|a|an|all|now|new|original|long|short|hot|white|black|blue|red|entire)\s+)+','',value,flags=re.I)
        match=re.match(r"[A-Za-z]+",value)
        return terms(match[0]) if match else set()

    for i,b in enumerate(fields['beats']):
        matches=sorted(anchors&terms(b['visibleConsequence']))
        primary_subject=subject(b['visibleConsequence'])
        effect_subjects.append(dict(beatNumber=i+1,subject=sorted(primary_subject)))
        if matches and primary_subject&(anchors|heads):effect_support.append(i+1);effect_refs.append(source_ref(f'beats[{i}].visibleConsequence',b['visibleConsequence']))
    identity=(terms(fields['primaryObject']) & (rule|normal|why|trigger)) or any(name.replace(' ','').endswith(w) for w in allwords if len(w)>=4 and w in ' '.join([fields['impossibleRule'],fields['normalExpectation']]).casefold())
    # A consistent source noun across why/rule/trigger can witness a source
    # short name (e.g. refrigerator/fridge) without creating an object alias row.
    source_short_name=subject(fields['whyThisObject'])
    source_identity=bool(source_short_name & rule & trigger)
    identity=bool(identity or source_identity)
    dependency=bool(identity and anchors and anchors&trigger and len(effect_support)>=2 and why and (why & (normal|rule)))
    normal_present=not PLACEHOLDER.fullmatch(fields['normalExpectation']) and bool(normal)
    # Existing covered ordinary functions remain authoritative, including when
    # the response itself is unclassified. A forged 'fork controls ceilings'
    # normalExpectation cannot erase the configured food-transport role.
    obj=model['objects'].get(name)
    ordinary_aligned=True
    if obj and obj['archetype']!='GENERIC':
        expected_terms=terms(' '.join(model['archetypes'][obj['archetype']]['primaryExpectedBehaviors']))
        ordinary_aligned=bool((normal-heads)&expected_terms)
    # Shared nouns alone are not a functional relation. Require the source rule
    # to address an ordinary/goal operation, or a configured function operation.
    first_word=re.findall(r'[A-Za-z]+',fields['normalExpectation'])
    first_word=first_word[0] if first_word else ''
    ordinary_actor=first_word if not first_word.casefold().endswith('ing') and terms(first_word)&heads else ''
    normal_action=action_evidence(fields['normalExpectation'],ordinary_actor)
    goal_action=action_evidence(fields['everydayGoal'],'')
    function_operations=set()
    for witness in (normal_action,goal_action):
        if witness['supported'] and witness['predicate'] not in {'use','do','happen','is','has','get','have'}:
            function_operations.add(witness['predicate'])
    if obj and obj['archetype']!='GENERIC':
        for behavior in model['archetypes'][obj['archetype']]['primaryExpectedBehaviors']:
            function_operations.update(terms(behavior.split()[0]))
    matched_operations=sorted(function_operations&rule)
    operation_supported=bool(matched_operations)
    dependency=dependency and operation_supported
    visual_response=bool(response['state'] not in ('RESPONSE_MISSING','RESPONSE_AMBIGUOUS') and facts['rule']['present'] and rule and all(b['visibleConsequence'].strip() for b in fields['beats']))
    trigger_action=action_evidence(fields['visibleTrigger'],candidate.get('protagonist',''))
    concrete_trigger=bool(facts['trigger']['present'] and not PLACEHOLDER.fullmatch(fields['visibleTrigger']) and trigger_action['supported'] and (trigger-heads)&rule)
    direct=report['goalInterferenceType']=='DIRECT'
    violations=coherence_findings(fields)
    review_notes=[dict(beatNumber=i+1,sourceField=f'beats[{i}].visibleConsequence',sourceText=b['visibleConsequence'],
        reason='A simile is not proof of literal material transformation; inspect whether this remains a rule-linked state escalation.')
        for i,b in enumerate(fields['beats']) if re.search(r'becomes? like\b',b['visibleConsequence'],re.I)]
    coherent=bool(facts['rule']['visible'] and facts['rule']['dominant'] and not violations)
    explicitly_arbitrary=report['qualityEvidence']['arbitraryMagicRisk']['qualitySupport']=='HIGH'
    arbitrary=explicitly_arbitrary
    refs=lambda k:[source_ref(k,fields[k])]
    factors={
        'normalExpectation':_factor(normal_present and ordinary_aligned,'A concrete ordinary function is explicit; a covered object role must corroborate it. An unmatched wording is unresolved, not proof of an incorrect function.',refs('normalExpectation'),knownObjectFunctionAligned=ordinary_aligned),
        'impossibleResponse':_factor(visual_response,'Abnormal outcomes are explicitly described; presence is independent of response class.',refs('impossibleRule')),
        'objectSpecificity':_factor(dependency,'Non-identity function operands link expectation, rule, trigger and at least two visible consequences; whyThisObject alone cannot pass.',refs('primaryObject')+refs('normalExpectation')+refs('impossibleRule')+refs('whyThisObject')+effect_refs,functionAnchors=sorted(anchors),triggerAnchors=sorted(anchors&trigger),supportedBeats=effect_support,identityTerms=sorted(heads),effectSubjects=effect_subjects,sourceShortName=sorted(source_short_name) if source_identity else [],normalActionEvidence=normal_action,goalActionEvidence=goal_action,matchedFunctionOperations=matched_operations),
        'trigger':_factor(concrete_trigger,'A concrete source action is linked to the declared abnormal behavior.',refs('visibleTrigger'),actionEvidence=trigger_action),
        'goalInterference':_factor(direct,'Existing canonical goal/effect/prevention links support DIRECT interference; no response label is required.',refs('goalRuleRelationship'),sourceJudgment=report['qualityEvidence']['goalInterference']),
        'causalCoherence':_factor(coherent,'Action→response→problem must be canonically grounded and preserve declared source constraints across beats.',refs('impossibleRule'),ruleSupported=facts['rule']['visible'],dominantRule=facts['rule']['dominant'],violations=violations,reviewNotes=review_notes),
        'nonArbitrary':_factor(not arbitrary and dependency,'A visible goal obstruction is insufficient when no ordinary-function dependency is supported.',refs('normalExpectation')+refs('whyThisObject'),explicitlyArbitrary=explicitly_arbitrary),
        'functionalAffordanceRelationship':_factor(dependency and ordinary_aligned,'The impossible effect changes the object’s stated function/operand, not an unrelated event attached to its name.',refs('normalExpectation')+refs('impossibleRule')+refs('whyThisObject')),
        'openingLegibility':_factor(opening_passed,'Existing opening score>=60 remains authoritative and is independent of core premise admission.',facts['opening']['source'],score=report['instantCausalLegibility'],required=opening_mandatory,standard=report['openingEvidence']),
    }
    failures=[dict(code='FACTOR_NOT_ESTABLISHED',factor=k,reason=v['reason']) for k,v in factors.items() if k!='openingLegibility' and not v['supported']]
    failures.extend(violations)
    core=not failures
    admitted=core and (opening_passed or not opening_mandatory)
    if admitted:status='ADMITTED_EVIDENCE_SUPPORTED_UNCLASSIFIED'
    elif arbitrary:status='NOT_ADMITTED_ARBITRARY'
    elif violations:status='NOT_ADMITTED_RULE_INCOHERENT'
    elif core and opening_mandatory and not opening_passed:status='NOT_ADMITTED_OPENING_WEAK'
    else:status='NOT_ADMITTED_INSUFFICIENT_EVIDENCE'
    if opening_mandatory and not opening_passed:failures.append(dict(code='OPENING_BELOW_EXISTING_FLOOR',score=report['instantCausalLegibility'],minimum=OPENING_FLOOR,reason='No fallback can make an opening below60 production-admissible.'))
    return AdmissionDecision(admitted=admitted,status=status,provenance='EVIDENCE_SUPPORTED_UNCLASSIFIED',
        coverage='EVIDENCE_SUPPORTED_UNCLASSIFIED' if core else 'UNSUPPORTED',
        responseClassificationStatus='PRESENT_UNCLASSIFIED' if response['classification'] is None else 'PRESENT_CLASSIFIED',
        responseClassification=response['classification'],openingMandatory=opening_mandatory,openingPassed=opening_passed,
        corePremiseSupported=core,productionOpeningRequirementSatisfied=opening_passed,factors=factors,reasons=failures,sourceContextSha256=context_id)


def project_naturalness(report,decision):
    """Boolean/provenance projection only. Naturalness metrics stay byte-identical."""
    decision=AdmissionDecision.model_validate(decision)
    if decision.sourceContextSha256 is not None:
        if (report.get('canonicalCreativeEvidence') or {}).get('contextSha256')!=decision.sourceContextSha256:
            raise ValueError('Admission projection context differs from source report')
    result=deepcopy(report)
    result['legacyAdmitted']=report['admitted']
    result['admitted']=decision.admitted
    result['admissionV2']=decision.model_dump()
    result['admissionProvenance']=decision.provenance
    return result
