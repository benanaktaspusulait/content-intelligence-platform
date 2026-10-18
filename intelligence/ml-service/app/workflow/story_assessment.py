"""Single research-only STORY_REVIEW adapter inside existing Story Evolution.

No generation, scheduler, new persistence or production approval. Java owns the
same durable ledger; this adapter compiles/checks one independently granted review.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import hashlib
import uuid
import time
from openai import Timeout
from .story_experiment import sha, encoded, model_identity
from .story_evidence import derive_source_evidence, review_evidence_catalog, verify_review_evidence_catalog
from .creative_reconstruction import DIMENSIONS

POLICY='ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1'
SCHEMA='assessment-only-story-review-v4-derived-verdict'
TIMEOUT_POLICY={'version':'assessment-story-review-timeouts-v1','connectSeconds':5,'poolSeconds':5,'writeSeconds':10,'readSeconds':60,'backendHttpSeconds':90,'workflowDeadlineSeconds':600}

def sdk_timeout():
    return Timeout(TIMEOUT_POLICY['readSeconds'],connect=TIMEOUT_POLICY['connectSeconds'],pool=TIMEOUT_POLICY['poolSeconds'],write=TIMEOUT_POLICY['writeSeconds'])
SELECTED={
 'A':('50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088','34bc110e50779d47964b3546cd3e5f69b9ac8ea773f9a63aee1e04f2281359d1'),
 'B':('4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739','10dc1482d66514e153835b6e3cd90f4e8b58ff1e1d61f51fa99e42424f15fef3')}
EXTRA_CHECKS=['trigger_conditions','single_mechanic','causal_clarity','protected_events']
CHECKS=['identity','premise','rule','continuity','ending']+EXTRA_CHECKS


def _object(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def _enum(*values):
    return {'type':'string','enum':list(values)}


def response_contract(catalog):
    """Same fixed A/B topology; native enum isolation from the bound catalog."""
    string={'type':'string'}
    schema=_object({'schemaVersion':_enum(SCHEMA),
        'candidateAssessments':_object({ref:{'$ref':'#/$defs/candidate_'+ref} for ref in ('A','B')}),
        'researchPreference':_enum('A','B','NO_CREATIVE_WINNER'),'reason':string,'evidenceLimitations':string})
    defs={}
    for role,key in [('SOURCE','S'),('CANDIDATE_A','A'),('CANDIDATE_B','B')]:
        ids=[r['evidenceId'] for r in catalog['records'] if r['documentRole']==role and r['exactOriginalText'].strip()]
        if not ids:raise ValueError('Empty authorized evidence role')
        defs['ids_'+key]={'type':'array','items':_enum(*ids)}
    for ref in ('A','B'):
        refs={'sourceEvidenceIds':{'$ref':'#/$defs/ids_S'},'candidateEvidenceIds':{'$ref':'#/$defs/ids_'+ref}}
        defs['semantic_'+ref]=_object({'outcome':_enum('PASS','FAIL','UNKNOWN'),
            'basis':_enum('SEMANTIC_SUPPORT','CONTRADICTION','SUBSTANTIVE_OMISSION','INSUFFICIENT'),**refs,'reason':string})
        defs['dimension_'+ref]=_object({'candidateEvidenceIds':refs['candidateEvidenceIds'],
            'strength':string,'weakness':string,'risk':string})
        defs['comparison_'+ref]=_object({'outcome':_enum('MATERIAL_IMPROVEMENT','MINOR_VARIATION','NO_MATERIAL_IMPROVEMENT','UNKNOWN'),
            'baselineEvidenceIds':refs['sourceEvidenceIds'],'candidateEvidenceIds':refs['candidateEvidenceIds'],
            **{k:string for k in ('change','visibleConsequence','addressedWeakness','newRisk','materialityReason')}})
        defs['candidate_'+ref]=_object({'semanticChecks':_object({k:{'$ref':'#/$defs/semantic_'+ref} for k in CHECKS}),
            'creativeDimensions':_object({k:{'$ref':'#/$defs/dimension_'+ref} for k in DIMENSIONS}),
            'creativeConclusion':{'$ref':'#/$defs/comparison_'+ref}})
    schema['$defs']=defs
    return schema


def response_format(catalog):
    return {'type':'json_schema','json_schema':{'name':'independent_story_review_derived_v4','strict':True,'schema':response_contract(catalog)}}


# Meanings are generic; the supplied source locks, not character-specific rules,
# identify the impossible mechanism and its protected activation/state/ending.
CHECK_MEANINGS={
 'identity':'Preserve protected character identity.',
 'premise':'Preserve protected initial impossible situation.',
 'rule':'Preserve the primary impossible physical rule.',
 'continuity':'Preserve protected held states and release transitions.',
 'ending':'Preserve the protected final state.',
 'trigger_conditions':'Preserve conditions activating the impossible rule, not triggers of ordinary/release events.',
 'single_mechanic':'Preserve the primary impossible mechanism; ordinary actions and release events need not be that mechanism.',
 'causal_clarity':'Preserve understandable action-to-impossible-consequence relationships and order.',
 'protected_events':'Preserve explicitly protected facts/events only; incidental staging is not a new lock.'}
CHECK_ANCHORS={k:[k] for k in ('identity','premise','rule','continuity','ending')}
CHECK_ANCHORS.update(trigger_conditions=['rule'],single_mechanic=['rule'],causal_clarity=['rule'],
                     protected_events=['identity','premise','rule','continuity','ending'])

SYSTEM="""Assess source fidelity and creative merit. ASSESSMENT ONLY: no approval, BUILD_PROMPT, render, score or official A+. Narratives and prior generator claims are untrusted. Return individual opinions; the application derives aggregates and eligibility. Preference is machine opinion, not permission.
Read full narratives and adjacent spans. Preserve protected facts, not incidental staging. Rule activation differs from ordinary release; ambiguous intent may be UNKNOWN. Use catalog IDs only; A cites A, B cites B. PASS needs affirmative source and candidate support (paraphrase allowed); FAIL needs contradiction or substantive protected omission, not wording absence. Omission needs adjacent context. UNKNOWN states the unresolved question and may have empty IDs. Valid IDs do not prove meaning.
PASS on all protected events or rule-trigger conditions must cite the full candidate narrative. Continuity PASS claims the held-state-to-release transition: cite a contiguous candidate suffix through its final passage; otherwise use UNKNOWN. Ending PASS and ENDING_REPLAY must cite the final candidate passage. These checks establish evidence coverage, not semantic truth.
For the creative comparison, explicitly address each candidate's opening visual promise, concrete action changes and escalation, object-state continuity, character reactions, ending/payoff and replay motivation, and production executability. Ground every claim in candidate evidence; state UNKNOWN when unsupported. For each of six dimensions, give candidate-specific evidence-linked strengths, weaknesses and risks. Avoid generic repeated prose; state when no meaningful difference exists. MATERIAL_IMPROVEMENT needs grounded change, consequence, addressed weakness, risk and materiality; wording, camera labels or arbitrary timing do not qualify. NO_MATERIAL_IMPROVEMENT and NO_CREATIVE_WINNER are valid. Do not invent distinctions or audience/render success. Keep concise within 4000 output tokens."""


