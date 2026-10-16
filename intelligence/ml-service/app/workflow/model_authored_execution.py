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

LEGACY_AUTHORING_VERSION = 'model-authored-production-v1'
AUTHORING_VERSION = 'model-authored-production-v2'

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


class ChoreographyV2(Choreography):
    instruction: str = Field(min_length=15,max_length=600)
    consequencePresentation: str | None = Field(min_length=15,max_length=500)

class StatePresentationV2(StatePresentation):
    transitionPresentation: str | None = Field(min_length=15,max_length=400)

class AuthoredProductionV2(AuthoredProduction):
    choreography: ChoreographyV2
    stateProgression: list[StatePresentationV2] = Field(max_length=8)
    temporalPresentation: str | None = Field(min_length=15,max_length=500)
    cameraComposition: str | None = Field(min_length=15,max_length=400)
    generatorConstraints: list[str] = Field(max_length=5)

RELATION_WORDS = {
    'LEFT_OF':r'\bleft\b', 'RIGHT_OF':r'\bright\b',
    'IN_FRONT_OF':r'\b(?:front|foreground)\b', 'BEHIND':r'\b(?:behind|background)\b',
    'ABOVE':r'\b(?:above|upper)\b', 'BELOW':r'\b(?:below|lower)\b',
    'SEPARATED_FROM':r'\b(?:gap|apart|separat\w*|spac\w*)\b'}
GEOMETRY = re.compile(r'\b(?:left|right|foreground|background|above|below|diagonal|vertical|horizontal|row|rows|pair|pairs|gap|apart|offset|aligned|separated|beside)\b',re.I)


def reference_catalog(source, context, diagnosis, enrich=False):
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
    if enrich:
        # Source mentions, not invented physical identities. Other/each-hand
        # references remain unresolved aliases until independent evidence exists.
        anatomy=r'(?:hands?|fingers?|arms?|legs?|faces?|paws?|feet|foot|wings?)'
        for b in beats:
            narrative=re.sub(r'\[[^\]]*\]',lambda m:' '*len(m[0]),b['sourceQuote'])
            patterns=[r'\b(?:her|his|their|its|each|the|one)\s+(?:(?:other|left|right|front|back)\s+)?'+anatomy+r'\b']
            obj=(b.get('fieldEvidence',{}).get('primaryObject') or {}).get('sourceQuote')
            if obj:
                patterns.append(r'\b(?:the|a|an|her|his|their|its)\s+(?:[\w\'-]+\s+){0,2}?'+re.escape(obj)+r'\b')
            mentions=sorted({(m.start(),m.end(),m[0]) for pattern in patterns for m in re.finditer(pattern,narrative,re.I)})
            seen_quotes=set();n=0
            for a,z,quote in mentions:
                if quote.casefold() in seen_quotes or re.search(r'\b(?:number|amount|count) of\b',quote,re.I):continue
                seen_quotes.add(quote.casefold())
                start=b['sourceSpan'][0]+a
                refs[b['id']+'.entity.'+str(n)]={'kind':'ENTITY','beatId':b['id'],'quote':quote,
                    'sourceSpan':[start,start+len(quote)],'evidence':'EXACT_SOURCE_TEXT',
                    'semanticVerification':'UNKNOWN','identityResolution':'UNKNOWN_SOURCE_MENTION_ONLY'}
                n+=1
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
    def add(path,value):
        if value is not None:fields.append((path,value))
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


def _text_guards(text, source, source_beat=None):
    if any(c in text for c in ('[',']','\n','\r')) or '->' in text or len(text)>650:
        raise ValueError('STORY_FIDELITY_FAILED: authored instructions cannot inject sections, narrative delimiters or timing rows')
    temporal = temporal_evidence(text,source,source_beat) if source_beat is not None else None
    if source_beat is None and re.search(r'\b\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*s\b',text,re.I):
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

    return temporal


def _words(text):return set(re.findall(r'\w+',text.casefold()))-{'the','a','an','her','his','their','is','to','of','and'}

def _validate_authored_v1(intervention, opportunity, refs, source):
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
            if any(a<=i['candidateSpan'][0]<z for i in beat['instructions']):
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


