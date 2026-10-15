"""Source-bound authored production fields for the existing V2 reconstructor.

Validates structural/source contracts and known textual deviations. Independent
semantic fidelity stays UNKNOWN: these checks are not a semantic story oracle.
"""
import re
from copy import deepcopy
from pydantic import Field
from typing import Literal
from .optimization_plans import Strict
from .optimization_distinctness import _beats
from app.parser.prompt_parser import parse_prompt

AUTHORING_VERSION = 'model-authored-production-v1'

class SpatialRelationship(Strict):
    subjectRef: str
    relation: Literal['LEFT_OF','RIGHT_OF','IN_FRONT_OF','BEHIND','ABOVE','BELOW','SEPARATED_FROM']
    objectRef: str
    instruction: str = Field(min_length=20,max_length=400)

class Choreography(Strict):
    sourceActionRef: str
    instruction: str = Field(min_length=25,max_length=600)
    sourceConsequenceRef: str
    consequencePresentation: str = Field(min_length=25,max_length=500)

class StatePresentation(Strict):
    sourceStateRef: str
    placementInstruction: str = Field(min_length=20,max_length=400)
    transitionPresentation: str = Field(min_length=20,max_length=400)

class AuthoredProduction(Strict):
    spatialRelationships: list[SpatialRelationship] = Field(max_length=6)
    choreography: Choreography
    stateProgression: list[StatePresentation] = Field(max_length=8)
    temporalPresentation: str = Field(min_length=25,max_length=500)
    cameraComposition: str = Field(min_length=20,max_length=400)
    generatorConstraints: list[str] = Field(min_length=1,max_length=5)

RELATION_WORDS = {
    'LEFT_OF':r'\bleft\b', 'RIGHT_OF':r'\bright\b',
    'IN_FRONT_OF':r'\b(?:front|foreground)\b', 'BEHIND':r'\b(?:behind|background)\b',
    'ABOVE':r'\b(?:above|upper)\b', 'BELOW':r'\b(?:below|lower)\b',
    'SEPARATED_FROM':r'\b(?:gap|apart|separat\w*|spac\w*)\b'}
GEOMETRY = re.compile(r'\b(?:left|right|foreground|background|above|below|diagonal|vertical|horizontal|row|rows|pair|pairs|gap|apart|offset|aligned|separated|beside)\b',re.I)


def reference_catalog(source, context, diagnosis):
    beats=_beats(source);parsed=parse_prompt(source).video_plan_ir
    by_id={b['id']:b for b in beats};refs={}
    def add(beat, kind, key, quote):
        if not quote or quote == 'UNKNOWN': return
        annotations=[(m.start(),m.end()) for m in re.finditer(r'\[[^\]]*\]',beat['sourceQuote'])]
        matches=[m for m in re.finditer(re.escape(quote),beat['sourceQuote'])
                 if not any(m.start()<z and m.end()>a for a,z in annotations)]
        if not matches:return
        m=matches[0];start=beat['sourceSpan'][0]+m.start()
        refs[beat['id']+'.'+key]={'kind':kind,'beatId':beat['id'],'quote':quote,'sourceSpan':[start,start+len(quote)],'evidence':'EXACT_SOURCE_TEXT','semanticVerification':'UNKNOWN'}
    for i,b in enumerate(beats):
        add(b,'ACTION','action',context['essentialEvents'][i])
        if '->' in b['sourceQuote']:
            result=b['sourceQuote'].split('->',1)[1].strip()
            result=re.sub(r'\[[^\]]*\]','',result).strip()
            add(b,'CONSEQUENCE','consequence',result)
        fields=b.get('fieldEvidence',{})
        for field,key in [('actor','actor'),('primaryObject','object')]:
            add(b,'ENTITY',key,(fields.get(field) or {}).get('sourceQuote'))
        # Generic source-mentioned anatomy, never invented character appearance.
        for noun in ('hand','hands','finger','fingers','arms','legs','face'):
            match=re.search(r'\b'+noun+r'\b',re.sub(r'\[[^\]]*\]','',b['sourceQuote']),re.I)
            if match:add(b,'ENTITY',noun,match[0])
    causal=parsed.get('coreMechanic',{}).get('surfaceAttachmentEvidence',{})
    for role in ('expectedSurface','actualSurface'):
        add(beats[0],'ENTITY',role,(causal.get(role) or {}).get('value'))
    for opportunity in diagnosis['opportunities']:
        if opportunity['operation']=='COUNTABLE_STATE_PATH':
            b=by_id[opportunity['beatId']]
            region=re.search(r'\bmultiply from (.+?) as ',b['sourceQuote'],re.I)
            for i,state in enumerate(opportunity['bindings']):
                # Resolve inside the actual progression, not an unrelated count mention.
                m=re.search(re.escape(state),region[1]);start=b['sourceSpan'][0]+region.start(1)+m.start()
                refs[b['id']+'.state.'+str(i)]={'kind':'STATE','beatId':b['id'],'quote':state,'sourceSpan':[start,start+len(state)],'evidence':'EXACT_SOURCE_TEXT','semanticVerification':'UNKNOWN'}
    return refs