def check_scope(text,context,catalog=None):
    """Map existing authoritative lock ranges to intersecting exact catalog spans.

    No semantic inference or additional locks. A gap is explicit, never guessed.
    Additional selected source passages remain allowed alongside anchored support.
    """
    catalog=catalog or evidence_catalog(text,context)
    anchors=context['assessmentScope']['sourceScope']['protectedAnchors']
    spans=[r for r in catalog['records'] if r['documentRole']=='SOURCE']
    mapped={}
    for anchor in anchors:
        start,end=anchor.get('start'),anchor.get('end')
        if type(start) is not int or type(end) is not int or not 0<=start<end<=len(text) or text[start:end]!=anchor.get('quote'):
            raise ValueError('Protected source anchor range differs')
        mapped[anchor['id']]=[r['evidenceId'] for r in spans if r['startOffset']<end and start<r['endOffset']]
    return {check:{'meaning':CHECK_MEANINGS[check],
        'anchorEvidence':{key:mapped.get(key,[]) for key in CHECK_ANCHORS[check]},
        **({'unmappedAnchors':[key for key in CHECK_ANCHORS[check] if not mapped.get(key)]} if any(not mapped.get(key) for key in CHECK_ANCHORS[check]) else {})} for check in CHECKS}


def sources(text, context):
    if context.get('assessmentOnlyPolicy')!=POLICY:raise ValueError('Assessment-only policy required')
    scope=context['assessmentScope']; source_scope=scope['sourceScope']
    if text!=source_scope['sourceStory'] or sha(text)!=source_scope['sourceStorySha256']:raise ValueError('Source SHA differs')
    if sha({k:v for k,v in source_scope.items() if k!='sourceScopeSha256'})!=source_scope['sourceScopeSha256']:raise ValueError('Source scope differs')
    entries=scope.get('candidates');out=[]
    if not isinstance(entries,list) or [x.get('ref') for x in entries]!=['A','B']:raise ValueError('Exact approved cross-run selection required')
    ctx={'storyExperiment':{'version':'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1','requestedAlternativeCount':2,
        'protectedAnchors':source_scope['protectedAnchors'],'sourceStorySha256':sha(text),'sourceScopeSha256':source_scope['sourceScopeSha256']}}
    for entry in entries:
        ref=entry['ref'];receipt=entry['receipt'];raw=receipt.get('rawProviderResponse')
        if not isinstance(raw,str) or sha(raw)!=SELECTED[ref][1] or entry['rawResponseSha256']!=sha(raw):raise ValueError('Authentic raw response SHA differs')
        if receipt.get('responseSha256')!=sha(raw) or not receipt.get('providerDispatched') or receipt.get('provider')!='deepseek':raise ValueError('Real provider provenance required')
        api=receipt.get('providerApiResponse') or {}
        if api.get('choices',[{}])[0].get('message',{}).get('content')!=raw:raise ValueError('SDK/raw evidence differs')
        metadata=receipt.get('providerResponseMetadata') or {}
        if metadata.get('model')!='deepseek-flash' or api.get('model')!=metadata.get('model') or receipt.get('usage')!=api.get('usage'):
            raise ValueError('Authentic SDK identity/usage provenance differs')
        if receipt.get('model')!=('deepseek-chat' if ref=='A' else 'deepseek-flash') or entry.get('originalExecutionState')!='STOPPED':
            raise ValueError('Historical failed identity qualification must remain visible')
        original=next((x for x in json.loads(raw).get('alternatives',[]) if x.get('candidateId')==entry['candidateId']),None)
        if not original or sha(original['text'])!=SELECTED[ref][0] or entry['candidateSha256']!=sha(original['text']):raise ValueError('Approved candidate SHA differs')
        if original!=entry['originalCandidate']:raise ValueError('Mutable candidate differs from immutable raw response')
        if entry.get('knownDefiniteSourceViolation') is not False:raise ValueError('Known definite source violation excluded')
        if entry['originalRunId']!=receipt['runId']:raise ValueError('Historical run identity differs')
        ev=derive_source_evidence(text,ctx,original)
        if ev['status'] not in ('SEMANTIC_FIDELITY_REVIEW_REQUIRED','DETERMINISTIC_SOURCE_CONTRACT_PASSED'):raise ValueError('Contradiction/proposal/invalid narrative excluded')
        out.append({'ref':ref,'title':original['title'],'narrative':original['text'],'candidateSha256':sha(original['text']),
            'researchStatus':'SEMANTIC_FIDELITY_REVIEW_REQUIRED','semanticFidelity':'UNKNOWN',
            'provenance':{'origin':'REAL_AI_PROVIDER','originalRunId':receipt['runId'],'rawResponseSha256':sha(raw),
                'requestedModel':receipt['model'],'returnedModel':receipt['providerResponseMetadata']['model'],
                'historicalExecutionState':entry['originalExecutionState'],'historicalIdentityMatch':receipt['model']==receipt['providerResponseMetadata']['model']},
            'derivedEvidence':{'protectedFacts':ev['protectedFacts'],'narrativeSpans':ev['narrativeSpans'],
                'invalidCitationsExcluded':[x for x in ev['modelEvidenceClaims'] if x['status']=='INVALID_EVIDENCE_CLAIM'],
                'explicitContradictions':ev['explicitContradictions'],'semanticQuestions':ev['semanticQuestions']}})
    if out[0]['provenance']['originalRunId']==out[1]['provenance']['originalRunId']:raise ValueError('Cross-run origins must remain distinct')
    return out


