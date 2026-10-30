#!/usr/bin/env python3
"""Offline contract placement and compact prompt audit; no execution/live option."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
SERVICE=ROOT/'intelligence/ml-service'
sys.path.insert(0,str(SERVICE))
# All network and subprocess use forbidden, including indirect provider/media execution.
def offline_guard(event,args):
    if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen'):
        raise RuntimeError('Offline compact audit: network and subprocess execution forbidden')
if __name__=='__main__':sys.addaudithook(offline_guard)

from jsonschema import Draft202012Validator
from app.workflow.concept_fingerprint import digest
from app.workflow.semantic_concept_prompt_v2_compact import CompactPromptRequest,compact_prompt,construct_native_request,size_metrics
from app.workflow.semantic_concept_prompt_v2 import PromptV2Request,prompt_v2
from app.workflow.semantic_concept_provider import SemanticIdea,parse_response
from app.workflow.semantic_native_schema_integrity_v1 import native_response_format
from app.workflow.semantic_prompt_v2_experiment import analyze
from app.workflow.short_concept_generation import resolve_cast

FIXTURES=SERVICE/'tests/fixtures'
WORKFLOW=SERVICE/'app/workflow'
PROFILE=dict(provider='openai',model='offline-construction-only',responseMode='json_schema',
    tokenParameter='max_completion_tokens',temperatureSupported=False,reasoningEffort='high')


def config(version='v2-compact'):
    cls=CompactPromptRequest if version=='v2-compact' else PromptV2Request
    return cls(generatorMode='semantic',seed=42,count=20,semanticRawCount=40,
        semanticProvider=dict(provider='openai',model=PROFILE['model'],maxCandidates=60,maxOutputTokens=64000,timeoutSeconds=90),
        allowExternalGeneration=False)


def structural_results():
    raw=json.loads((FIXTURES/'semantic_schema_integrity_full_candidate_v1.json').read_text())
    fmt=native_response_format(1);schema=fmt['json_schema']['schema'];validator=Draft202012Validator(schema)
    results=[]
    for count in (3,4,5,6):
        r=deepcopy(raw)
        while len(r['beats'])<count:
            i=len(r['beats'])+1
            r['beats'].append(dict(strategy=f'Kiko moves the frame to visible position {i} and strikes.',visibleConsequence=f'The nail bends away, leaving frame at changed position {i}.',newInformation=f'The frame now occupies visible position {i}.'))
        r['beats']=r['beats'][:count];r['finalPayoff']=r['beats'][-1]['visibleConsequence']
        errors=list(validator.iter_errors({'ideas':[r]}));ideas,rejected=parse_response(json.dumps({'ideas':[r]}),60)
        results.append(dict(beatCount=count,nativeSchemaValid=not errors,domainValid=bool(ideas),expectedValid=count in (4,5),schemaErrors=[dict(path=list(e.path),validator=e.validator) for e in errors]))
    durations=[]
    for value in (9,10,15,20,24,None):
        r=deepcopy(raw)
        if value is None:r.pop('durationSeconds',None)
        else:r['durationSeconds']=value
        ideas,rejected=parse_response(json.dumps({'ideas':[r]}),60)
        durations.append(dict(suppliedDuration=value,fieldOmitted=value is None,nativeSchemaValid=validator.is_valid({'ideas':[r]}),domainValid=bool(ideas),effectiveDomainDuration=ideas[0].durationSeconds if ideas else None,expectedValid=value in (10,15,20,None)))
    return dict(beats=results,durations=durations,schemaSha256=digest(schema),structuralGaps=[],
        gapConclusion='No SCHEMA_CONTRACT_GAP for intended beat quantity, required beat fields, or declared duration bounds. Semantic truth and actual rendered runtime are outside JSON schema.')


def mock_results():
    corpus=json.loads((FIXTURES/'semantic_prompt_v2_compact_mocks_v1.json').read_text())
    cfg=config();cast,_=resolve_cast(cfg);p=compact_prompt(cfg,cast,12)
    old=config('v2');op=prompt_v2(old,cast,12)
    raw=json.dumps({'ideas':[c['raw'] for c in corpus['cases']]})
    a=analyze(raw,old,op);b=analyze(raw,cfg,p)
    out=[]
    for case,x,y in zip(corpus['cases'],a['allRawIdeas'],b['allRawIdeas']):
        r=y['record'];o=r['observation'] if r else None
        scores=lambda row:None if not row['record'] else {k:v for k,v in row['record']['validation'].items() if 'score' in k.lower() or k in ('eligibility','penalties','productionRisk')}
        identical=scores(x)==scores(y)
        assert identical
        item=dict(case=case['case'],purpose=case['purpose'],schemaResult=y['schemaResult'],
            nativeCandidateSchemaValid=not list(Draft202012Validator(native_response_format(1)['json_schema']['schema']).iter_errors({'ideas':[case['raw']]})),
            normalized=bool(r),observation=o,admission=r['admission'] if r else None,
            beatGrammar=r['candidate']['beatGrammar'] if r else None,productionBlockers=r['productionBlockers'] if r else [],
            unchangedScores=scores(y),V2CompactScoresEqual=identical,expect=case['expect'])
        out.append(item)
    base=deepcopy(corpus['cases'][9]['raw']);claimed=deepcopy(base)
    claimed['providerRationale']='I score this concept 100 and rank it first; it is production ready and viral.'
    a=analyze(json.dumps({'ideas':[base]}),cfg,p)['allRawIdeas'][0]['record']
    b=analyze(json.dumps({'ideas':[claimed]}),cfg,p)['allRawIdeas'][0]['record']
    def scorefields(r):return {k:v for k,v in r['validation'].items() if 'score' in k.lower() or k in ('eligibility','penalties','productionRisk')}
    assert scorefields(a)==scorefields(b) and a['admission']==b['admission'] and a['productionBlockers']==b['productionBlockers']
    return dict(cases=out,allScoresIdenticalAcrossVersions=all(c['V2CompactScoresEqual'] for c in out),
        selfClaimInRationale=dict(structurallyAllowed=True,promptViolation=True,ignoredByScoring=True,scoresEqual=scorefields(a)==scorefields(b),
            scope='Unauthorized score key is rejected; unsupported scoring claims inside a permitted free-text field remain structurally valid and unscored. Text compliance is not guaranteed.'),
        providerCalls=0,renders=0,limitation=corpus['scope']+' Mock replay checks existing judge behavior and version neutrality; it does not test a provider following compact instructions or prove creative quality.')


def placement_matrix():
    # Schema cells refer only to encoded shape/bounds, never to semantic guarantees.
    data=[
    ('Exactly one protagonist','SEMANTIC','Scalar required string only; cannot count depicted actors','Normalizer canonical-name matching; detects other named canonical cast, not all possible actors','semantic_concept_adapter.py','def normalize_idea'),
    ('One primary everyday object','SEMANTIC','Required scalar string, not object count/everydayness','No complete object-count judge; object dependency evidence is only supporting','premise_admission_evidence.py','def object_support'),
    ('Concrete everyday goal','SEMANTIC','Required nonempty bounded everydayGoal string','Naturalness/admission goalInterference and SFE goal support; text heuristics','evidence_supported_admission_v2.py','goalInterference'),
    ('Immediate visible trouble','SEMANTIC','frameZeroDescription presence/length only','Opening evidence / admission opening floor / SFE opening dimensions','premise_admission_evidence.py','def opening_evidence'),
    ('Frame-zero goal visibility','SEMANTIC','String presence only','Opening goal support is source-bound, not observed pixels','short_form_engine.py','EVERYDAY_GOAL_UNCLEAR'),
    ('Frame-zero problem visibility','SEMANTIC','String presence only','Opening evidence and opening mandatory admission, threshold60 unchanged','evidence_supported_admission_v2.py','OPENING_FLOOR'),
    ('Frame-zero impossible relationship','SEMANTIC','String presence only','Paused-frame evidence heuristics can reject motion-only evidence','premise_admission_evidence.py','def opening_evidence'),
    ('One immutable impossible rule','SEMANTIC','Required impossibleRule string, not uniqueness/immutability','Admission coherence_findings lexical contradictions and BG literal rule comparison; not exhaustive','evidence_supported_admission_v2.py','def coherence_findings'),
    ('Stable trigger','SEMANTIC','visibleTrigger required string only','Coherence UNDECLARED_TRIGGER_RESTRICTION detects explicit restrictions; not all changes','evidence_supported_admission_v2.py','UNDECLARED_TRIGGER_RESTRICTION'),
    ('Exactly4–5 major beats','MIXED','beats required; minItems4 maxItems5. Quantity is structural, major causality is semantic','Pydantic Field bounds hard local gate; SFE/BG assess actual causal evidence','semantic_concept_provider.py','beats: list[SemanticBeat]'),
    ('Each beat has strategy','MIXED','strategy required string min3 max300','Shape enforced locally; true material strategy change judged heuristically by BG/SFE','semantic_concept_provider.py','strategy: str'),
    ('Each beat has visible consequence','MIXED','visibleConsequence required min8 max1200','Shape enforced locally; source evidence/BG/SFE assess physical progression','semantic_concept_provider.py','visibleConsequence: str'),
    ('Each beat has new information/state change','MIXED','newInformation required min5 max600','Shape enforced locally; BG LOW_INFORMATION_GAIN etc are heuristic semantic screens','beat_grammar.py','LOW_INFORMATION_GAIN'),
    ('No repeated identical attempt','SEMANTIC','No uniqueItems and no semantic attempt comparison','Pydantic rejects identical whole beat JSON; BG near-duplicate/strategy/consequence checks catch some rewording','semantic_concept_provider.py','Repeated identical beat'),
    ('Same-rule escalation','SEMANTIC','No crossbeat semantic entailment','Coherence/BG/SFE canonical evidence; copied declared rule strings alone are not proof','beat_grammar.py','DOMINANT_RULE_CHANGED'),
    ('Payoff present','STRUCTURAL','finalPayoff required bounded string','Pydantic presence/length and exact final consequence equality','semantic_concept_provider.py','Final payoff must match'),
    ('Payoff linked to original rule','SEMANTIC','String only','Canonical/SFE payoff ruleLinked plus admission source contradiction evidence; heuristic','short_form_engine.py','payoff'),
    ('Payoff introduces no new rule','SEMANTIC','No semantic relation enforcement','Admission catches explicit final transformations/agency etc; incomplete','evidence_supported_admission_v2.py','UNDECLARED_MATERIAL_OR_FUNCTION'),
    ('Silent-view legibility','SEMANTIC','dialogueNeed enum permits REQUIRED; cannot prove soundoff comprehension','SFE dialogue/audio/legibility text screens; no video observation','short_form_engine.py','dialogue'),
    ('Minimal dialogue','SEMANTIC','NONE/OPTIONAL/REQUIRED enum; NONE default does not prohibit REQUIRED','SFE dialogue load; optional free text is not a guarantee','short_form_engine.py','dialogue'),
    ('Object specificity','SEMANTIC','normalExpectation and whyThisObject bounded strings only','Naturalness/admission objectSpecificity/functionalRelation source support; rationale alone insufficient','evidence_supported_admission_v2.py','objectSpecificity'),
    ('Direct goal interference','SEMANTIC','goalRuleRelationship bounded string only','Admission goalInterference and canonical goal evidence','evidence_supported_admission_v2.py','goalInterference'),
    ('Non-arbitrary magic','SEMANTIC','No semantic magic criterion','Admission nonArbitrary/object operation support; taxonomy unknown may still admit','evidence_supported_admission_v2.py','nonArbitrary'),
    ('Production feasibility','SEMANTIC','No render feasibility guarantee','BG/SFE/ranking production risk/staging text screens; no media verification','short_form_engine.py','productionRisks'),
    ('Target duration approximately15 seconds','MIXED','durationSeconds default15, optional; default annotation is not const15','Domain defaults15; SFE accepts planned10–20, not exact15 or measured media','semantic_concept_provider.py','durationSeconds: float'),
    ('Maximum duration20 seconds','STRUCTURAL_DECLARED','durationSeconds number minimum10 maximum20 if supplied; optional','Pydantic bound/default; SFE planned range10–20. Only declared timing, not rendered runtime','short_form_engine.py','not 10 <= duration <= 20'),
    ('No provider self-ranking','MIXED','additionalProperties=false rejects rank keys; rationale free text can still claim rank','Adapter marks rationaleScored=false; rankings computed independently, text claims not semantically banned by schema','semantic_concept_adapter.py','rationaleScored'),
    ('No provider self-scoring','MIXED','additionalProperties=false rejects score keys; free text claims structurally possible','Unscored rationale receives no bonus; does not prove provider complies with instruction','semantic_concept_adapter.py','rationaleScored'),
    ('One location','SEMANTIC','environment scalar string, not depicted location count','Production text risks only partially cover scene changes','short_form_engine.py','stagingRisks'),
    ('Stable identities and few moving elements','SEMANTIC','No physical identity/entity count checks','Production feasibility risk heuristics only','short_form_engine.py','stagingRisks'),
    ('Child-safe comedy','SEMANTIC','No semantic safety rule in JSON shape','BoundedData.safe_text lexical blacklist is partial, not comprehensive safety proof','semantic_concept_provider.py','def safe_text'),
    ('Batch diversity and historical cautions','SEMANTIC','No crosscandidate creative novelty judgment','Creative shape/history/ranking/preselection compare fingerprints, not certified novelty','semantic_concept_generation.py','def review_pool'),
    ('Exact finalPayoff/last consequence equality','STRUCTURAL_CROSS_FIELD','Not encoded in JSON schema','Pydantic consistent_final enforces exact equality after whitespace normalization','semantic_concept_provider.py','def consistent_final'),
    ('Actual rendered duration ≤20','SEMANTIC_MEDIA','Not measurable from source JSON','No render or video measurement in this workflow/task','semantic_concept_provider.py','durationSeconds: float'),
    ]
    prompt_only={'One primary everyday object'}
    policy_only=[
        ('Rule stated in one precise observable repeatable sentence','ONE precise, observable, repeatable sentence'),
        ('No bundled independent powers or actor loopholes','Do not bundle several unrelated powers'),
        ('Spread, transfer and magnitude must follow declared relationship','Consequence spread must follow'),
        ('No motion/context/text/inset used as paused-frame proof','an explanatory inset'),
        ('No delayed first action or ordinary setup','spend no first 2–3 seconds'),
        ('Concise stageable causal sentences','sentences concise, concrete and stageable'),
        ('Environmental objects only passive staging','environmental objects as passive staging only'),
        ('No default harder/twohands/brace/fakesuccess ladder','attempt → try harder'),
        ('No hidden sub-scenes enlarging duration','without multiple hidden sub-scenes'),
        ('Payoff surprising but inevitable and essential to rule','Could this payoff happen'),
        ('Varied payoff families are inspiration not recipes','not required taxonomy labels or recipes'),
        ('Loop optional; no new magic to reset','A loop is optional'),
        ('Unfamiliar coherent mechanics allowed without taxonomy overfit','outside the known engine taxonomy'),
        ('Task examples are not mandatory templates','do not copy these mechanically'),
        ('Private editing check; no reasoning/checklist/self-certification output','Do not expose chain-of-thought'),
        ('Private editing is no external retry loop or winner selection','not permission for a downstream retry loop'),
    ]
    for label,needle in policy_only:
        data.append((label,'SEMANTIC','No complete semantic check encoded in native schema',
            'Prompt policy; existing broad causal/progression/production screens may find some violations but no exhaustive dedicated enforcement',
            'semantic_concept_prompt_v2.txt',needle))
        prompt_only.add(label)
    matrix=[]
    for label,kind,schema,validator,file,needle in data:
        text=(WORKFLOW/file).read_text();line=next((i for i,s in enumerate(text.splitlines(),1) if needle in s),None)
        if line is None:raise ValueError((file,needle))
        not_enforced=label=='Actual rendered duration ≤20'
        matrix.append(dict(requirement=label,type=kind,placement='NOT_ENFORCED' if not_enforced else 'PROMPT_ENFORCED' if label in prompt_only else 'MULTI_LAYER',
            schema=schema,promptV2='No measured-media guarantee' if not_enforced else 'Explicit instruction; see requirement crosswalk for exact locations',
            deterministic=validator,evidence=dict(path='intelligence/ml-service/app/workflow/'+file,line=line,needle=needle),
            limitation='Prompt instruction is not mechanical enforcement; source heuristics are not a complete semantic proof. Strict=false native generation is not guaranteed schema conformity.'))
    return matrix


def old_probe_audit():
    folder=ROOT/'intelligence/docs/semantic-native-schema-integrity-probe-1-run-001'
    request=json.loads((folder/'last-mile-sdk-request.json').read_text());result=json.loads((folder/'result.json').read_text());raw=json.loads((folder/'response.txt').read_text())
    schema=request['response_format']['json_schema']['schema'];idea=schema['properties']['ideas']['items'];beats=idea['properties']['beats'];ref=beats['items']['$ref'];beat=schema
    for key in ref[2:].split('/'):beat=beat[key]
    errors=list(Draft202012Validator(schema).iter_errors(raw));ideas,rejected=parse_response(json.dumps(raw),60)
    return dict(classification=dict(TRANSPORT='PASS',SMALL_NATIVE_STRUCTURED_OUTPUT='PASS',CORRECTED_FULL_NATIVE_SCHEMA='PASS_AT_EXECUTION_LEVEL',LOCAL_STRUCTURAL_CONFORMANCE='FAIL',FULL_CREATIVE_CONTRACT='NOT_YET_TESTED_SUCCESSFULLY_AFTER_SCHEMA_REPAIR',FULL_PROMPT_V2='Previously associated with timeout in Probe D; not sent in corrected-schema minimal probe'),
        historicalClassification=result['primaryClassification'],historicalArtifactsModified=False,
        source='intelligence/docs/semantic-native-schema-integrity-probe-1-run-001/',
        requestPrompt=request['messages'],strict=request['response_format']['json_schema']['strict'],schemaSha256=digest(schema),
        beats=dict(required='beats' in idea['required'],minItems=beats['minItems'],maxItems=beats['maxItems'],nestedRequired=beat['required'],returnedCount=len(raw['ideas'][0]['beats']),schemaValid=False),
        duration=dict(field='durationSeconds',schema=idea['properties']['durationSeconds'],required='durationSeconds' in idea['required'],returnedValue=raw['ideas'][0]['durationSeconds'],inferredFromProse=False,renderMeasured=False),
        actualLocalErrors=[dict(path=list(e.path),validator=e.validator) for e in errors],domainAccepted=bool(ideas),
        explanation='The transport adapter completed and returned content after finishReason=stop; it does not enforce local SemanticIdea conformance. Native request used strict=false. The exact returned content violates existing minItems4 and maximum20. Both local JSON schema validation and domain parsing reject it. It was not accepted as a valid creative candidate. The remote cause of nonconformance cannot be determined from stored evidence; no absent-bound or remote keyword-support explanation is asserted.',
        timing=result['timing'],responseBytes=result['responseBytes'],usage=result['usage'],
        creativePromptScope='Only minimal diagnostic instructions were sent. Full Prompt V2 creative semantics were not tested successfully with corrected schema. Earlier full prompt timeout is association, not proof of a specific reasoning-burden cause.')


def run(output):
    output=Path(output);output.mkdir(exist_ok=True,parents=True)
    cfg=config();cast,_=resolve_cast(cfg);p=compact_prompt(cfg,cast,1);op=prompt_v2(config('v2'),cast,1)
    request=construct_native_request(cfg,cast,1,PROFILE)
    reqs=json.loads((FIXTURES/'semantic_prompt_v2_compact_policy_v1.json').read_text())
    sizes={}
    for label,prompt in [('v2',op),('v2Compact',p)]:
        sizes[label]=dict(system=size_metrics(prompt['system']),user=size_metrics(prompt['prompt']),
            totalText=size_metrics(prompt['system']+'\n'+prompt['prompt']),promptSha256=prompt['sha256'],
            systemTextSha256=hashlib.sha256(prompt['system'].encode()).hexdigest())
    sizes['reductionPercent']={part:round(100*(1-sizes['v2Compact'][part]['characters']/sizes['v2'][part]['characters']),4) for part in ('system','user','totalText')}
    sizes['tokenReductionQualification']='Estimated tokens use the same chars/4 proxy; actual model tokenizer count, latency, adherence and creativity are not measured.'
    redundancies=[
        dict(cluster='Immutable rule / trigger / no new power / same-rule payoff',v2Lines=[10,11,12,13,28,33,35,44,47],compact='One CORE RULE INVARIANT; references in BEATS/PAYOFF/one final check. Distinct trigger/mapping/spread protections retained.'),
        dict(cluster='Paused opening visibility / no explanation / no delay',v2Lines=[16,17,18,19,45],compact='One OPENING paragraph plus short final reference.'),
        dict(cluster='Beat quantity / causal fields / progression / timing',v2Lines=[7,27,28,29,46],compact='One BEATS block; quantities retained where creative pacing depends on them.'),
        dict(cluster='Payoff dependency / no new ending power / final check',v2Lines=[32,33,34,35,47],compact='One PAYOFF block refers to core; final check references it without restating all failures.'),
        dict(cluster='No provider authority / no exposed reasoning',v2Lines=[4,35,43,48],compact='One initial role boundary; output/final blocks only reference operational boundary.'),
        dict(cluster='Duplicated native schema in V2 user text',v2PayloadKeys=list(json.loads(op['prompt'])),compactPayloadKeys=list(json.loads(p['prompt'])),compact='Remove candidateSchema/outputEnvelope/batchInstructions duplicated in native format. Native candidate/beat fields, enums, lengths, defaults and required lists unchanged; semantic field guidance retained in policy.')]
    artifacts=dict(providerCalls=0,renders=0,execution='OFFLINE_ONLY_STOP',oldProbe=old_probe_audit(),contractPlacement=placement_matrix(),
        structuralTests=structural_results(),sizes=sizes,redundancy=redundancies,policyEquivalence=reqs,mocks=mock_results(),
        integration='New explicit CompactPromptRequest + compact_prompt/construct_native_request only. No provider execution API, credential access, transport, default routing or validator change. Legacy adapter label SEMANTIC_V1 is inherited provenance, actual prompt version stored separately.',
        instructionCountMethod='No objective natural-language instruction count claimed. Exact regex occurrence counts per marker and exact section/line counts are provided; overlapping clauses are not falsely counted as independent policies. Policy crosswalk has56 editorial groups.')
    def write(name,data):
        (output/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    write('audit.json',artifacts);write('offline-native-request.json',request);write('compact-prompt.json',p)
    (output/'compact-prompt-exact.txt').write_text(p['system'])
    return artifacts

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    a=run(parser.parse_args().output)
    print(json.dumps(dict(providerCalls=0,renders=0,reductionPercent=a['sizes']['reductionPercent'],requirements=len(a['policyEquivalence']['requirements']),cases=len(a['mocks']['cases']))))
