"""Plan first: one bounded provider response, validated source-bound execution,
then deterministic prompt compilation. No story rewriting or semantic approval."""
import json
import re
from copy import deepcopy
from hashlib import sha256
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.parser.prompt_parser import parse_prompt
from .optimization_distinctness import _beats, validate_execution_candidates
from .optimization_profile_contract import generation_contract, normalize_candidate_profiles

CONTRACT_VERSION='plan-first-v1'
INSTRUCTIONS_VERSION='plan-first-owned-source-v3'
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
class Binding(Strict):
    quote: str = Field(min_length=1,max_length=300)
class Change(Strict):
    sourceBeatId: str
    sourceQuote: str = Field(min_length=1,max_length=2000)
    framing: Literal['EXTREME_CLOSE','CLOSE','MEDIUM','WIDE']
    motion: Literal['STATIC','PAN','TRACK','PUSH']
    stagingMode: Literal['CAUSE_EFFECT_SAME_FRAME','ACTION_CONSEQUENCE_PAIR','DISTINCT_STATE_HOLDS']
    focusBindings: list[Binding] = Field(max_length=4)
    stateSequence: list[Binding] = Field(max_length=8)
    startTime: float = Field(ge=0)
    endTime: float = Field(gt=0)
class Plan(Strict):
    candidateId: Literal['candidate-a','candidate-b']
    title: str = Field(min_length=3,max_length=100)
    objective: Literal['OPENING_CAUSAL_LEGIBILITY','ESCALATION_EXECUTION_FEASIBILITY']
    baselineOpportunity: str = Field(min_length=12,max_length=600)
    proposedVisualConsequence: str = Field(min_length=12,max_length=600)
    materialDifference: str = Field(min_length=12,max_length=600)
    preservedStoryAnchors: list[str] = Field(min_length=1,max_length=30)
    risksIntroduced: list[str] = Field(max_length=8)
    risksReducedHypotheses: list[str] = Field(min_length=1,max_length=8)
    unknowns: list[str] = Field(min_length=1,max_length=8)
    evidenceStatus: Literal['HYPOTHESIS_ONLY']
    changes: list[Change] = Field(min_length=1,max_length=12)
class Plans(Strict):
    plans: list[Plan] = Field(min_length=2,max_length=2)

class PlanNarrative(Strict):
    title: str = Field(min_length=3,max_length=100)
    baselineOpportunity: str = Field(min_length=12,max_length=600)
    proposedVisualConsequence: str = Field(min_length=12,max_length=600)
    materialDifference: str = Field(min_length=12,max_length=600)
    risksIntroduced: list[str] = Field(max_length=8)
    risksReducedHypotheses: list[str] = Field(min_length=1,max_length=8)
    unknowns: list[str] = Field(min_length=1,max_length=8)
    evidenceStatus: Literal['HYPOTHESIS_ONLY']
class ExecutionChoice(Strict):
    executionOptionId: str
    framing: Literal['EXTREME_CLOSE','CLOSE','MEDIUM','WIDE']
    motion: Literal['STATIC','PAN','TRACK','PUSH']
class OpeningChoice(ExecutionChoice):
    pass
class PairChoice(ExecutionChoice):
    pass
class ProgressionChoice(ExecutionChoice):
    pass
class OpeningPlan(PlanNarrative):
    openingChange: OpeningChoice
class EscalationPlan(PlanNarrative):
    actionConsequenceChange: PairChoice
    progressionChange: ProgressionChoice
class SourceOwnedPlans(Strict):
    openingPlan: OpeningPlan
    escalationPlan: EscalationPlan

def protected_contract(source,context):
    ownership=generation_contract(source,context)
    approved=context.get('approvedStoryText','')
    beats=_beats(source);anchors=context.get('essentialEvents')
    if not ownership or not approved.strip() or not isinstance(anchors,list) or len(anchors)!=len(beats):
        raise ValueError('Source-plan protected story/production contract is incomplete')
    if any(anchor not in b['sourceQuote'] for anchor,b in zip(anchors,beats)):
        raise ValueError('Source-plan protected event anchors do not match the baseline')
    ir=parse_prompt(source).video_plan_ir
    return {**ownership,'sourcePromptSha256':sha256(source.encode()).hexdigest(),
            'approvedStorySha256':sha256(approved.encode()).hexdigest(),
            'characterIdentity':ir.get('characters',{}),'openingCausalParticipants':ir.get('coreMechanic',{}).get('surfaceAttachmentEvidence',{}),'corePhysicalRule':ir.get('coreMechanic',{}).get('physicalRuleEvidence',{'state':'UNKNOWN'}),
            'requiredEnding':{'sourceBeatId':beats[-1]['id'],'sourceQuote':beats[-1]['sourceQuote']},
            'events':[{'sourceBeatId':b['id'],'sourceQuote':b['sourceQuote'],'actionAnchor':a,'startTime':b['startTime'],'endTime':b['endTime']} for a,b in zip(anchors,beats)],
            'semanticStoryFidelity':'UNKNOWN','visualEvidence':'NOT_SUPPLIED'}

