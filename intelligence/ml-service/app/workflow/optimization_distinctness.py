"""Conservative text-only execution comparison; never semantic story approval."""
import re
from app.parser.prompt_parser import parse_prompt

_SHOTS=[('EXTREME_CLOSE',r'extreme\s+close'),('CLOSE',r'close[- ]?up|tight\s+shot|insert\s+shot'),('MEDIUM',r'medium\s+shot|mid[- ]?shot'),('WIDE',r'wide\s+shot|long\s+shot|full[- ]body')]
_MOTIONS=[('STATIC',r'static|locked[- ]off'),('TRACK',r'track(?:ing)?'),('PAN',r'\bpan\b'),('PUSH',r'push[- ]in')]
_CAMERA_WORDS=set('extreme close up tight insert medium mid wide long full body shot static locked off tracking track pan slow push in camera frame framing focus foreground background hold single continuous on of the a an and with from to eye level view over shoulder shallow depth field cut cuts clear readable center centred centered left right soft lighting light contrast zoom at'.split())

def _normalize(text):return ' '.join(re.findall(r'\w+',text.casefold()))
def _tokens(text):return set(re.findall(r'\w+',text.casefold()))
def _beats(text):
    beats=parse_prompt(text).video_plan_ir['beats']
    if not beats or any(b.get('sourceSpanStatus')!='TEXT_MATCHED' for b in beats):raise ValueError('Source-plan validation failed: exact timed source spans are required')
    return beats

def _signature(beat):
    annotations=' '.join(re.findall(r'\[([^\]]*)\]',beat['sourceQuote'])).casefold()
    shot=next((name for name,pattern in _SHOTS if re.search(pattern,annotations)),None)
    motion=next((name for name,pattern in _MOTIONS if re.search(pattern,annotations)),None)
    return (beat['startTime'],beat['endTime'],shot,motion)

def _narrative(beat):
    quote=re.sub(r'^\d+(?:\.\d+)?\s*[-–—]\s*\d+(?:\.\d+)?\s*(?:s|sec|seconds)\s*:?\s*','',beat['sourceQuote'],flags=re.I)
    return _normalize(re.sub(r'\[[^\]]*\]','',quote))

def _outside(text,beats):
    for b in reversed(beats):
        a,z=b['sourceSpan'];text=text[:a]+text[z:]
    # The saved production target overrides a stale profile label, not story content.
    return _normalize(re.sub(r'Content profile:\s*[A-Z_]+','Content profile: TARGET',text,flags=re.I))

def baseline_execution(text):
    return [{'beatId':b['id'],'sourceSpan':b['sourceSpan'],'startTime':b['startTime'],'endTime':b['endTime'],
             'framing':_signature(b)[2] or 'UNSPECIFIED','cameraMotion':_signature(b)[3] or 'UNSPECIFIED'} for b in _beats(text)]

def _coverage_groups(baseline, beats, anchors, identity):
    if len(beats)==len(baseline):
        groups=[[b] for b in beats]
    else:
        if not isinstance(anchors,list) or len(anchors)!=len(baseline):
            raise ValueError(f'{identity}: source-plan event coverage cannot be bound to source anchors')
        groups=[[] for _ in baseline];sequence=[]
        for beat in beats:
            matched=[i for i,anchor in enumerate(anchors) if anchor in beat['sourceQuote']]
            if len(matched)!=1:raise ValueError(f'{identity}: source-plan event coverage differs from baseline; shot has missing or ambiguous source event')
            groups[matched[0]].append(beat);sequence.append(matched[0])
        if sequence!=sorted(sequence) or any(not group for group in groups):
            raise ValueError(f'{identity}: source-plan event coverage differs from baseline; missing or reordered source event')
    for original,group in zip(baseline,groups):
        if len(group)==1:
            if _narrative(original)!=_narrative(group[0]):
                raise ValueError(f'{identity}: source-plan beat {baseline.index(original)+1} narrative/staging/consequence coverage differs from baseline; independent story fidelity is not established')
            continue
        # A supported textual progression may be divided into contiguous shots.
        # Prefix/action and suffix/staging/consequence must remain EXACT, and
        # concatenated progression edges must equal the source path verbatim.
        pattern=r'^(.*?\bmultiply from )(.+?)( as .*)$'
        source_match=re.match(pattern,_narrative(original))
        parts=[re.match(pattern,_narrative(beat)) for beat in group]
        if not source_match or any(not part for part in parts):
            raise ValueError(f'{identity}: source-plan split event lacks exact source progression evidence')
        path=[]
        for part in parts:
            if part[1]!=source_match[1] or part[3]!=source_match[3]:
                raise ValueError(f'{identity}: source-plan split event changes action, staging or consequence')
            edge=part[2].split(' to ')
            if len(edge)<2 or (path and path[-1]!=edge[0]):
                raise ValueError(f'{identity}: source-plan split progression is incomplete or discontinuous')
            path.extend(edge if not path else edge[1:])
        if path!=source_match[2].split(' to '):
            raise ValueError(f'{identity}: source-plan split progression does not preserve the complete source path')
    return groups


