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

def validate_execution_candidates(source,candidates,context):
    baseline=_beats(source);target=context.get('targetConfiguration') or {};settings=target.get('settings') or {}
    duration=target.get('duration',baseline[-1]['endTime']);ratio=settings.get('aspectRatio') or target.get('aspectRatio')
    protected=_outside(source,baseline);signatures=[]
    for index,candidate in enumerate(candidates):
        prompt=candidate['prompt'];beats=_beats(prompt);identity=candidate['candidateId']
        if len(beats)!=len(baseline):raise ValueError(f'{identity}: source-plan event coverage differs from baseline')
        if beats[0]['startTime']!=0 or beats[-1]['endTime']!=float(duration) or any(a['endTime']!=b['startTime'] for a,b in zip(beats,beats[1:])):
            raise ValueError(f'{identity}: source-plan timing must cover the configured duration without gaps or overlaps')
        if any(_narrative(a)!=_narrative(b) for a,b in zip(baseline,beats)) or _outside(prompt,beats)!=protected:
            raise ValueError(f'{identity}: approved source narrative, identity, physical rule or ending changed; candidate rejected')
        if ratio and set(re.findall(r'\b(?:9:16|16:9|1:1)\b',prompt))!={ratio}:raise ValueError(f'{identity}: source-plan aspect ratio conflicts with target')
        for key,label in [('generator','Target generator'),('contentProfile','Content profile')]:
            expected=target.get(key)
            if expected and expected!='UNKNOWN' and not re.search(re.escape(label)+r':\s*'+re.escape(str(expected))+r'\b',prompt,re.I):raise ValueError(f'{identity}: source-plan {key} conflicts with target')
        for source_beat,beat in zip(baseline,beats):
            allowed=_tokens(source_beat['sourceQuote'])|_CAMERA_WORDS
            annotations=' '.join(re.findall(r'\[([^\]]*)\]',beat['sourceQuote']))
            if _tokens(annotations)-allowed:raise ValueError(f'{identity}: unsupported annotation content; story fidelity remains unverified')
        signature=[_signature(b) for b in beats];before=[_signature(b) for b in baseline]
        changes=[i for i,(a,b) in enumerate(zip(before,signature)) if a!=b]
        if not changes:raise ValueError(f'{identity}: materially unchanged execution; paraphrases and commentary do not constitute optimization')
        if index==0 and before[0][2:]==signature[0][2:]:raise ValueError(f'{identity}: opening framing or camera decision must materially change')
        if index==1 and not any(i in changes for i in range(1,max(2,len(beats)-1))):raise ValueError(f'{identity}: mid-section pacing or camera decision must materially change')
        evidence=[]
        for i in changes:
            evidence.append({'beatId':beats[i]['id'],'baselineSourceSpan':baseline[i]['sourceSpan'],'candidateSourceSpan':beats[i]['sourceSpan'],'baselineQuote':baseline[i]['sourceQuote'],'candidateQuote':beats[i]['sourceQuote'],'before':before[i],'after':signature[i]})
        candidate['optimizationObjective']='FIRST_FRAME_ANOMALY_CLARITY_CURIOSITY' if index==0 else 'BEAT_PROGRESSION_TIMING_ESCALATION_SEEDANCE_FEASIBILITY'
        candidate['executionDistinctness']={'status':'MATERIAL_TEXT_EXECUTION_DIFFERENCE','method':'TIMING_FRAMING_CAMERA_SIGNATURE_V1','changes':evidence,'approvedStorySemanticFidelity':'UNKNOWN','generatorSuccess':'UNKNOWN','authorization':'NOT_EVALUATED'}
        signatures.append(signature)
    if signatures[0]==signatures[1]:raise ValueError('Candidates share the same execution decisions; wording-only differences are rejected')
    if signatures[0][0][2:]==signatures[1][0][2:]:raise ValueError('Candidate A and B must offer different first timed beat framing/camera decisions')