def response_format(anchors=None,options=None):
    schema=(SourceOwnedPlans if options is not None else Plans).model_json_schema()
    def wire(value):
        if isinstance(value,dict):
            result={k:wire(v) for k,v in value.items() if k != 'default' and not (k == 'title' and isinstance(v,str))}
            if 'const' in result:result['enum']=[result.pop('const')]
            return result
        return [wire(v) for v in value] if isinstance(value,list) else value
    schema=wire(schema)
    if options is not None:
        for definition,kind in [('OpeningChoice','opening'),('PairChoice','action-consequence'),('ProgressionChoice','progression')]:
            schema['$defs'][definition]['properties']['executionOptionId']['enum']=[key for key,value in options.items() if value['kind']==kind]
    elif anchors:
        protected=schema['$defs']['Plan']['properties']['preservedStoryAnchors']
        protected.update(minItems=len(anchors),maxItems=len(anchors))
        protected['items']={'type':'string','enum':list(anchors)}
    return {'type':'json_schema','json_schema':{'name':'protected_execution_plans','strict':True,'schema':schema}}

def plan_request_payload(source,context):
    contract=protected_contract(source,context)
    events=contract['events']
    causal=contract['openingCausalParticipants']
    opening=[{'quote':(causal.get(key) or {}).get('value','UNKNOWN')} for key in ('expectedSurface','actualSurface')]
    pairs=[];progressions=[]
    for event in events[1:-1]:
        quote=event['sourceQuote'];boundary=quote.find('->');anchor=event['actionAnchor']
        consequence=quote[boundary+2:].strip() if boundary>=0 else ''
        if boundary>=0 and anchor in quote[:boundary] and consequence and len(anchor)<=300 and len(consequence)<=300 and '[' not in consequence:
            pairs.append({'sourceBeatId':event['sourceBeatId'],'focusBindings':[{'quote':anchor},{'quote':consequence}],'stateSequence':[]})
        match=re.search(r'\bmultiply from (.+?) as ',quote,re.I)
        if match:
            states=match[1].split(' to ')
            if len(states)>=3:
                progressions.append({'sourceBeatId':event['sourceBeatId'],'focusBindings':[],'stateSequence':[{'quote':s} for s in states]})
    payload={'phase':'MATERIAL_IMPROVEMENT_PLANS','instructionsVersion':INSTRUCTIONS_VERSION,
            'protectedStoryContract':contract,'bindingProtocol':{
                'exactPreservedStoryAnchorsForBOTHPlans':[e['actionAnchor'] for e in events],
                'openingRequiredBindings':{'sourceBeatId':events[0]['sourceBeatId'],'stagingMode':'CAUSE_EFFECT_SAME_FRAME','focusBindings':opening,'stateSequence':[]},
                'actionConsequenceBindingOptions':pairs,'explicitProgressionBindingOptions':progressions,
                'audienceEvidence':'NONE. Do not propose engagement, retention, views or watch-time gains, even under risksReducedHypotheses. Put unmeasured audience response in unknowns.',
                'riskExamples':{'allowed':'Simultaneous source-bound contact visibility may reduce causal ambiguity; visual review is still required.','notAllowed':'Increased viewer engagement / better audience retention.'}}}
    payload['executionOptions']=execution_options(payload)
    return payload