def _resolve(text, refs):
    def replace(match):
        ref=refs.get(match[1])
        if not ref:raise ValueError('STORY_FIDELITY_FAILED: unknown authored source reference '+match[1])
        return ref['quote']
    return re.sub(r'\{([\w.:-]+)\}',replace,text)


def authored_fields(production):
    fields=[]
    def add(path,value):fields.append((path,value))
    for i,relation in enumerate(production.spatialRelationships):add(f'spatialRelationships.{i}.instruction',relation.instruction)
    add('choreography.instruction',production.choreography.instruction)
    add('choreography.consequencePresentation',production.choreography.consequencePresentation)
    for i,state in enumerate(production.stateProgression):
        add(f'stateProgression.{i}.placementInstruction',state.placementInstruction)
        add(f'stateProgression.{i}.transitionPresentation',state.transitionPresentation)
    add('temporalPresentation',production.temporalPresentation)
    add('cameraComposition',production.cameraComposition)
    for i,text in enumerate(production.generatorConstraints):add(f'generatorConstraints.{i}',text)
    return fields


def _text_guards(text, source):
    if any(c in text for c in ('[',']','\n','\r')) or '->' in text or len(text)>650:
        raise ValueError('STORY_FIDELITY_FAILED: authored instructions cannot inject sections, narrative delimiters or timing rows')
    if re.search(r'\b\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*s\b',text,re.I):
        raise ValueError('STORY_FIDELITY_FAILED: preserve source beat windows; no unbound sub-beat timestamps')
    if re.search(r'\b(?:PRODUCTION SETTINGS|CHARACTER IDENTITY|FINAL CUT|SYSTEM PROMPT)\b',text,re.I):
        raise ValueError('STORY_FIDELITY_FAILED: protected section override')
    for sentence in re.split(r'(?<=[.!?])\s+|;',text):
        lower=sentence.lower()
        # Safety constraints may prohibit a deviation, but may not introduce it.
        prohibited=bool(re.search(r'\b(?:do not|never|no |without |avoid )',lower))
        if not prohibited and re.search(r'\b(?:add|introduce|invent|perform|make|create)\b.{0,35}\b(?:third|extra|additional|new)\s+(?:pull|attempt|event|character|mechanic)\b',lower):
            raise ValueError('STORY_FIDELITY_FAILED: invented narrative attempt or event')
        if not prohibited and re.search(r'\b(?:skip|omit|erase|replace|reverse|remove)\b.{0,40}\b(?:ending|story|rule|character|mirror|scream|sneeze|event)\b',lower):
            raise ValueError('STORY_FIDELITY_FAILED: protected event or ending override')
        for word in re.findall(r'\b(?:teleport\w*|tripl\w*|vanish\w*|explod\w*|burn\w*|transform\w*)\b',lower):
            if word not in source.lower() and not prohibited:
                raise ValueError('STORY_FIDELITY_FAILED: unsupported physical transformation')
        # Recognize unbound named actors in action claims without mistaking
        # every sentence-initial production verb (e.g. Contact/Follow) for a name.
        names=re.findall(r'\b([A-Z][a-z]+)\s+(?:reaches|pulls|grabs|appears|enters|takes|sneezes|screams|becomes)\b',sentence)
        for name in names:
            if name.lower() not in source.lower():
                raise ValueError('STORY_FIDELITY_FAILED: unsupported named actor '+name)
        for forbidden_identity in re.findall(r'do not render (?:a|an) (\w+)',source,re.I):
            if not prohibited and re.search(r'\b(?:render|become|becomes|as)\b.{0,35}\b'+re.escape(forbidden_identity)+r'\b',sentence,re.I):
                raise ValueError('STORY_FIDELITY_FAILED: protected character identity override')
        # Object introduction is checked conservatively; the validator still does
        # not claim complete natural-language semantic fidelity.
        match=re.search(r'\b(?:introduce|add|bring|spawn)\s+(?:a|an|another|new)\s+(\w+)',lower)
        if match and match[1] not in source.lower() and match[1] not in {'gap','row','pair','view','angle','composition','alignment'} and not prohibited:
            raise ValueError('STORY_FIDELITY_FAILED: unsupported object introduction')
        if re.search(r'\b(?:guaranteed|proven)\b.{0,25}\b(?:render|retention|engagement|quality|success)\b',lower) and not prohibited:
            raise ValueError('UNSUPPORTED_AUDIENCE_OR_RENDER_CLAIM')