def evidence_catalog(text,context):
    selected=sources(text,context)
    documents={'SOURCE':text,**{'CANDIDATE_'+c['ref']:c['narrative'] for c in selected}}
    catalog=review_evidence_catalog(documents)
    verify_review_evidence_catalog(catalog,documents)
    return catalog


def wire(text, context):
    selected=sources(text,context);scope=context['assessmentScope']['sourceScope']
    if {a['id'] for a in scope['protectedAnchors']}!=set(CHECKS)-set(EXTRA_CHECKS):
        raise ValueError('Approved protected fact IDs differ from strict reviewer schema')
    catalog=evidence_catalog(text,context)
    # Full narratives and original protected facts remain available. The catalog
    # replaces redundant literal-location/quotation projections, not source text.
    candidates=[{k:c[k] for k in ('ref','title','narrative','candidateSha256','provenance')} for c in selected]
    return {'system':SYSTEM,'payload':{'policy':POLICY,'originalStory':text,
        'protectedAnchors':scope['protectedAnchors'],'productionSettings':scope['productionSettings'],
        'candidates':candidates,'evidenceCatalog':catalog,'dimensions':list(DIMENSIONS),'semanticChecks':check_scope(text,context,catalog),
        'comparisonObjective':'Identify source-supported viewer-visible gains over the original; NO_CREATIVE_WINNER is valid.',
        'assessmentOnly':True,'sourceApproval':False,'renderAuthorization':False},'responseFormat':response_format(catalog)}