def execution_options(payload):
    contract=payload['protectedStoryContract'];protocol=payload['bindingProtocol']
    by_id={event['sourceBeatId']:event for event in contract['events']};options={}
    def add(kind,binding,mode):
        event=by_id[binding['sourceBeatId']]
        _check_bindings([Binding.model_validate(b) for b in binding['focusBindings']],event['sourceQuote'])
        _check_bindings([Binding.model_validate(b) for b in binding['stateSequence']],event['sourceQuote'])
        key=f'{kind}:{event["sourceBeatId"]}'
        options[key]={'kind':kind,'change':{**deepcopy(event),**deepcopy(binding),'stagingMode':mode}}
        options[key]['change'].pop('actionAnchor',None)
    opening=protocol['openingRequiredBindings']
    if any(b['quote']=='UNKNOWN' for b in opening['focusBindings']):
        raise ValueError('Source-plan opening evidence is UNKNOWN; no paid plan request can be grounded')
    add('opening',opening,'CAUSE_EFFECT_SAME_FRAME')
    progression_ids={p['sourceBeatId'] for p in protocol['explicitProgressionBindingOptions']}
    for pair in protocol['actionConsequenceBindingOptions']:
        if pair['sourceBeatId'] not in progression_ids:add('action-consequence',pair,'ACTION_CONSEQUENCE_PAIR')
    for progression in protocol['explicitProgressionBindingOptions']:add('progression',progression,'DISTINCT_STATE_HOLDS')
    if not all(any(o['kind']==kind for o in options.values()) for kind in ('opening','action-consequence','progression')):
        raise ValueError('Source-plan lacks supported distinct action and progression options; evidence remains UNKNOWN')
    return options

def expand_source_owned_plans(value,payload):
    parsed=SourceOwnedPlans.model_validate(value);options=payload['executionOptions']
    def resolve(choice,kind):
        option=options.get(choice.executionOptionId)
        if not option or option['kind']!=kind:
            raise ValueError(f'Source-plan execution option {choice.executionOptionId} is not an approved {kind} choice')
        return {**deepcopy(option['change']),'framing':choice.framing,'motion':choice.motion}
    output=[]
    for identity,objective,plan,choices in [
        ('candidate-a','OPENING_CAUSAL_LEGIBILITY',parsed.openingPlan,[(parsed.openingPlan.openingChange,'opening')]),
        ('candidate-b','ESCALATION_EXECUTION_FEASIBILITY',parsed.escalationPlan,[(parsed.escalationPlan.actionConsequenceChange,'action-consequence'),(parsed.escalationPlan.progressionChange,'progression')])]:
        narrative=plan.model_dump(exclude={'openingChange','actionConsequenceChange','progressionChange'})
        changes=[resolve(choice,kind) for choice,kind in choices]
        order={e['sourceBeatId']:i for i,e in enumerate(payload['protectedStoryContract']['events'])}
        changes.sort(key=lambda c:order[c['sourceBeatId']])
        output.append({**narrative,'candidateId':identity,'objective':objective,
                       'preservedStoryAnchors':deepcopy(payload['bindingProtocol']['exactPreservedStoryAnchorsForBOTHPlans']),
                       'changes':changes})
    return {'plans':output}

def _check_bindings(bindings,quote,region=None):
    groups=[]
    for b in bindings:
        annotations=[(m.start(),m.end()) for m in re.finditer(r'\[[^\]]*\]',quote)]
        spans=[(m.start(),m.end()) for m in re.finditer(re.escape(b.quote),quote)
               if (region is None or (m.start()>=region[0] and m.end()<=region[1]))
               and not any(m.start()<z and m.end()>a for a,z in annotations)]
        if not spans:
            raise ValueError('Source-plan execution binding has no exact source quote; no span is invented')
        groups.append(spans)
    ordered=sorted(span for spans in groups for span in spans)
    if any(a[1]>b[0] for a,b in zip(ordered,ordered[1:])):
        raise ValueError('Source-plan execution bindings overlap')
    return groups

def _source_refs(plan,by_id):
    refs=[]
    for change in plan.changes:
        region=None
        if change.stateSequence:
            match=re.search(r'\bmultiply from (.+?) as ',change.sourceQuote,re.I)
            region=(match.start(1),match.end(1))
        for bindings,scope in [(change.focusBindings,None),(change.stateSequence,region)]:
            for binding,spans in zip(bindings,_check_bindings(bindings,change.sourceQuote,scope)):
                refs.append({'sourceBeatId':change.sourceBeatId,'quote':binding.quote,'localSpans':[list(s) for s in spans],
                             'globalSpans':[[by_id[change.sourceBeatId]['sourceSpan'][0]+s[0],by_id[change.sourceBeatId]['sourceSpan'][0]+s[1]] for s in spans],
                             'method':'ALL_EXACT_SOURCE_TEXT_MATCHES','semanticVerification':'UNKNOWN'})
    return refs