def _words(text):return set(re.findall(r'\w+',text.casefold()))-{'the','a','an','her','his','their','is','to','of','and'}

def validate_authored(intervention, opportunity, refs, source):
    production=intervention.production;beat=opportunity['beatId']
    from types import SimpleNamespace
    from .optimization_plans import _validate_outcome_claims
    try:
        _validate_outcome_claims(SimpleNamespace(candidateId='authored-plan',title='',baselineOpportunity='',
            proposedVisualConsequence='',materialDifference='',risksIntroduced=[],unknowns=[],
            risksReducedHypotheses=[text for _,text in authored_fields(production)]))
    except ValueError:
        raise ValueError('UNSUPPORTED_AUDIENCE_OR_RENDER_CLAIM')
    def require(key,kind):
        ref=refs.get(key)
        if not ref or ref['kind']!=kind or ref['beatId']!=beat:
            raise ValueError('STORY_FIDELITY_FAILED: wrong beat, kind or unsupported source reference '+key)
        return ref
    require(production.choreography.sourceActionRef,'ACTION')
    require(production.choreography.sourceConsequenceRef,'CONSEQUENCE')
    for _,raw in authored_fields(production):
        _text_guards(_resolve(raw,refs),source)
        # Explicit curly references must also stay within this source event.
        for key in re.findall(r'\{([\w.:-]+)\}',raw):
            if refs[key]['beatId']!=beat:raise ValueError('STORY_FIDELITY_FAILED: authored instruction imports a different source event')
    relations=[]
    for relation in production.spatialRelationships:
        subject=require(relation.subjectRef,'ENTITY');obj=require(relation.objectRef,'ENTITY')
        if relation.subjectRef==relation.objectRef:raise ValueError('Non-material authored spatial relation repeats the same entity')
        instruction=_resolve(relation.instruction,refs)
        if not re.search(RELATION_WORDS[relation.relation],instruction,re.I):raise ValueError('Non-material authored relation lacks its stated visible geometry')
        if not all(_words(q['quote'])&_words(instruction) for q in (subject,obj)):
            raise ValueError('STORY_FIDELITY_FAILED: spatial instruction does not address its bound participants')
        relations.append(relation)
    state_keys=[key for key,value in refs.items() if value['kind']=='STATE' and value['beatId']==beat]
    if opportunity['operation']=='COUNTABLE_STATE_PATH':
        if [s.sourceStateRef for s in production.stateProgression]!=state_keys:
            raise ValueError('STORY_FIDELITY_FAILED: authored progression omits, changes or reorders source states')
        geometries=[]
        numbers={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'twelve':12}
        for state in production.stateProgression:
            expected=require(state.sourceStateRef,'STATE')['quote'].lower()
            text=_resolve(state.placementInstruction,refs)
            for count in re.findall(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+(?:sticky\s+)?notes?\b',text,re.I):
                if numbers.get(count.lower(),count)!=numbers.get(expected,expected):
                    raise ValueError('STORY_FIDELITY_FAILED: authored note count contradicts its source state')
            if not re.search(r'\b'+re.escape(expected)+r'\b',text,re.I):
                raise ValueError('Non-material authored progression does not present its bound state')
            geometry=frozenset({'pairs':'pair','rows':'row','separated':'apart'}.get(x.lower(),x.lower()) for x in GEOMETRY.findall(text))
            if not geometry:raise ValueError('Non-material authored progression only repeats source counts')
            geometries.append(geometry)
        if len(set(geometries))<2:raise ValueError('Non-material authored progression has no differentiated state presentation')
    elif production.stateProgression:
        raise ValueError('STORY_FIDELITY_FAILED: invented state progression on an unrelated event')
    if opportunity['operation']=='CONTACT_PLANE':
        required={beat+'.expectedSurface',beat+'.actualSurface'}
        relevant=[r for r in relations if {r.subjectRef,r.objectRef}==required]
        if not relevant:raise ValueError('Non-material authored contact plan must stage both intended and actual source surfaces')
        if not any(not re.search(RELATION_WORDS[r.relation],opportunity['currentExecution'],re.I) for r in relevant):
            raise ValueError('Non-material authored contact staging repeats baseline geometry')
    elif opportunity['operation']=='SEPARATE_ACTION_RESULT' and not relations:
        raise ValueError('Non-material authored action/result plan has no concrete spatial presentation')
    rendered=' '.join(_resolve(text,refs) for _,text in authored_fields(production))
    if rendered in opportunity['currentExecution']:raise ValueError('Non-material authored execution repeats baseline')
    if intervention.camera!='LOCKED':raise ValueError('EXECUTION_RISK_REGRESSION_MOVING_CONTACT_VIEW')
    camera_text = production.cameraComposition
    if re.search(r'\b(?:tracking|panning|orbiting|zooming|moving)\s+(?:camera|shot|view)|\b(?:track|pan|orbit|zoom)\b', camera_text, re.I) and not re.search(r'\b(?:no|never|avoid|without)\s+(?:tracking|panning|orbiting|zooming|moving|track|pan|orbit|zoom)\b', camera_text, re.I):
        raise ValueError('EXECUTION_RISK_REGRESSION_CONTRADICTORY_CAMERA_INSTRUCTION')
    for sentence in re.split(r'(?<=[.!?])\s+|;',rendered):
        if re.search(r'\b(?:hide|obscure|occlude)\b.{0,30}\b(?:contact|count|transition)\b',sentence,re.I) and not re.search(r'\b(?:do not|never|without|avoid)\s+(?:hide|obscure|occlude)',sentence,re.I):
            raise ValueError('EXECUTION_RISK_REGRESSION_CRITICAL_TRANSITION_OCCLUDED')
    return {'status':'SOURCE_BOUND_AUTHORED_EXECUTION_VALIDATED','semanticFidelity':'UNKNOWN',
            'materialityMethod':'SOURCE_BOUND_SPATIAL_RELATIONS_AND_STATE_GEOMETRY',
            'limitations':['Deterministic structural and known-deviation checks are not complete semantic validation.','Independent story and visual review remain required.']}


def assemble_authored(intervention, opportunity, refs, source):
    validation=validate_authored(intervention,opportunity,refs,source)
    pieces=[];provenance=[];offset=0
    for path,raw in authored_fields(intervention.production):
        value=_resolve(raw,refs)
        if pieces:offset+=1
        pieces.append(value)
        provenance.append({'field':'production.'+path,'author':'MODEL_AUTHORED','rawText':raw,
            'compiledText':value,'localSpan':[offset,offset+len(value)],
            'referenceSubstitutions':[{'referenceId':key,'source':deepcopy(refs[key])} for key in re.findall(r'\{([\w.:-]+)\}',raw)]})
        offset+=len(value)
    return ' '.join(pieces),validation,provenance


def provenance_spans(source, prompt, beats):
    """Partition every compiled code point, including substituted source text.

    Equal source fragments outside changed annotations retain exact source offsets.
    The compiler owns delimiters/separators/profile normalization; never choreography.
    """
    from difflib import SequenceMatcher
    origins=[('SERVER_ASSEMBLY',None,None)]*len(prompt)
    for block in SequenceMatcher(None,source,prompt,autojunk=False).get_matching_blocks():
        for n in range(block.size):origins[block.b+n]=('PROTECTED_SOURCE',block.a+n,None)
    for beat in beats:
        row=next(b for b in _beats(prompt) if b['id']==beat['beatId'])
        for annotation in re.finditer(r'\[[^\]]*\]',row['sourceQuote']):
            a=row['sourceSpan'][0]+annotation.start();z=row['sourceSpan'][0]+annotation.end()
            origins[a:z]=[('SERVER_ASSEMBLY',None,None)]*(z-a)
        for instruction in beat['instructions']:
            start,end=instruction['candidateSpan']
            # Include annotation delimiters and all inter-field separators as compiler work.
            origins[start:end]=[('SERVER_ASSEMBLY',None,None)]*(end-start)
            if instruction['author']=='SERVER_TEMPLATE':
                origins[start:end]=[('SERVER_TEMPLATE',None,None)]*(end-start)
            for field in instruction['fields']:
                a,z=field['candidateSpan'];path=beat['beatId']+'.'+field['field']
                origins[a:z]=[('MODEL_AUTHORED',None,path)]*(z-a)
                cursor=a
                refs={r['referenceId']:r['source'] for r in field['referenceSubstitutions']}
                offset=0
                for match in re.finditer(r'\{([\w.:-]+)\}',field['rawText']):
                    cursor+=match.start()-offset
                    ref=refs[match[1]]
                    for n in range(len(ref['quote'])):origins[cursor+n]=('SOURCE_BOUND_SUBSTITUTION',ref['sourceSpan'][0]+n,path)
                    cursor+=len(ref['quote']);offset=match.end()
    profile=re.search(r'Content profile:\s*[^.\n]+',prompt)
    if profile and profile[0] not in source:
        origins[profile.start():profile.end()]=[('AUTHORITATIVE_SETTINGS',None,None)]*len(profile[0])
    result=[]
    for i,(author,source_offset,field) in enumerate(origins):
        if result and result[-1]['author']==author and result[-1].get('field')==field and ((source_offset is None and result[-1].get('sourceSpan') is None) or (source_offset is not None and result[-1].get('sourceSpan',[None,None])[1]==source_offset)):
            result[-1]['candidateSpan'][1]=i+1
            if source_offset is not None:result[-1]['sourceSpan'][1]=source_offset+1
        else:
            row={'author':author,'candidateSpan':[i,i+1]}
            if field:row['field']=field
            if source_offset is not None:row['sourceSpan']=[source_offset,source_offset+1]
            result.append(row)
    for row in result:
        a,z=row['candidateSpan'];row['text']=prompt[a:z]
    return result