def request_body(text,context):
    w=wire(text,context)
    return {'model':'gpt-4o-mini-2024-07-18','messages':[{'role':'system','content':w['system']},
        {'role':'user','content':encoded(w['payload'])}],'temperature':0,'max_tokens':4000,'response_format':w['responseFormat']}


def preview(text, context):
    if context['assessmentScope'].get('transportPolicy')!=TIMEOUT_POLICY:raise ValueError('Assessment-specific timeout policy differs from backend binding')
    w=wire(text,context);model=os.getenv('WORKFLOW_STORY_REVIEW_MODEL','')
    if model!='gpt-4o-mini-2024-07-18':raise ValueError('Exact configured OpenAI STORY_REVIEW model required')
    rates=[float(os.getenv('WORKFLOW_STORY_REVIEW_'+s+'_USD_PER_MILLION','nan')) for s in ('INPUT','OUTPUT')]
    if not all(math.isfinite(v) and v>0 for v in rates):raise ValueError('Explicit configured review prices required')
    size=len(encoded(w['payload']).encode());sys_size=len(w['system'].encode())
    request_bytes=len(encoded(request_body(text,context)).encode())
    if request_bytes>24000:raise ValueError('Assessment complete request exceeds 24000-byte envelope')
    bound=((request_bytes+1000)*rates[0]+4000*rates[1])/1e6
    root=Path(__file__).resolve().parents[1]
    return {'policy':POLICY,'role':'STORY_REVIEW','provider':'openai','model':model,
        'sourceStorySha256':sha(text),'scopeSha256':sha(context['assessmentScope']),
        'evidenceCatalogSha256':w['payload']['evidenceCatalog']['catalogSha256'],
        'evidenceDocumentBindings':w['payload']['evidenceCatalog']['documentBindings'],
        'evidenceExtractionVersion':w['payload']['evidenceCatalog']['version'],
        'systemSha256':sha(w['system']),'effectiveRequestSha256':sha(encoded(w['payload'])),
        'responseSchemaSha256':sha(w['responseFormat']['json_schema']['schema']),'responseFormatSha256':sha(w['responseFormat']),
        'serializedRequestSha256':sha(request_body(text,context)),
        'responseFormatType':'json_schema','strictStructuredOutput':True,
        'schemaVersion':SCHEMA,'maxRequests':1,'maximumInputBytes':24000,
        'payloadBytes':size,'systemBytes':sys_size,'serializedRequestBytes':request_bytes,
        'schemaBytes':len(encoded(w['responseFormat']['json_schema']['schema']).encode()),'maxOutputTokens':4000,
        'inputUsdPerMillion':rates[0],'outputUsdPerMillion':rates[1],'maximumCalculatedUsd':bound,
        'automaticRetries':False,'fallback':False,'assessmentOnly':True,
        'clientRequestIdPolicy':'application-request-uuid-v1','timeoutPolicy':deepcopy(TIMEOUT_POLICY),
        'outboundTransportMetadataSha256':sha({'timeoutPolicy':TIMEOUT_POLICY,'clientHeader':'X-Client-Request-Id','valuePolicy':'application-request-uuid-v1','valueAsciiBytes':36}),
        'requestFramingAllowanceBytes':1000,'clientRequestIdHeaderBytes':len('X-Client-Request-Id: '+str(uuid.UUID(int=0))+'\r\n'),
        'implementationSha256':sha({str(p):hashlib.sha256((root/p).read_bytes()).hexdigest() for p in (
            'workflow/story_assessment.py','workflow/story_evidence.py','workflow/story_quality.py','workflow/api.py','workflow/creative_roles.py','llm/openai_provider.py')})}