def _validate_outcome_claims(plan):
    # Plans have no audience or rendered-output evidence. A hypothesis label
    # cannot turn invented metrics or outcome assurances into supported facts.
    fields=[plan.title,plan.baselineOpportunity,plan.proposedVisualConsequence,
            plan.materialDifference,*plan.risksIntroduced,
            *plan.risksReducedHypotheses,*plan.unknowns]
    audience=r'\b(?:retention|watch[ -]?time|completion rates?|views?|engagement|audience response|viewer response)\b'
    improvement=r'\b(?:increase[sd]?|improve[sd]?|boost[sd]?|raise[sd]?|lift[sd]?|double[sd]?|triple[sd]?|reduce[sd]?|better|higher|greater|longer)\b'
    quantified=r'\b\d+(?:\.\d+)?\s*(?:%|percent\b|percentage points\b|times\b|x\b)'
    for text in fields:
        lower=text.lower()
        forbidden=False
        for sentence in re.split(r'(?<=[.!?])\s+|\n',lower):
            unknown=bool(re.search(r'\b(?:unknown|unmeasured|unverified|not measured|not established|no (?:guaranteed|proven|measured|verified)|cannot (?:assess|establish)|requires? (?:actual )?audience evidence)\b',sentence))
            assurance=bool(re.search(r'(?<!not )(?<!no )\b(?:will|guaranteed|proven|verified)\b',sentence))
            evidence_claim=bool(re.search(r'\b(?:guaranteed|proven|measured) retention\b|\bguaranteed render\b',sentence))
            if evidence_claim and (not unknown or assurance):
                forbidden=True
            if re.search(audience,sentence) and (re.search(quantified,sentence) or (re.search(improvement,sentence) and (not unknown or assurance))):
                forbidden=True
        if forbidden:
            raise ValueError(f'Source-plan {plan.candidateId} plan claims unsupported audience or render evidence: {text}')