def validate_execution_candidates(source,candidates,context,candidate_indices=None):
    baseline=_beats(source);target=context.get('targetConfiguration') or {};settings=target.get('settings') or {}
    duration=target.get('duration',baseline[-1]['endTime']);ratio=settings.get('aspectRatio') or target.get('aspectRatio')
    protected=_outside(source,baseline);signatures=[]
    before=[[_signature(b)] for b in baseline]
    for index,candidate in enumerate(candidates):
        if candidate_indices is not None and index not in candidate_indices:continue
        prompt=candidate['prompt'];beats=_beats(prompt);identity=candidate['candidateId']
        if len(beats)==len(baseline) and [_signature(b) for b in beats]==[_signature(b) for b in baseline]:
            first=_signature(baseline[0])
            raise ValueError(f'{identity}: materially unchanged execution; first beat remains {first[2] or "UNSPECIFIED"} framing, {first[3] or "UNSPECIFIED"} camera motion, {first[0]}-{first[1]}s. Moving camera brackets, paraphrases or deleting prose is not optimization')
        groups=_coverage_groups(baseline,beats,context.get('essentialEvents'),identity)
        if beats[0]['startTime']!=0 or beats[-1]['endTime']!=float(duration) or any(a['endTime']!=b['startTime'] for a,b in zip(beats,beats[1:])):
            raise ValueError(f'{identity}: source-plan timing must cover the configured duration without gaps or overlaps')
        signature=[[_signature(b) for b in group] for group in groups]
        changes=[i for i,(a,b) in enumerate(zip(before,signature)) if a!=b]
        if signatures and signature==signatures[0]:raise ValueError('Candidates share the same execution decisions; wording-only differences are rejected')
        if not changes:raise ValueError(f'{identity}: materially unchanged execution; first beat remains {before[0][0][2] or "UNSPECIFIED"} framing, {before[0][0][3] or "UNSPECIFIED"} camera motion, {before[0][0][0]}-{before[0][0][1]}s. Moving camera brackets, paraphrases or deleting prose is not optimization')
        if index==0 and before[0][0][2:]==signature[0][0][2:]:raise ValueError(f'{identity}: opening framing or camera decision must materially change')
        if index==1 and not any(i in changes for i in range(1,max(2,len(baseline)-1))):raise ValueError(f'{identity}: mid-section pacing or camera decision must materially change')
        if ratio and set(re.findall(r'\b(?:9:16|16:9|1:1)\b',prompt))!={ratio}:raise ValueError(f'{identity}: source-plan aspect ratio conflicts with target')
        for key,label in [('generator','Target generator'),('contentProfile','Content profile')]:
            expected=target.get(key)
            if expected and expected!='UNKNOWN' and not re.search(re.escape(label)+r':\s*'+re.escape(str(expected))+r'\b',prompt,re.I):raise ValueError(f'{identity}: source-plan {key} conflicts with target')
        if _outside(prompt,beats)!=protected:
            raise ValueError(f'{identity}: source-plan protected text outside timed beats differs from baseline; identity, rule and ending coverage requires review')
        for source_beat,group in zip(baseline,groups):
            allowed=_tokens(source_beat['sourceQuote'])|_CAMERA_WORDS
            for beat in group:
                annotations=' '.join(re.findall(r'\[([^\]]*)\]',beat['sourceQuote']))
                if _tokens(annotations)-allowed:raise ValueError(f'{identity}: unsupported annotation content; story fidelity remains unverified')
        coverage=[];evidence=[]
        for i,group in enumerate(groups):
            mapping={'baselineBeatId':baseline[i]['id'],'baselineSourceSpan':baseline[i]['sourceSpan'],
                     'baselineQuote':baseline[i]['sourceQuote'],'candidateBeatIds':[b['id'] for b in group],
                     'candidateSourceSpans':[b['sourceSpan'] for b in group],
                     'candidateQuotes':[b['sourceQuote'] for b in group],
                     'method':'EXACT_TEXT_PROGRESSION_EDGES' if len(group)>1 else 'EXACT_SOURCE_NARRATIVE'}
            coverage.append(mapping)
            if i in changes:
                evidence.append({**mapping,'beatId':group[0]['id'],'candidateSourceSpan':group[0]['sourceSpan'],
                                 'candidateQuote':group[0]['sourceQuote'],'before':before[i][0],
                                 'after':signature[i][0],'candidateShotSignatures':signature[i]})
        candidate['sourceEventCoverage']={'status':'SOURCE_TEXT_COVERED','sourceEventCount':len(baseline),
                                        'candidateShotCount':len(beats),'mappings':coverage,'semanticFidelity':'UNKNOWN'}
        candidate['optimizationObjective']='FIRST_FRAME_ANOMALY_CLARITY_CURIOSITY' if index==0 else 'BEAT_PROGRESSION_TIMING_ESCALATION_SEEDANCE_FEASIBILITY'
        candidate['executionDistinctness']={'status':'MATERIAL_TEXT_EXECUTION_DIFFERENCE','method':'SOURCE_EVENT_GROUPED_EXECUTION_V2','changes':evidence,'approvedStorySemanticFidelity':'UNKNOWN','generatorSuccess':'UNKNOWN','authorization':'NOT_EVALUATED'}
        signatures.append(signature)
    if len(signatures)==2 and signatures[0][0][0][2:]==signatures[1][0][0][2:]:raise ValueError('Candidate A and B must offer different first timed beat framing/camera decisions')