def resolve_review_evidence(value,text,context):
    """Defined v3 decoding; never mutate/repair raw model decisions or evidence IDs."""
    catalog=evidence_catalog(text,context)
    index={r['evidenceId']:r for r in catalog['records']}
    resolved={}
    scopes=check_scope(text,context,catalog)
    def resolve(ids,role,path,required=False):
        if not isinstance(ids,list) or len(ids)!=len(set(ids)) or required and not ids:
            raise ValueError('Distinct grounded evidence references required: '+path)
        out=[]
        for identity in ids:
            record=index.get(identity)
            if record is None or record['documentRole']!=role or not record['exactOriginalText'].strip():
                raise ValueError('Evidence ID outside bound document: '+path)
            out.append(deepcopy(record))
        resolved[path]=out
        return out
    for ref,row in value['candidateAssessments'].items():
        role='CANDIDATE_'+ref
        # Keep the historical hard creative-boundary rejection first so an
        # unchanged V5 response continues to fail for its original reason.
        for dim,d in row['creativeDimensions'].items():
            passages=resolve(d['candidateEvidenceIds'],role,ref+'.creativeDimensions.'+dim+'.candidateEvidenceIds')
            if passages and dim in ('SCROLL_STOP_VISUAL_PROMISE','ENDING_REPLAY'):
                ordered=[r for r in catalog['records'] if r['documentRole']==role and r['exactOriginalText'].strip()]
                boundary=ordered[0 if dim=='SCROLL_STOP_VISUAL_PROMISE' else -1]['evidenceId']
                if boundary not in d['candidateEvidenceIds']:
                    raise ValueError('Creative boundary evidence missing: '+ref+'.'+dim)
        for check,f in row['semanticChecks'].items():
            path=ref+'.semanticChecks.'+check
            source=resolve(f['sourceEvidenceIds'],'SOURCE',path+'.sourceEvidenceIds',f['outcome']!='UNKNOWN')
            groups=[set(ids) for ids in scopes[check]['anchorEvidence'].values() if ids]
            chosen={r['evidenceId'] for r in source}
            # PASS on all protected events requires all authoritative lock groups.
            # FAIL/UNKNOWN may concern just one protected fact. Extra context allowed.
            if groups and chosen and (not all(chosen & group for group in groups) if check=='protected_events' and f['outcome']=='PASS' else not any(chosen & group for group in groups)):
                raise ValueError('Source evidence misses protected-fact anchor: '+path)
            candidate=resolve(f['candidateEvidenceIds'],role,path+'.candidateEvidenceIds',f['outcome']!='UNKNOWN')
            if check in ('protected_events','trigger_conditions') and f['outcome']=='PASS':
                all_candidate_ids={r['evidenceId'] for r in catalog['records'] if r['documentRole']==role and r['exactOriginalText'].strip()}
                selected_ids={r['evidenceId'] for r in candidate}
                if selected_ids!=all_candidate_ids:
                    raise ValueError('PASS evidence must cover the full candidate narrative: '+path)
            # A protected continuity PASS describes a transition through the
            # story's terminal state. Validate coverage, not meaning: selected
            # candidate spans must form a contiguous suffix ending at the final
            # catalog span. The model's interpretation remains non-deterministic.
            if check=='continuity' and f['outcome']=='PASS':
                ordered=[r for r in catalog['records'] if r['documentRole']==role and r['exactOriginalText'].strip()]
                selected_ids={r['evidenceId'] for r in candidate}
                if not ordered or ordered[-1]['evidenceId'] not in selected_ids:
                    raise ValueError('Continuity PASS evidence must reach the candidate final passage: '+path)
                first=min((i for i,r in enumerate(ordered) if r['evidenceId'] in selected_ids),default=len(ordered))
                expected={r['evidenceId'] for r in ordered[first:]}
                if selected_ids!=expected:
                    raise ValueError('Continuity PASS evidence must cover a contiguous candidate suffix: '+path)
            if check=='ending' and f['outcome']=='PASS':
                ordered=[r for r in catalog['records'] if r['documentRole']==role and r['exactOriginalText'].strip()]
                if not ordered or ordered[-1]['evidenceId'] not in {r['evidenceId'] for r in candidate}:
                    raise ValueError('Ending PASS evidence must include the candidate final passage: '+path)
            if f['outcome']=='FAIL' and f['basis']=='SUBSTANTIVE_OMISSION':
                ordered=sorted(candidate,key=lambda r:r['startOffset'])
                if len(ordered)<2 or any(a['endOffset']!=b['startOffset'] for a,b in zip(ordered,ordered[1:])):
                    raise ValueError('Substantive omission requires adjacent bounded narrative context; otherwise UNKNOWN')
        comp=row['creativeConclusion'];path=ref+'.creativeConclusion.';material=comp['outcome']=='MATERIAL_IMPROVEMENT'
        resolve(comp['baselineEvidenceIds'],'SOURCE',path+'baselineEvidenceIds',material)
        resolve(comp['candidateEvidenceIds'],role,path+'candidateEvidenceIds',material)
    return {'evidenceType':'APPLICATION_DERIVED_EVIDENCE','catalogSha256':catalog['catalogSha256'],
        'offsetConvention':catalog['offsetConvention'],'resolvedReferences':resolved,
        'semanticInterpretation':'MODEL_OPINION_NOT_DETERMINISTIC_PROOF'}