def validate_plan(source,context,plan):
    p=Plan.model_validate(plan) if isinstance(plan,dict) else plan
    _validate_outcome_claims(p)
    contract=protected_contract(source,context);beats=_beats(source);by_id={b['id']:b for b in beats}
    if p.preservedStoryAnchors!=context['essentialEvents']:
        raise ValueError(f'Source-plan {p.candidateId} must preserve all {len(context["essentialEvents"])} approved event anchors in order, including untouched events; received {len(p.preservedStoryAnchors)}')
    expected='OPENING_CAUSAL_LEGIBILITY' if p.candidateId=='candidate-a' else 'ESCALATION_EXECUTION_FEASIBILITY'
    if p.objective!=expected:raise ValueError('Source-plan candidate objective is not the assigned strategy')
    ids=[c.sourceBeatId for c in p.changes]
    if len(ids)!=len(set(ids)) or any(x not in by_id for x in ids):raise ValueError('Source-plan change IDs must be unique source events')
    if ids!=sorted(ids,key=lambda x:list(by_id).index(x)):raise ValueError('Source-plan changes reorder events')
    for c in p.changes:
        original=by_id[c.sourceBeatId]
        if c.sourceQuote!=original['sourceQuote']:raise ValueError('Source-plan change source quote differs from baseline')
        if c.endTime<=c.startTime:raise ValueError('Source-plan change timing is invalid')
        focus_spans=_check_bindings(c.focusBindings,c.sourceQuote);state_spans=_check_bindings(c.stateSequence,c.sourceQuote)
        if c.stagingMode in ('CAUSE_EFFECT_SAME_FRAME','ACTION_CONSEQUENCE_PAIR'):
            if len(c.focusBindings)<2 or len({b.quote.casefold() for b in c.focusBindings})<2 or c.stateSequence:
                raise ValueError('Non-material plan: causal staging requires two distinct source-bound participants/states')
            if len({b.quote.casefold() for b in c.focusBindings})!=len(c.focusBindings):raise ValueError('Non-material plan: repeated focus bindings')
            if c.stagingMode=='ACTION_CONSEQUENCE_PAIR':
                boundary=c.sourceQuote.find('->')
                if boundary<0 or not any(z<=boundary for a,z in focus_spans[0]) or not any(a>=boundary+2 for a,z in focus_spans[1]):
                    raise ValueError('Non-material plan: focus pair must bind existing action before its explicit consequence')
        else:
            match=re.search(r'\bmultiply from (.+?) as ',c.sourceQuote,re.I)
            if not match or [b.quote for b in c.stateSequence]!=match[1].split(' to ') or len(c.stateSequence)<3:
                raise ValueError('Non-material plan: state holds must expose the complete explicit source progression')
            # Evidence must point to those actual progression tokens, not an
            # unrelated occurrence of a number elsewhere in the event.
            _check_bindings(c.stateSequence,c.sourceQuote,(match.start(1),match.end(1)))
    changed={c.sourceBeatId:c for c in p.changes}
    timeline=[(changed[b['id']].startTime,changed[b['id']].endTime) if b['id'] in changed else (b['startTime'],b['endTime']) for b in beats]
    if timeline[0][0]!=0 or timeline[-1][1]!=float(contract['generatorSettings']['duration']) or any(a[1]!=b[0] for a,b in zip(timeline,timeline[1:])):
        raise ValueError('Source-plan plan timing must cover the target duration without gaps or overlaps')
    if p.candidateId=='candidate-a':
        if not p.changes or p.changes[0].sourceBeatId!=beats[0]['id'] or p.changes[0].stagingMode!='CAUSE_EFFECT_SAME_FRAME':
            raise ValueError('Non-material opening plan: opening cause and effect must share source-bound staging')
        evidence=contract['openingCausalParticipants']
        participants=[(evidence.get(key) or {}).get('value') for key in ('expectedSurface','actualSurface')]
        if any(not q or q=='UNKNOWN' for q in participants) or {b.quote for b in p.changes[0].focusBindings}!=set(participants):
            raise ValueError('Non-material opening plan: bind both supported intended and actual source participants; missing causal evidence remains UNKNOWN')
    else:
        mid=[c for c in p.changes if c.sourceBeatId in by_id and c.sourceBeatId not in (beats[0]['id'],beats[-1]['id'])]
        if len(mid)<2 or not any(c.stagingMode=='DISTINCT_STATE_HOLDS' for c in mid) or not any(c.stagingMode=='ACTION_CONSEQUENCE_PAIR' for c in mid):
            raise ValueError('Non-material escalation plan: distinct source actions and ordered state exposure are required; timing splits alone are insufficient')
    return {'contractVersion':CONTRACT_VERSION,'status':'SOURCE_BOUND_MATERIAL_PLAN','strategy':p.objective,
            'materialityBasis':'EXPLICIT_CAUSAL_STAGING' if p.candidateId=='candidate-a' else 'DISTINCT_ACTION_AND_ORDERED_STATE_EXPOSURE',
            'preservedStorySha256':contract['approvedStorySha256'],'sourcePromptSha256':contract['sourcePromptSha256'],
            'storyFidelity':'UNKNOWN','creativeBenefit':'HYPOTHESIS_ONLY','renderAuthorization':'NOT_GRANTED',
            'sourceBindings':_source_refs(p,by_id)}

_FRAMES={'EXTREME_CLOSE':'extreme close-up','CLOSE':'close-up','MEDIUM':'medium shot','WIDE':'wide shot'}
_MOTIONS={'STATIC':'static','PAN':'pan','TRACK':'tracking','PUSH':'push-in'}
def compile_plan(source,context,plan):
    p=Plan.model_validate(plan) if isinstance(plan,dict) else plan
    proof=validate_plan(source,context,p);beats=_beats(source);changes={c.sourceBeatId:c for c in p.changes};prompt=source
    for b in reversed(beats):
        if b['id'] not in changes:continue
        c=changes[b['id']];parts=[_MOTIONS[c.motion]+' '+_FRAMES[c.framing]]
        if c.stagingMode=='CAUSE_EFFECT_SAME_FRAME':parts.append('keep '+' and '.join(x.quote for x in c.focusBindings)+' visible together in the same frame')
        elif c.stagingMode=='ACTION_CONSEQUENCE_PAIR':parts.append('focus '+ ' then '.join(x.quote for x in c.focusBindings)+' in a single continuous shot')
        else:parts.extend('hold '+x.quote for x in c.stateSequence);parts.append('single continuous shot')
        quote=re.sub(r'\[[^\]]*\]','',b['sourceQuote'])
        quote=re.sub(r'^\d+(?:\.\d+)?\s*[-–—]\s*\d+(?:\.\d+)?\s*s\s*:',f'{c.startTime:g}-{c.endTime:g}s:',quote)
        quote=quote.rstrip()+' ['+'; '.join(parts)+']'
        a,z=b['sourceSpan'];prompt=prompt[:a]+quote+prompt[z:]
    candidate={'candidateId':p.candidateId,'title':p.title,'hypothesis':p.proposedVisualConsequence,
               'prompt':prompt,'executionPlan':p.model_dump(),'planValidation':proof}
    normalize_candidate_profiles(source,[candidate],context)
    return candidate