# V2 corrects authoring semantics only. V1 replay retains its original checks.
NUMBER_WORDS={'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'fifteen':15,'twenty':20}
TIME_RANGE=re.compile(r'(?<![\w.])(-?\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)?\s*(?:[-–—]|\bto\b)\s*(-?\d+(?:\.\d+)?)\s*-?\s*(?:seconds?|secs?|s)\b',re.I)
PHYSICAL_GEOMETRY=re.compile(r'\b(?:left|right|foreground|background|front|behind|above|below|diagonal(?:ly)?|vertical(?:ly)?|horizontal(?:ly)?|rows?|pairs?|gaps?|apart|offset|align\w*|edges?|silhouettes?|separat\w*)\b',re.I)


def temporal_evidence(text, source, beat):
    """Recognize existing windows without granting new temporal evidence.

    Numeric/spelled quantified timing is supported conservatively. Acceptance of
    a repeated source window conveys no materiality or story-semantic PASS.
    """
    normalized=re.sub(r'\b('+ '|'.join(NUMBER_WORDS)+r')\b',lambda m:str(NUMBER_WORDS[m[0].lower()]),text,flags=re.I)
    normalized=re.sub(r'(\d+)-to-(\d+)-second\b',r'\1-\2s',normalized,flags=re.I)
    windows={(b['startTime'],b['endTime']) for b in _beats(source)}
    target_end=max(z for a,z in windows);bound=(beat['startTime'],beat['endTime']);advisories=[]
    masked=list(normalized)
    for m in TIME_RANGE.finditer(normalized):
        a,z=float(m[1]),float(m[2])
        if a<0 or z<=a:raise ValueError('TEMPORAL_CONTRACT_INVALID: INVALID_TIME_RANGE')
        if z>target_end:raise ValueError('STORY_FIDELITY_FAILED: STORY_DURATION_CHANGED')
        if (a,z)==bound:
            advisories.append({'code':'SOURCE_BEAT_WINDOW_REPEATED','range':[a,z],'materialEvidence':False})
        elif (a,z) in windows:raise ValueError('TEMPORAL_CONTRACT_INVALID: WRONG_SOURCE_BEAT_WINDOW')
        elif bound[0]<=a<z<=bound[1]:raise ValueError('TEMPORAL_CONTRACT_INVALID: UNSUPPORTED_NEW_SUB_BEAT_TIMING')
        else:raise ValueError('TEMPORAL_CONTRACT_INVALID: CHANGED_SOURCE_BEAT_WINDOW')
        masked[m.start():m.end()]=[' ']*(m.end()-m.start())
    rest=''.join(masked)
    for m in re.finditer(r'\b(\d+(?:\.\d+)?)\s*-?\s*(?:seconds?|secs?|s)\b',rest,re.I):
        value=float(m[1]);near=rest[max(0,m.start()-45):m.end()+30]
        if re.search(r'\b(?:video|story|runtime|total duration|target duration|original duration)\b',near,re.I):
            if value!=target_end:raise ValueError('STORY_FIDELITY_FAILED: STORY_DURATION_CHANGED')
            advisories.append({'code':'SOURCE_DURATION_REPEATED','duration':value,'materialEvidence':False})
        elif re.search(r'\bat\s*$',rest[:m.start()],re.I) and value in bound:
            advisories.append({'code':'SOURCE_BEAT_BOUNDARY_REPEATED','time':value,'materialEvidence':False})
        else:raise ValueError('TEMPORAL_CONTRACT_INVALID: UNSUPPORTED_TEMPORAL_CLAIM')
    return advisories


def authoring_reference_contract(refs, diagnosis):
    by_kind={kind:[key for key,value in refs.items() if value['kind']==kind] for kind in ('ENTITY','ACTION','CONSEQUENCE','STATE')}
    opportunities=[]
    for op in diagnosis['opportunities']:
        allowed={kind:[key for key in ids if refs[key]['beatId']==op['beatId']] for kind,ids in by_kind.items()}
        row={'opportunityId':op['opportunityId'],'beatId':op['beatId'],'allowedReferenceIdsByKind':allowed,
             'groundingStatus':'SOURCE_MENTIONS_ONLY; ENTITY_IDENTITY_AND_STORY_SEMANTICS_UNKNOWN'}
        if op['operation']=='CONTACT_PLANE':row['requiredSurfacePair']=[op['beatId']+'.expectedSurface',op['beatId']+'.actualSurface']
        opportunities.append(row)
    return {'version':AUTHORING_VERSION,'referenceEncoding':'EXACT_CATALOG_KEY_NOT_ENTITY_NAME_OR_QUOTE',
        'allowedReferenceIdsByKind':by_kind,'opportunityContracts':opportunities,
        'missingEvidencePolicy':'No grounded ID means UNKNOWN; omit an unsupported relation or return no justified improvement. Never invent IDs or entities.',
        'spatialRelationshipProtocol':{
            'subjectAndObject':'Each instruction must describe both its exact subjectRef and objectRef, not merely a plural group or the final consequence.',
            'recommendedEncoding':'Use {subjectRef} and {objectRef} placeholders in instruction text so exact source participants remain auditable.',
            'compositeMentions':'A composite mention such as “each hand” does not establish separate left/right hand identities. Use multiple exact catalog references only when the source catalog supplies them.',
            'multiObjectStaging':'A proposal involving multiple independently positioned objects needs one grounded relationship per supported participant pair; otherwise omit it or return no justified improvement.'},
        'relationshipMeaning':{key:'subjectRef is '+key.lower().replace('_',' ')+' objectRef in the proposed view' for key in RELATION_WORDS},
        'fieldUse':{'objective':'One source-cited execution weakness, not a rewritten event.',
            'rationale':'Contrast baseline execution with the physical intervention and explain its observable difference; benefit is a hypothesis.',
            'choreography.instruction':'Only how the existing action is staged/performed differently; do not retell the story.',
            'consequencePresentation':'New visible cause/result presentation, or null when unchanged.',
            'temporalPresentation':'New supported relative presentation, or null. Repeated source windows are redundant, never improvement evidence.',
            'cameraComposition':'Only composition needed for the physical intervention, otherwise null.',
            'generatorConstraints':'Only intervention-specific execution constraints; [] when none. Do not repeat protected model/aspect-ratio/profile settings.'}}


def constrain_reference_schema(schema, refs, diagnosis):
    """Constrain wire IDs by kind. Per-opportunity beat scope remains a consumer check."""
    kinds=authoring_reference_contract(refs,diagnosis)['allowedReferenceIdsByKind'];defs=schema['$defs']
    for name,fields in [('SpatialRelationship',{'subjectRef':'ENTITY','objectRef':'ENTITY'}),
                        ('ChoreographyV2',{'sourceActionRef':'ACTION','sourceConsequenceRef':'CONSEQUENCE'}),
                        ('StatePresentationV2',{'sourceStateRef':'STATE'})]:
        for field,kind in fields.items():
            if kinds[kind]:defs[name]['properties'][field]['enum']=kinds[kind]
    if not kinds['STATE']:defs['AuthoredProductionV2']['properties']['stateProgression']['maxItems']=0
    for definition in defs.values():
        properties=definition.get('properties',{})
        if 'opportunityId' in properties and 'production' in properties:
            properties['opportunityId']['enum']=[o['opportunityId'] for o in diagnosis['opportunities']]
    # With no supported opportunities, no intervention can be proposed.
    if not diagnosis['opportunities']:
        del defs['AuthoredInterventionV2']['properties']['opportunityId']['enum']
        schema['properties']['proposals']['maxItems']=0
    return schema


def _features(text):
    return frozenset({'pairs':'pair','rows':'row','separated':'apart','separate':'apart','gaps':'gap','edges':'edge','diagonally':'diagonal','horizontally':'horizontal','vertically':'vertical'}.get(word.lower(),word.lower()) for word in PHYSICAL_GEOMETRY.findall(text))


def materiality_review(intervention, opportunity, refs):
    """Conservative production-difference evidence, independent of wire validity.

    Visibility adjectives, operation labels, camera prose, metadata and repeated
    timecodes cannot supply the physical difference. This is not a creative oracle.
    """
    p=intervention.production
    def resolved(text):
        try:return _resolve(text or '',refs)
        except ValueError:return text or ''
    core=' '.join(resolved(text) for text in [*(r.instruction for r in p.spatialRelationships),p.choreography.instruction,p.choreography.consequencePresentation])
    baseline=re.sub(r'\[[^\]]*\]','',opportunity['currentExecution'])
    delta=_features(core)-_features(baseline);reasons=[]
    relations=[r for r in p.spatialRelationships if re.search(RELATION_WORDS[r.relation],resolved(r.instruction),re.I)]
    if opportunity['operation']=='COUNTABLE_STATE_PATH':
        placements=[_features(resolved(s.placementInstruction)) for s in p.stateProgression]
        if not placements or any(not x for x in placements) or len(set(placements))<2:
            reasons.append('NO_DIFFERENTIATED_STATE_GEOMETRY')
        # A count sequence alone was already in the source; actual arrangements are required.
        material=bool(placements) and not reasons
    else:
        if not relations:reasons.append('NO_EXPLICIT_PHYSICAL_RELATION_INSTRUCTIONS')
        if not delta:reasons.append('NO_OBSERVABLE_PHYSICAL_EXECUTION_DELTA')
        if opportunity['operation']=='CONTACT_PLANE':
            pair={opportunity['beatId']+'.expectedSurface',opportunity['beatId']+'.actualSurface'}
            if not any({r.subjectRef,r.objectRef}==pair for r in relations):reasons.append('NO_INTENDED_VERSUS_ACTUAL_CONTACT_STAGING')
        material=bool(relations and delta) and not reasons
    return {'classification':'MATERIAL_TEXTUAL_CHANGE_UNVERIFIED' if material else 'VALID_BUT_EQUIVALENT',
        'material':material,'reasons':reasons,'newPhysicalFeatures':sorted(delta),
        'excludedEvidence':['reference validity alone','field count or text length','camera-label expansion','source consequence restatement','unchanged settings','repeated timecodes'],
        'method':'SOURCE_BOUND_PHYSICAL_RELATION_OR_STATE_ARRANGEMENT_DIFFERENCE',
        'visualBenefit':'UNKNOWN','audienceBenefit':'UNMEASURED','creativeQualityProven':False}


def review_authored(intervention, opportunity, refs, source):
    """Report technical validity, source/risk and materiality independently."""
    p=intervention.production;beat=next(b for b in _beats(source) if b['id']==opportunity['beatId'])
    technical=[];source_errors=[];risks=[];advisories=[]
    def reference(path,key,kind):
        value=refs.get(key);allowed=[k for k,v in refs.items() if v['kind']==kind and v['beatId']==beat['id']]
        code='INVALID_CATALOG_REFERENCE' if not value else 'WRONG_REFERENCE_KIND' if value['kind']!=kind else 'CROSS_BEAT_REFERENCE' if value['beatId']!=beat['id'] else None
        if code:technical.append({'code':code,'field':path,'referenceId':key,'expectedKind':kind,'expectedBeat':beat['id'],'allowedIds':allowed,'message':'Use an exact allowed catalog ID; entity-name aliases are never resolved silently.'})
    reference('choreography.sourceActionRef',p.choreography.sourceActionRef,'ACTION')
    reference('choreography.sourceConsequenceRef',p.choreography.sourceConsequenceRef,'CONSEQUENCE')
    for n,r in enumerate(p.spatialRelationships):
        reference(f'spatialRelationships.{n}.subjectRef',r.subjectRef,'ENTITY');reference(f'spatialRelationships.{n}.objectRef',r.objectRef,'ENTITY')
    for n,state in enumerate(p.stateProgression):reference(f'stateProgression.{n}.sourceStateRef',state.sourceStateRef,'STATE')
    from types import SimpleNamespace
    from .optimization_plans import _validate_outcome_claims
    try:_validate_outcome_claims(SimpleNamespace(candidateId='authored-plan',title='',baselineOpportunity='',proposedVisualConsequence='',materialDifference='',risksIntroduced=[],unknowns=[],risksReducedHypotheses=[text for _,text in authored_fields(p)]))
    except ValueError:technical.append({'code':'UNSUPPORTED_AUDIENCE_OR_RENDER_CLAIM','field':'production'})
    rendered=[]
    for path,raw in authored_fields(p):
        keys=re.findall(r'\{([\w.:-]+)\}',raw)
        for key in keys:
            if key not in refs:reference(path,key,'ENTITY')
            elif refs[key]['beatId']!=beat['id']:technical.append({'code':'CROSS_BEAT_REFERENCE','field':path,'referenceId':key})
        try:text=_resolve(raw,refs)
        except ValueError:continue
        rendered.append(text)
        try:
            for advisory in _text_guards(text,source,beat) or []:advisories.append({'field':path,**advisory})
        except ValueError as e:
            error={'code':str(e).split(': ',1)[-1],'field':path,'message':str(e)}
            (source_errors if str(e).startswith('STORY_FIDELITY_FAILED') else technical).append(error)
    for n,r in enumerate(p.spatialRelationships):
        if r.subjectRef in refs and r.objectRef in refs:
            a,z=refs[r.subjectRef]['sourceSpan'];c,d=refs[r.objectRef]['sourceSpan']
            if r.subjectRef==r.objectRef or max(a,c)<min(z,d):
                technical.append({'code':'SAME_SOURCE_MENTION_RELATION','field':f'spatialRelationships.{n}','message':'Distinct source IDs do not establish distinct entities when the mentions overlap.'})
            try:text=_resolve(r.instruction,refs)
            except ValueError:continue
            if not all(_words(refs[k]['quote'])&_words(text) for k in (r.subjectRef,r.objectRef)):
                source_errors.append({'code':'BOUND_PARTICIPANTS_NOT_ADDRESSED','field':f'spatialRelationships.{n}'})
    expected_states=[k for k,v in refs.items() if v['kind']=='STATE' and v['beatId']==beat['id']]
    if opportunity['operation']=='COUNTABLE_STATE_PATH':
        if [s.sourceStateRef for s in p.stateProgression]!=expected_states:
            source_errors.append({'code':'SOURCE_STATES_OMITTED_CHANGED_OR_REORDERED','field':'stateProgression'})
        for n,state in enumerate(p.stateProgression):
            if state.sourceStateRef not in refs:continue
            expected=refs[state.sourceStateRef]['quote'].casefold();expected_value=NUMBER_WORDS.get(expected,int(expected) if expected.isdigit() else expected)
            try:text=_resolve(state.placementInstruction,refs)
            except ValueError:continue
            counts=re.findall(r'\b(\d+|'+ '|'.join(NUMBER_WORDS)+r')\s+(?:sticky\s+)?notes?\b',text,re.I)
            value=lambda count:NUMBER_WORDS.get(count.casefold(),int(count) if count.isdigit() else count.casefold())
            if any(value(count)!=expected_value for count in counts):source_errors.append({'code':'SOURCE_STATE_COUNT_CHANGED','field':f'stateProgression.{n}.placementInstruction'})
            if not any(value(count)==expected_value for count in counts):
                technical.append({'code':'SOURCE_STATE_NOT_PRESENTED','field':f'stateProgression.{n}.placementInstruction'})
    elif p.stateProgression:source_errors.append({'code':'UNSUPPORTED_STATE_PROGRESSION_ON_OTHER_EVENT','field':'stateProgression'})
    joined=' '.join(rendered);camera=p.cameraComposition or ''
    if intervention.camera!='LOCKED':risks.append({'code':'EXECUTION_RISK_REGRESSION_MOVING_CONTACT_VIEW'})
    if re.search(r'\b(?:tracking|panning|orbiting|zooming|moving)\s+(?:camera|shot|view)|\b(?:track|pan|orbit|zoom)\b',camera,re.I) and not re.search(r'\b(?:no|never|avoid|without)\s+(?:tracking|panning|orbiting|zooming|moving|track|pan|orbit|zoom)\b',camera,re.I):risks.append({'code':'EXECUTION_RISK_REGRESSION_CONTRADICTORY_CAMERA_INSTRUCTION'})
    for sentence in re.split(r'(?<=[.!?])\s+|;',joined):
        if re.search(r'\b(?:hide|obscure|occlude)\b.{0,30}\b(?:contact|count|transition)\b',sentence,re.I) and not re.search(r'\b(?:do not|never|without|avoid)\s+(?:hide|obscure|occlude)',sentence,re.I):risks.append({'code':'EXECUTION_RISK_REGRESSION_CRITICAL_TRANSITION_OCCLUDED'})
    materiality=materiality_review(intervention,opportunity,refs)
    return {'instructionsVersion':AUTHORING_VERSION,'technicalValidity':'INVALID' if technical else 'VALID',
        'technicalDiagnostics':technical,'temporalAdvisories':advisories,
        'sourceFidelity':'VIOLATION_DETECTED' if source_errors else 'UNKNOWN','sourceDiagnostics':source_errors,
        'sourceGrounding':'UNVERIFIABLE' if any('REFERENCE' in e['code'] for e in technical) else 'SOURCE_REFERENCES_BOUND',
        'materiality':materiality,'productionRisk':'REGRESSION_DETECTED' if risks else 'UNVERIFIED_NO_DETERMINISTIC_REGRESSION',
        'riskDiagnostics':risks,'accepted':not technical and not source_errors and not risks and materiality['material'],
        'actualImprovementEvidence':'PLANNED_TEXT_ONLY; visual/creative benefit unverified'}


def validate_authored(intervention, opportunity, refs, source):
    if not isinstance(intervention.production,AuthoredProductionV2):
        return _validate_authored_v1(intervention,opportunity,refs,source)
    review=review_authored(intervention,opportunity,refs,source)
    if not review['accepted']:
        reasons=[('AUTHORING_CONTRACT_INVALID: '+e['code']) for e in review['technicalDiagnostics']]
        reasons += ['STORY_FIDELITY_FAILED: '+e['code'] for e in review['sourceDiagnostics']]
        reasons += [e['code'] for e in review['riskDiagnostics']]
        if not review['materiality']['material']:reasons.append('Non-material authored plan: '+', '.join(review['materiality']['reasons']))
        raise ValueError('; '.join(reasons))
    return {'status':'SOURCE_BOUND_AUTHORED_EXECUTION_VALIDATED','semanticFidelity':'UNKNOWN',
        'materialityMethod':review['materiality']['method'],'authoringReview':review,
        'limitations':['Deterministic checks establish planned physical differences, not successful rendering or complete semantic fidelity.']}