def validate_review(value,text,context):
    import re
    from jsonschema import Draft202012Validator
    from .story_quality import _EVENT_ALIASES
    catalog=evidence_catalog(text,context)
    errors=sorted(Draft202012Validator(response_contract(catalog)).iter_errors(value),key=lambda e:str(list(e.path)))
    if errors:raise ValueError('Strict review schema: '+str(list(errors[0].path))+': '+errors[0].message[:240])
    resolved=resolve_review_evidence(value,text,context)['resolvedReferences']
    for ref,row in value['candidateAssessments'].items():
        for check,f in row['semanticChecks'].items():
            if not f['reason'].strip():raise ValueError('Semantic reason required')
            expected={'PASS':{'SEMANTIC_SUPPORT'},'FAIL':{'CONTRADICTION','SUBSTANTIVE_OMISSION'},'UNKNOWN':{'INSUFFICIENT'}}
            if f['basis'] not in expected[f['outcome']]:raise ValueError('Semantic outcome/evidence basis mismatch')
            if f['outcome']=='FAIL' and re.search(r'(?:exact|identical|verbatim|literal) (?:source )?(?:sentence|wording|phrase|text).{0,40}(?:missing|absent|not)|(?:missing|absent).{0,40}(?:exact|identical|verbatim|literal)',f['reason'],re.I):
                raise ValueError('Literal absence alone cannot establish semantic FAIL')
        for d in row['creativeDimensions'].values():
            if not all(d[k].strip() for k in ('strength','weakness','risk')):raise ValueError('Strengths, weaknesses and risks required')
            if not d['candidateEvidenceIds'] and any(d[k].strip().upper()!='UNKNOWN' for k in ('strength','weakness','risk')):
                raise ValueError('Unsupported creative dimension must remain UNKNOWN')
        creative=row['creativeConclusion']
        baseline_text=''.join(r['exactOriginalText'] for r in resolved[ref+'.creativeConclusion.baselineEvidenceIds'])
        candidate_text=''.join(r['exactOriginalText'] for r in resolved[ref+'.creativeConclusion.candidateEvidenceIds'])
        if creative['outcome']=='MATERIAL_IMPROVEMENT':
            if not all(creative[k].strip() and creative[k].strip().upper() not in ('NONE','UNKNOWN','N/A') for k in ('change','visibleConsequence','addressedWeakness','newRisk','materialityReason')):
                raise ValueError('Material improvement needs complete baseline/change/consequence/risk evidence')
            def tokens(t):return [_EVENT_ALIASES.get(w,w) for w in re.findall(r"[\w']+",t.lower())]
            def content(t):
                stop={'the','and','with','from','that','this','into','then','they','their','them','both','tries','story','candidate','original'}
                return {w for w in tokens(t) if len(w)>3 and w not in stop}
            if not (content(creative['change']) & content(candidate_text)) or not (content(creative['visibleConsequence']) & content(candidate_text)) or not (content(creative['addressedWeakness']) & content(baseline_text)):
                raise ValueError('Generic material claim lacks source-specific comparative grounding')
            if tokens(baseline_text)==tokens(candidate_text):raise ValueError('Identical or synonym-only evidence is not material improvement')
            if re.search(r'\b(?:shorter|polish|wording|vocabulary|synonym|different verb|camera label)\b',creative['change'],re.I):
                raise ValueError('Cosmetic change cannot establish material improvement')
        statements=[d[k] for d in row['creativeDimensions'].values() for k in ('strength','weakness','risk')]
        statements.extend(creative[k] for k in ('change','visibleConsequence','addressedWeakness','newRisk','materialityReason'))
        claim=r'\b(?:measured|proven|verified|guaranteed) (?:audience|retention|engagement|render|visual success)|(?:audience|retention) (?:increased|improved) by \d|official A\+ (?:achieved|verified)'
        for statement in statements:
            for sentence in re.split(r'[.!?;]',statement):
                match=re.search(claim,sentence,re.I)
                if match and not re.search(r'\b(?:no|not|never|without|unverified|unknown|lacks)\b',sentence[:match.start()],re.I):raise ValueError('Invented audience/render/A+ evidence')
    if not value['reason'].strip() or not value['evidenceLimitations'].strip():raise ValueError('Research reason and limitations required')
    return value


def semantic_summary(findings):
    """Deterministic application ownership; reasons remain exact model text."""
    outcomes={f['outcome'] for f in findings.values()}
    return {'semanticOutcome':'SEMANTIC_SOURCE_FAIL' if 'FAIL' in outcomes else 'SEMANTIC_SOURCE_UNKNOWN' if 'UNKNOWN' in outcomes else 'SEMANTIC_SOURCE_PASS',
        'sourceUnknowns':[{'check':key,'reason':f['reason']} for key,f in findings.items() if f['outcome']=='UNKNOWN']}