SYSTEM='''Generate two materially distinct execution plans through openingPlan and escalationPlan. These are production hypotheses, not prompt rewrites. The server owns approved story events/order, character identity, physical rule, ending, source quotes, evidence bindings, target duration and production profile. You only select supplied executionOptionIds, framing/motion and explain the proposed material intervention, visual consequence, risks and unknowns.
OpeningPlan improves simultaneous intended/actual contact visibility and first-frame causal legibility: select an opening option in openingChange. EscalationPlan improves readability of distinct approved actions and escalation states: select an action-consequence option in actionConsequenceChange AND a progression option in progressionChange. They must be separate source events; the catalog already provides disjoint options. The server exposes the complete source-state sequence through explicit continuous state holds. Preserve existing beat timing, story and ending. Do not substitute camera adjectives or arbitrary timing splits for these required interventions.
Do not return sourceQuote, sourceBeatId, preservedStoryAnchors, objective, stagingMode, focusBindings or stateSequence: these fields are resolved from the immutable server catalog after your selections. Do not invent an executionOptionId or narrative action. Each option refers to an alternative production treatment of an existing source event, not an additional story beat. Return both plan slots, complete descriptive fields and no full prompts.
Explain concrete causal staging/exposure benefits as unproven hypotheses. Risks may discuss compositional density, causal ambiguity, continuity or execution uncertainty. Do not claim increased engagement, better retention, higher views, improved watch time, measured audience benefit or guaranteed render success. Audience response and actual visual/generator feasibility remain unmeasured unknowns. No automatic approval or render authorization. The server validates both expanded plans before compiling either full prompt.'''

def perform_plan_first(source,context,provider,model):
    payload=plan_request_payload(source,context);contract=payload['protectedStoryContract']
    provider.response_format=response_format(options=payload['executionOptions']);provider.last_request_started=True
    raw=provider.complete(json.dumps(payload,ensure_ascii=False),system=SYSTEM,temperature=0)
    provider.last_raw_response=raw
    try:value=json.loads(raw)
    except (ValueError,TypeError) as error:raise ValueError('Optimization plan provider returned invalid JSON') from error
    provider.last_role_result=deepcopy(value)
    if context.get('optimizationGenerationInstructionsVersion')==INSTRUCTIONS_VERSION and not getattr(provider,'saved_result_recovery',False) and not ('openingPlan' in value and 'escalationPlan' in value):
        raise ValueError('Source-plan generation requires source-owned openingPlan and escalationPlan slots')
    normalized=expand_source_owned_plans(value,payload) if 'openingPlan' in value or 'escalationPlan' in value else value
    parsed=Plans.model_validate(normalized)
    if [p.candidateId for p in parsed.plans]!=['candidate-a','candidate-b']:raise ValueError('Source-plan strategies must be candidate-a then candidate-b')
    # All plans pass before a single complete candidate is compiled.
    proofs=[validate_plan(source,context,p) for p in parsed.plans]
    candidates=[compile_plan(source,context,p) for p in parsed.plans]
    validate_execution_candidates(source,candidates,context)
    return {'role':'PROMPT_OPTIMIZATION','provider':'openai','model':model,'calls':1,
            'result':{'candidates':candidates,'plans':[p.model_dump() for p in parsed.plans],'planValidations':proofs,'protectedStoryContract':contract},
            'rawProviderResult':deepcopy(value),'rawProviderResponse':raw,'validationStatus':'NOT_VALIDATED',
            'workflowStrategy':CONTRACT_VERSION,'promptCompilation':'DETERMINISTIC_AFTER_PLAN_VALIDATION',
            'usage':getattr(provider,'last_usage',None),'providerResponseMetadata':getattr(provider,'last_response_metadata',None)}
