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

def response_format():
    schema=Plans.model_json_schema()
    def wire(value):
        if isinstance(value,dict):
            result={k:wire(v) for k,v in value.items() if k != 'default' and not (k == 'title' and isinstance(v,str))}
            if 'const' in result:result['enum']=[result.pop('const')]
            return result
        return [wire(v) for v in value] if isinstance(value,list) else value
    return {'type':'json_schema','json_schema':{'name':'protected_execution_plans','strict':True,'schema':wire(schema)}}

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


def validate_plan(source,context,plan):
    p=Plan.model_validate(plan) if isinstance(plan,dict) else plan
    contract=protected_contract(source,context);beats=_beats(source);by_id={b['id']:b for b in beats}
    if p.preservedStoryAnchors!=context['essentialEvents']:
        raise ValueError('Source-plan improvement plan must preserve all approved event anchors in order')
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
        if any(x in text.lower() for text in [p.baselineOpportunity,p.proposedVisualConsequence,p.materialDifference,*p.risksReducedHypotheses] for x in ['guaranteed retention','proven retention','measured retention','guaranteed render']):
            raise ValueError('Source-plan plan claims unsupported audience or render evidence')
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

SYSTEM='''Return exactly two structured execution plans, not prompt rewrites. The server supplies the protected story contract and compiles validated plans into full prompts. Do not change story events, their order, character, physical rule or ending. Candidate A: opening causal legibility and first-frame curiosity through the exact expectedSurface.value and actualSurface.value from openingCausalParticipants sharing a readable frame. Missing supported participants cannot be invented. Candidate B: escalation/action diversity and execution feasibility through at least two distinct existing mid-section actions, one action/consequence focus pair and a complete ordered source-state sequence in continuous execution. Every binding supplies an exact quote within that change's sourceQuote. The server retains all exact matching Unicode spans (and binds state values to their explicit progression clause); do not supply guessed offsets. Preserve every actionAnchor verbatim in preservedStoryAnchors, in order. Framing adjectives, camera labels and arbitrary time splits alone are insufficient. State sequences must use actual explicit source progression; never invent a stage or object. Baseline opportunities and consequences are text-only hypotheses. Explain exact production changes, their visual consequences, materiality, risks and unknowns. No measured audience claims, automatic approval or render authorization. Current server profile is authoritative; historical AUTO is not. Keep full selected duration and ordered contiguous events. Only two plans are returned; the server validates materiality before compiling any candidate.'''

def perform_plan_first(source,context,provider,model):
    contract=protected_contract(source,context)
    provider.response_format=response_format();provider.last_request_started=True
    raw=provider.complete(json.dumps({'phase':'MATERIAL_IMPROVEMENT_PLANS','protectedStoryContract':contract},ensure_ascii=False),system=SYSTEM,temperature=0)
    provider.last_raw_response=raw
    try:value=json.loads(raw)
    except (ValueError,TypeError) as error:raise ValueError('Optimization plan provider returned invalid JSON') from error
    provider.last_role_result=deepcopy(value)
    parsed=Plans.model_validate(value)
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