def derive_assessment(value,text,context):
    """Separate derived record. Never add calculated fields to model output."""
    validate_review(value,text,context)
    candidates={}
    for ref,row in value['candidateAssessments'].items():
        summary=semantic_summary(row['semanticChecks'])
        blockers=[]
        if summary['semanticOutcome']!='SEMANTIC_SOURCE_PASS':blockers.append(summary['semanticOutcome'])
        if row['creativeConclusion']['outcome']!='MATERIAL_IMPROVEMENT':blockers.append('NO_SUPPORTED_MATERIAL_IMPROVEMENT')
        if context.get('assessmentOnlyPolicy')!=POLICY or context['assessmentScope'].get('ownerPolicyApproval') is not True:
            blockers.append('RESEARCH_POLICY_NOT_AUTHORIZED')
        candidates[ref]={**summary,'eligibleForOwnerProposal':not blockers,'eligibilityRestrictions':blockers}
    return {'evidenceType':'APPLICATION_DERIVED_ASSESSMENT','schemaVersion':SCHEMA,
        'rawResponseSha256':sha(encoded(value)),'candidateAssessments':candidates,
        'researchPreference':value['researchPreference'],'researchPreferenceAuthority':'MACHINE_OPINION_ONLY',
        'ownerDecision':'PENDING','sourceApproved':False,'buildPromptAuthorized':False,'renderAuthorized':False,
        'officialAPlus':'INACTIVE'}


def execute(text,context,cap):
    from app.llm.openai_provider import OpenAIProvider, safe_provider_error
    from .creative_roles import _optimization_cost
    current=preview(text,context);authorized=context.get('assessmentDispatch') or {}
    if not context.get('assessmentSpendingAuthorized') or any(authorized.get(k)!=v for k,v in current.items()):raise ValueError('Fresh exact assessment spending grant required')
    if cap<current['maximumCalculatedUsd'] or cap>authorized.get('maxCostUsd',0):raise ValueError('Assessment reservation mismatch')
    if os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED','false').lower()!='true' or os.getenv('CPQ_PILOT_REAL_ENABLED','false').lower()!='true':raise ValueError('Real assessment dispatch disabled')
    if any(os.getenv(k) for k in ('POMPOM_ISOLATED_FIXTURE_DIR','POMPOM_ISOLATED_FIXTURE_TOKEN')) or os.getenv('POMPOM_ISOLATED_ACCEPTANCE')=='true':raise ValueError('Fixture fallback forbidden')
    request_id=str(uuid.UUID(str(context.get('storyRequestId'))))
    root=Path(os.environ['POMPOM_DATA_ROOT'])/'workflow'/'story-assessment-receipts'
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    def checkpoint(suffix,value):
        path=root/(request_id+suffix+'.json')
        with path.open('x',encoding='utf-8') as stream:
            os.chmod(path,0o600);stream.write(encoded(value));stream.flush();os.fsync(stream.fileno())
        return path
    # Exclusive pre-dispatch marker prevents paid replay even after ML/Java
    # process death. A complete raw checkpoint precedes parsing/validation.
    checkpoint('-reserved',{'requestId':request_id,'clientRequestId':request_id,'binding':current,'automaticResume':False})
    receipt={'role':'STORY_REVIEW','requestId':context.get('storyRequestId'),'provider':'openai','model':current['model'],
        'binding':current,'policy':POLICY,'evidenceType':'MACHINE_REVIEW','assessmentOnly':True,'retrySafe':False,
        'providerDispatched':False,'rawProviderResponse':None,'usage':None,'actualCostUsd':None,
        'clientRequestId':request_id,'billingStatus':'NOT_DISPATCHED','processingStatus':'NOT_STARTED','requestStartedAt':datetime.now(timezone.utc).isoformat()}
    provider=None; started=time.monotonic()
    try:
        provider=OpenAIProvider(model=current['model'],request_timeout=sdk_timeout());provider.client_request_id=request_id;provider.max_output_tokens=4000;provider.response_format=response_format(evidence_catalog(text,context))
        w=wire(text,context);receipt['providerDispatched']=True
        raw=provider.complete(encoded(w['payload']),system=w['system'],temperature=0)
        provider.last_raw_response=raw
        snapshot={'requestId':request_id,'binding':current,'rawProviderResponse':raw,
                  'providerApiResponse':getattr(provider,'last_provider_response',None),
                  'usage':getattr(provider,'last_usage',None),'providerResponseMetadata':getattr(provider,'last_response_metadata',None),
                  'responseSha256':sha(raw),'clientRequestId':request_id,'capturedBeforeParsing':True}
        receipt['rawReceiptFile']=str(checkpoint('-response',snapshot));receipt['rawReceiptSha256']=sha(snapshot)
        if (getattr(provider,'last_response_metadata',None) or {}).get('refusal'):raise ValueError('Provider refusal; no accepted review')
        if (getattr(provider,'last_response_metadata',None) or {}).get('finishReason')!='stop':raise ValueError('Incomplete provider response; no accepted review')
        receipt['parsedProviderResponse']=json.loads(raw)
        receipt['result']=validate_review(receipt['parsedProviderResponse'],text,context)
        receipt['derivedAssessment']=derive_assessment(receipt['result'],text,context)
        receipt['derivedAssessment']['rawResponseSha256']=sha(raw)
        receipt['resolvedEvidence']=resolve_review_evidence(receipt['result'],text,context)
        receipt['evidenceCatalog']=evidence_catalog(text,context)
        receipt['assessmentValidation']={'structuralSchemaValidity':'PASS','evidenceReferenceValidity':'PASS','modelSemanticFindings':'MACHINE_REVIEW_OPINION_NOT_DETERMINISTIC_PROOF','creativeComparison':'MACHINE_REVIEW_OPINION_NOT_PROVEN_QUALITY','ownerDecision':'PENDING'}
        receipt['processingStatus']='INDEPENDENT_REVIEW_COMPLETED'
    except Exception as error:
        receipt['processingStatus']='LOCALLY_REJECTED'
        diagnostic=getattr(provider,'last_error',None) or safe_provider_error(error,time.monotonic()-started)
        if getattr(provider,'last_provider_response',None) is not None or getattr(provider,'last_raw_response',None) is not None:
            meta=getattr(provider,'last_response_metadata',None) or {}
            diagnostic={'category':type(error).__name__,'detail':str(error)[:2000],
                'failureClass':'PROVIDER_REFUSAL' if meta.get('refusal') else 'INCOMPLETE_RESPONSE' if meta.get('finishReason')!='stop' else 'RESPONSE_VALIDATION_FAILED',
                'elapsedSeconds':round(time.monotonic()-started,6)}
        receipt['error']=diagnostic
        receipt['primaryFailureFile']=str(checkpoint('-failure',{'requestId':request_id,'clientRequestId':request_id,
            'primaryError':diagnostic,'completeSdkResponseReceived':getattr(provider,'last_provider_response',None) is not None,
            'usageReceived':getattr(provider,'last_usage',None) is not None}))
    if provider is not None:
        for dest,attribute in (('rawProviderResponse','last_raw_response'),('providerApiResponse','last_provider_response'),('usage','last_usage'),('providerResponseMetadata','last_response_metadata')):receipt[dest]=getattr(provider,attribute,None)
    raw=receipt['rawProviderResponse'];meta=receipt.get('providerResponseMetadata') or {};receipt['responseReceived']=raw is not None or receipt.get('providerApiResponse') is not None
    receipt['responseSha256']=sha(raw) if isinstance(raw,str) else None;receipt['responseReceivedAt']=datetime.now(timezone.utc).isoformat();receipt['modelIdentity']=model_identity(current['model'],meta)
    try:
        cost=_optimization_cost(receipt['usage'],current['inputUsdPerMillion'],current['outputUsdPerMillion']);receipt['configuredRateCostUsd']=cost
        if not receipt['modelIdentity']['verified']:
            receipt['billingStatus']='MODEL_IDENTITY_UNVERIFIED';raise ValueError('Actual reviewer identity missing/differs')
        receipt.update(actualCostUsd=cost,billingStatus='KNOWN_INCURRED')
        if meta.get('finishReason')!='stop' or cost>cap or receipt['usage'].get('completion_tokens',0)>4000:raise ValueError('Reviewer completion/budget constraint failed')
    except Exception as error:
        receipt['processingStatus']='LOCALLY_REJECTED' if receipt['responseReceived'] else 'DISPATCH_UNCERTAIN'
        accounting_error={'category':type(error).__name__,'detail':str(error)[:2000],
            'failureClass':'MISSING_USAGE_AFTER_RESPONSE' if receipt['responseReceived'] and not receipt['usage'] else 'ACCOUNTING_VALIDATION_FAILED'}
        if 'error' in receipt:receipt['accountingError']=accounting_error
        else:receipt['error']=accounting_error
        if receipt['actualCostUsd'] is None and receipt['billingStatus']!='MODEL_IDENTITY_UNVERIFIED':receipt['billingStatus']='USAGE_UNKNOWN'
    receipt['diagnostics']={'completeSdkResponseReceived':receipt.get('providerApiResponse') is not None,'usageReceived':receipt['usage'] is not None,'elapsedSeconds':round(time.monotonic()-started,6)}
    return receipt
